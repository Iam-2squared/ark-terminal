import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {loadFormalL0PartitionFromCache} from '../predict/long-only/phase57-long-only-l0-cache.js';
import {normalizeAndAggregateMinuteRows} from '../predict/long-only/phase57-long-only-integrated-dataset.js';
import {buildL1CrossSectionDataset} from '../predict/long-only/phase57-long-only-l1-cross-section.js';
import {buildFixedHorizonTargets} from '../predict/long-only/phase57-long-only-l2-fixed-horizon.js';
import {fitL2Candidate,selectRanked,evaluateSelection} from '../predict/long-only/phase57-long-only-l2-selector-v1.js';
import {
  LONG_ONLY_CURRENT_INTEGRATION_CONTRACT,selectCurrentSelectorCandidates,buildCurrentEntryTrainingRows,
  fitCurrentEntryAdapter,applyCurrentEntryLongOnly,replayCurrentExitLongOnly,
} from '../predict/long-only/phase57-long-only-current-integration.js';
import {simulateLaneCPortfolio,PHASE57_P25_LANE_C_ALLOCATION_PROFILES} from '../predict/portfolio/phase57-p25-lane-c-portfolio-simulator.js';

const arg=name=>{const i=process.argv.indexOf(name);return i<0?null:process.argv[i+1];};
const cacheRoot=path.resolve(arg('--cache-root')??''),freezePath=path.resolve(arg('--freeze-report')??''),output=path.resolve(arg('--output')??'');
if(!cacheRoot||!freezePath||!output)throw new Error('usage: --cache-root <private cache> --freeze-report <L2 report> --output <sanitized report>');
const plan=JSON.parse(fs.readFileSync(new URL('../predict/long-only/phase57-long-only-data-plan.json',import.meta.url),'utf8'));
const allocation=JSON.parse(fs.readFileSync(new URL('../predict/long-only/phase57-long-only-session-allocation-v3.json',import.meta.url),'utf8'));
const sessionsContract=JSON.parse(fs.readFileSync(new URL('../predict/long-only/phase57-long-only-l2-development-sessions.json',import.meta.url),'utf8'));
const freezeReport=JSON.parse(fs.readFileSync(freezePath,'utf8'));
const shaText=value=>createHash('sha256').update(value).digest('hex');
const sha=value=>shaText(JSON.stringify(value));
const base=path.join(cacheRoot,'phase57-long-only','raw','jquants-v2');
const codeOf=row=>String(row?.Code??row?.code??row?.symbol??'').trim().toUpperCase();
const sectorOf=row=>String(row?.S17??row?.Sec17??row?.Sector17Code??row?.Sector33Code??row?.S33??row?.sectorCode??'UNKNOWN');
const rowKey=row=>`${row.sessionDate}|${row.symbol}|${row.decisionTimeJst}`;

if(freezeReport.status!=='L2_SELECTOR_FROZEN'||freezeReport.freeze?.freezeSha256!=='e883168e49b0ee2cf75e4b5bb1053c170b1ca58621a50ff004cd0aa973bfdf15')throw new Error('unexpected or unfrozen L2 artifact');
if(freezeReport.sessionListSha256!==sessionsContract.sessionListSha256||freezeReport.audit?.validationOpened!==false||freezeReport.audit?.oosOpened!==false)throw new Error('sealed-partition or session identity mismatch');

function loadSession(partition,sessionDate,{retainBars=false}={}){
  const l0=loadFormalL0PartitionFromCache({cacheRoot,partition,plan,allocation}),sessionDir=path.join(base,sessionDate);
  const manifest=JSON.parse(fs.readFileSync(path.join(sessionDir,'l2-minute-manifest.json'),'utf8')),pages=JSON.parse(fs.readFileSync(path.join(sessionDir,'minute-pages.json'),'utf8'));
  if(manifest.sessionDate!==sessionDate||manifest.partition!==partition||manifest.sessionListSha256!==sessionsContract.sessionListSha256||pages.length!==manifest.pageCount||pages.some(page=>shaText(page.responseText)!==page.responseSha256))throw new Error(`immutable Minute cache mismatch: ${sessionDate}`);
  const minuteRows=pages.flatMap(page=>JSON.parse(page.responseText).data??[]),intraday=normalizeAndAggregateMinuteRows(minuteRows);
  const masterPages=JSON.parse(fs.readFileSync(path.join(sessionDir,'master-pages.json'),'utf8')),sectorBySymbol={};
  for(const row of masterPages.flatMap(page=>JSON.parse(page.responseText).data??[])){const symbol=codeOf(row);if(symbol)sectorBySymbol[`${sessionDate}|${symbol}`]=sectorOf(row);}
  const dailyRows=l0.rows.filter(row=>row.sessionDate===sessionDate),cross=buildL1CrossSectionDataset({partition,dailyRows,bars5m:intraday.bars,terminalAuctions:intraday.terminalAuctions,sectorBySymbol});
  const targets=buildFixedHorizonTargets({featureRows:cross.featureRows,bars5m:intraday.bars,evaluatorOnlyLabels:cross.evaluatorOnlyLabels}),targetKeys=new Set(targets.map(rowKey));
  return {features:cross.featureRows.filter(row=>targetKeys.has(rowKey(row))),targets,bars:retainBars?intraday.bars:[],pageCount:manifest.pageCount,rawRows:minuteRows.length};
}

function buildPartition(partition){
  const features=[],targets=[],audit=[];
  for(const sessionDate of allocation.partitions[partition]){
    const loaded=loadSession(partition,sessionDate);features.push(...loaded.features);targets.push(...loaded.targets);
    audit.push({sessionDate,pageCount:loaded.pageCount,rawRows:loaded.rawRows,featureRows:loaded.features.length});
    console.log(JSON.stringify({status:'INTEGRATION_SESSION_FEATURES_READY',partition,sessionDate,featureRows:loaded.features.length}));
  }
  return {partition,features,targets,audit};
}

const C=buildPartition('DEVELOPMENT_C'),D=buildPartition('DEVELOPMENT_D');
const selectedFeatureNames=freezeReport.freeze.selectedFeatureNames;
const cFit=fitL2Candidate({candidateId:freezeReport.freeze.selectedCandidate,featureRows:C.features,targetRows:C.targets,featureNames:selectedFeatureNames});
const newC=selectRanked({featureRows:C.features,artifact:freezeReport.freeze.finalArtifact,topN:freezeReport.freeze.topN});
const newD=selectRanked({featureRows:D.features,artifact:cFit,topN:freezeReport.freeze.topN});
const currentC=selectCurrentSelectorCandidates(C.features),currentD=selectCurrentSelectorCandidates(D.features);
const wanted=new Set([...newC,...newD,...currentC,...currentD].map(row=>`${row.sessionDate}|${row.symbol}`)),retainedBars=[];
for(const partition of ['DEVELOPMENT_C','DEVELOPMENT_D'])for(const sessionDate of allocation.partitions[partition]){
  const loaded=loadSession(partition,sessionDate,{retainBars:true});
  retainedBars.push(...loaded.bars.filter(bar=>wanted.has(`${bar.sessionDate}|${bar.symbol}`)));
  console.log(JSON.stringify({status:'INTEGRATION_REPLAY_BARS_READY',partition,sessionDate,retainedBars:retainedBars.length}));
}

const entryTraining=buildCurrentEntryTrainingRows({candidateRows:currentC,bars5m:retainedBars});
const currentEntry=fitCurrentEntryAdapter({trainingRowsByHorizon:entryTraining});
const currentAccepted=applyCurrentEntryLongOnly({candidateRows:currentD,bars5m:retainedBars,adapter:currentEntry});
const newAccepted=applyCurrentEntryLongOnly({candidateRows:newD,bars5m:retainedBars,adapter:currentEntry});
const currentTrades=replayCurrentExitLongOnly({entries:currentAccepted.accepted,bars5m:retainedBars});
const newTrades=replayCurrentExitLongOnly({entries:newAccepted.accepted,bars5m:retainedBars});

function portfolioSessions(trades){
  const bySession=new Map(allocation.partitions.DEVELOPMENT_D.map(date=>[date,[]]));
  for(const trade of trades)bySession.get(trade.sessionDate)?.push(trade);
  const barsBySessionSymbol=new Map();
  for(const bar of retainedBars.filter(x=>bySession.has(x.sessionDate))){
    const k=`${bar.sessionDate}|${bar.symbol}`;if(!barsBySessionSymbol.has(k))barsBySessionSymbol.set(k,[]);
    barsBySessionSymbol.get(k).push({timestamp:bar.availableAtJst,close:bar.close});
  }
  // Lane C requires the event-time mark to equal the actual fill. Current EXIT may fill an intrabar stop,
  // so replace only that symbol's exit-event mark with the exact frozen EXIT fill.
  for(const trade of trades){
    const k=`${trade.sessionDate}|${trade.symbol}`,rows=barsBySessionSymbol.get(k)??[],at=String(trade.exitTimestamp);
    const found=rows.find(row=>new Date(row.timestamp).toISOString()===new Date(at).toISOString());if(found)found.close=trade.exitPrice;
  }
  return [...bySession].map(([sessionDate,rows])=>{
    const symbols=new Set(rows.map(row=>row.symbol)),sessionBarsBySymbol={};
    for(const symbol of symbols)sessionBarsBySymbol[symbol]=(barsBySessionSymbol.get(`${sessionDate}|${symbol}`)??[]).sort((a,b)=>a.timestamp.localeCompare(b.timestamp));
    return {sessionDate,trades:rows.map(row=>({...row,symbol:`${row.symbol}.T`,sector:row.sector??'UNKNOWN'})),sessionBarsBySymbol};
  });
}

const profile=PHASE57_P25_LANE_C_ALLOCATION_PROFILES.find(x=>x.id==='MAX_10');
const currentPortfolio=simulateLaneCPortfolio({sessions:portfolioSessions(currentTrades),profile,managementMode:'CURRENT_FROZEN_RATCHET_EXIT',universeVariant:'CURRENT_SELECTOR_V1',roundTripCostPct:LONG_ONLY_CURRENT_INTEGRATION_CONTRACT.costPct});
const newPortfolio=simulateLaneCPortfolio({sessions:portfolioSessions(newTrades),profile,managementMode:'CURRENT_FROZEN_RATCHET_EXIT',universeVariant:'NEW_LONG_SELECTOR_FROZEN',roundTripCostPct:LONG_ONLY_CURRENT_INTEGRATION_CONTRACT.costPct});
const selectorMetrics={current:evaluateSelection({selected:currentD,targetRows:D.targets,horizon:6}),new:evaluateSelection({selected:newD,targetRows:D.targets,horizon:6})};
const report={
  schemaVersion:1,status:'INITIAL_CURRENT_ENTRY_EXIT_COMPARISON_COMPLETE_STOP',contract:LONG_ONLY_CURRENT_INTEGRATION_CONTRACT,
  source:{l2FreezeSha256:freezeReport.freeze.freezeSha256,l2ArtifactSha256:freezeReport.freeze.finalArtifact.artifactSha256,sessionListSha256:sessionsContract.sessionListSha256,evaluationPartition:'DEVELOPMENT_D',evaluationSessions:allocation.partitions.DEVELOPMENT_D,validationOpened:false,oosOpened:false},
  currentEntry:{...currentEntry.identity,artifactSha256:currentEntry.artifactSha256,selectionEligibleCount:currentEntry.picked?1:0,trainingRowsByHorizon:Object.fromEntries(Object.entries(entryTraining).map(([h,rows])=>[h,rows.length]))},
  selectorOnly:selectorMetrics,
  currentSystem:{selectorCandidates:currentD.length,entryAccepted:currentAccepted.accepted.length,entryBlocked:currentAccepted.blocked,currentExitTrades:currentTrades.length,portfolio:currentPortfolio},
  newLongSystem:{selectorCandidates:newD.length,entryAccepted:newAccepted.accepted.length,entryBlocked:newAccepted.blocked,currentExitTrades:newTrades.length,portfolio:newPortfolio,shortTrades:0,marginTrades:0,leverage:0},
  delta:{totalReturnPct:newPortfolio.return.totalReturnPct-currentPortfolio.return.totalReturnPct,realizedPnlJpy:newPortfolio.return.realizedPnlJpy-currentPortfolio.return.realizedPnlJpy,maxDrawdownPct:newPortfolio.risk.maxDrawdownPct-currentPortfolio.risk.maxDrawdownPct,profitFactor:(newPortfolio.trade.profitFactor??0)-(currentPortfolio.trade.profitFactor??0)},
  integrity:{sameDevelopmentDWindow:true,sameCurrentEntry:true,sameCurrentExit:true,sameCurrentAllocationMax10:true,sameCostModel:true,hundredShareLots:true,availableCashConstraint:true,selectorOutcomeNeverReachedEntry:true,currentEntryFitOnDevelopmentCOnly:true,developmentComparisonOnly:true,validationClaimAllowed:false,oosClaimAllowed:false,syntheticExitFillMarkOnlyForLaneCReconciliation:true,newEntryDeveloped:false,newExitDeveloped:false,stopAfterReport:true},
  safety:{executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,shortTrades:0,marginTrades:0,leverage:0},
};
report.reportSha256=sha(report);
fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,`${JSON.stringify(report,null,2)}\n`,{flag:'wx'});
console.log(JSON.stringify({status:report.status,currentReturnPct:currentPortfolio.return.totalReturnPct,newReturnPct:newPortfolio.return.totalReturnPct,deltaReturnPct:report.delta.totalReturnPct,currentTrades:currentPortfolio.trade.accepted,newTrades:newPortfolio.trade.accepted,reportSha256:report.reportSha256}));
