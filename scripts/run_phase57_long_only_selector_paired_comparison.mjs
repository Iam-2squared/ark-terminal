import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {loadFormalL0PartitionFromCache} from '../predict/long-only/phase57-long-only-l0-cache.js';
import {normalizeAndAggregateMinuteRows} from '../predict/long-only/phase57-long-only-integrated-dataset.js';
import {buildL1CrossSectionDataset} from '../predict/long-only/phase57-long-only-l1-cross-section.js';
import {buildFixedHorizonTargets} from '../predict/long-only/phase57-long-only-l2-fixed-horizon.js';
import {fitL2Candidate,selectRanked} from '../predict/long-only/phase57-long-only-l2-selector-v1.js';
import {selectCurrentSelectorCandidates} from '../predict/long-only/phase57-long-only-current-integration.js';
import {scorePhase57SelectorV3CrossSection,selectPhase57SelectorV3} from '../predict/daytrade/phase57-selector-v3.js';
import {runPhase57MinimalHybrid} from '../predict/daytrade/phase57-selector-minimal-hybrid.js';
import {PAIRED_SELECTOR_COMPARISON_CONTRACT,equalBudgetTopN,summarizeFrozenSelector} from '../predict/long-only/phase57-long-only-selector-paired-comparison.js';

const arg=name=>{const i=process.argv.indexOf(name);return i<0?null:process.argv[i+1];};
const cacheRoot=path.resolve(arg('--cache-root')??''),freezePath=path.resolve(arg('--freeze-report')??''),output=path.resolve(arg('--output')??'');
if(!cacheRoot||!freezePath||!output)throw new Error('usage: --cache-root <private cache> --freeze-report <L2 report> --output <sanitized report>');
const plan=JSON.parse(fs.readFileSync(new URL('../predict/long-only/phase57-long-only-data-plan.json',import.meta.url),'utf8'));
const allocation=JSON.parse(fs.readFileSync(new URL('../predict/long-only/phase57-long-only-session-allocation-v3.json',import.meta.url),'utf8'));
const sessionsContract=JSON.parse(fs.readFileSync(new URL('../predict/long-only/phase57-long-only-l2-development-sessions.json',import.meta.url),'utf8'));
const freezeReport=JSON.parse(fs.readFileSync(freezePath,'utf8'));
const hybridModel=JSON.parse(fs.readFileSync(new URL('../predict/research/phase57-selector-minimal-hybrid-development-model.json',import.meta.url),'utf8'));
const shaText=value=>createHash('sha256').update(value).digest('hex');
const sha=value=>shaText(JSON.stringify(value));
const base=path.join(cacheRoot,'phase57-long-only','raw','jquants-v2');
const codeOf=row=>String(row?.Code??row?.code??row?.symbol??'').trim().toUpperCase();
const sectorOf=row=>String(row?.S17??row?.Sec17??row?.Sector17Code??row?.Sector33Code??row?.S33??row?.sectorCode??'UNKNOWN');
const rowKey=row=>`${row.sessionDate}|${row.symbol}|${row.decisionTimeJst}`;
const selectorSourceRef='research/phase57-selector-v1-v3-minimal-hybrid@c70cb168358b1aedd9785a18ca76fde1832d7a53';

if(freezeReport.status!=='L2_SELECTOR_FROZEN'||freezeReport.freeze?.freezeSha256!=='e883168e49b0ee2cf75e4b5bb1053c170b1ca58621a50ff004cd0aa973bfdf15')throw new Error('unexpected or unfrozen L2 artifact');
if(freezeReport.audit?.validationOpened!==false||freezeReport.audit?.oosOpened!==false)throw new Error('sealed partition violation');
if(hybridModel.modelDigest!=='444e296d31b0e59263f268706b4c8a7c7e9e59d6f7c9547e9f90342a24040fc2')throw new Error('Minimal Hybrid frozen model mismatch');

function loadSession(partition,sessionDate){
  const l0=loadFormalL0PartitionFromCache({cacheRoot,partition,plan,allocation}),sessionDir=path.join(base,sessionDate);
  const manifest=JSON.parse(fs.readFileSync(path.join(sessionDir,'l2-minute-manifest.json'),'utf8')),pages=JSON.parse(fs.readFileSync(path.join(sessionDir,'minute-pages.json'),'utf8'));
  if(manifest.sessionDate!==sessionDate||manifest.partition!==partition||manifest.sessionListSha256!==sessionsContract.sessionListSha256||pages.length!==manifest.pageCount||pages.some(page=>shaText(page.responseText)!==page.responseSha256))throw new Error(`immutable Minute cache mismatch: ${sessionDate}`);
  const minuteRows=pages.flatMap(page=>JSON.parse(page.responseText).data??[]),intraday=normalizeAndAggregateMinuteRows(minuteRows);
  const masterPages=JSON.parse(fs.readFileSync(path.join(sessionDir,'master-pages.json'),'utf8')),sectorBySymbol={};
  for(const row of masterPages.flatMap(page=>JSON.parse(page.responseText).data??[])){const symbol=codeOf(row);if(symbol)sectorBySymbol[`${sessionDate}|${symbol}`]=sectorOf(row);}
  const dailyRows=l0.rows.filter(row=>row.sessionDate===sessionDate),cross=buildL1CrossSectionDataset({partition,dailyRows,bars5m:intraday.bars,terminalAuctions:intraday.terminalAuctions,sectorBySymbol});
  const targets=buildFixedHorizonTargets({featureRows:cross.featureRows,bars5m:intraday.bars,evaluatorOnlyLabels:cross.evaluatorOnlyLabels}),targetKeys=new Set(targets.map(rowKey));
  return {features:cross.featureRows.filter(row=>targetKeys.has(rowKey(row))),targets,bars:intraday.bars,audit:{sessionDate,pageCount:manifest.pageCount,rawRows:minuteRows.length,featureRows:cross.featureRows.length,corporateActionExclusions:cross.audit.exclusions.CORPORATE_ACTION_UNRESOLVED}};
}

const append=(target,source)=>{for(const row of source)target.push(row);};
const C={features:[],targets:[]},D={features:[],targets:[],bars:[],audit:[]},previousTail=new Map();
for(const sessionDate of allocation.partitions.DEVELOPMENT_C){
  const loaded=loadSession('DEVELOPMENT_C',sessionDate);append(C.features,loaded.features);append(C.targets,loaded.targets);
  const grouped=new Map();for(const bar of loaded.bars){if(!grouped.has(bar.symbol))grouped.set(bar.symbol,[]);grouped.get(bar.symbol).push(bar);}
  for(const [symbol,bars] of grouped)previousTail.set(symbol,bars.sort((a,b)=>a.availableAtJst.localeCompare(b.availableAtJst)).slice(-12).map(bar=>({timestamp:bar.barStartJst,availableAt:bar.availableAtJst,sessionDate:bar.sessionDate,open:bar.open,high:bar.high,low:bar.low,close:bar.close,volume:bar.volume,turnover:bar.turnover})));
  console.log(JSON.stringify({status:'PAIRED_C_FIT_READY',sessionDate,featureRows:loaded.features.length}));
}
for(const sessionDate of allocation.partitions.DEVELOPMENT_D){const loaded=loadSession('DEVELOPMENT_D',sessionDate);append(D.features,loaded.features);append(D.targets,loaded.targets);append(D.bars,loaded.bars);D.audit.push(loaded.audit);console.log(JSON.stringify({status:'PAIRED_D_READY',sessionDate,featureRows:loaded.features.length}));}

const cFit=fitL2Candidate({candidateId:freezeReport.freeze.selectedCandidate,featureRows:C.features,targetRows:C.targets,featureNames:freezeReport.freeze.selectedFeatureNames});
const newNative=selectRanked({featureRows:D.features,artifact:cFit,topN:freezeReport.freeze.topN});
const v1Native=selectCurrentSelectorCandidates(D.features);
const featuresByPoint=new Map();for(const row of D.features){const k=`${row.sessionDate}|${row.decisionTimeJst}`;if(!featuresByPoint.has(k))featuresByPoint.set(k,[]);featuresByPoint.get(k).push(row);}
const barsBySessionSymbol=new Map();for(const bar of D.bars){const k=`${bar.sessionDate}|${bar.symbol}`;if(!barsBySessionSymbol.has(k))barsBySessionSymbol.set(k,[]);barsBySessionSymbol.get(k).push(bar);}for(const rows of barsBySessionSymbol.values())rows.sort((a,b)=>a.availableAtJst.localeCompare(b.availableAtJst));
const v3Native=[],v3Ranked=[],hybridNative=[],hybridRanked=[];
const oldBar=bar=>({timestamp:bar.barStartJst,availableAt:bar.availableAtJst,sessionDate:bar.sessionDate,open:bar.open,high:bar.high,low:bar.low,close:bar.close,volume:bar.volume,turnover:bar.turnover});
const attach=(picks,source,scoreField,rankField)=>picks.flatMap(pick=>{const row=source.get(String(pick.symbol));return row?[Object.freeze({...row,selectorScore:Number(pick[scoreField]),selectorRank:Number(pick[rankField])})]:[];});

for(const sessionDate of allocation.partitions.DEVELOPMENT_D){
  const pointKeys=[...featuresByPoint.keys()].filter(k=>k.startsWith(`${sessionDate}|`)).sort();
  for(const pointKey of pointKeys){
    const rows=featuresByPoint.get(pointKey),source=new Map(rows.map(row=>[String(row.symbol),row])),cutoff=rows[0].decisionAtJst;
    const entries=rows.map(row=>({symbol:row.symbol,sector:row.sector??'UNKNOWN',market:row.segment,bars:[...(previousTail.get(row.symbol)??[]),...(barsBySessionSymbol.get(`${sessionDate}|${row.symbol}`)??[]).filter(bar=>bar.availableAtJst<=cutoff).map(oldBar)]}));
    const scoredV3=scorePhase57SelectorV3CrossSection({featureCutoff:cutoff,entries}),selectedV3=selectPhase57SelectorV3({featureCutoff:cutoff,entries,threshold:PAIRED_SELECTOR_COMPARISON_CONTRACT.v3Threshold});
    const hybrid=runPhase57MinimalHybrid({featureCutoff:cutoff,entries,model:hybridModel,baselineDiagnostics:{v3SelectedSymbols:selectedV3.selected.map(row=>row.symbol)}});
    v3Native.push(...attach(selectedV3.selected,source,'utilityScore','rank'));v3Ranked.push(...attach(scoredV3.ranked,source,'utilityScore','rank'));
    hybridNative.push(...attach(hybrid.selected,source,'hybridScore','hybridRank'));hybridRanked.push(...attach(hybrid.ranked,source,'hybridScore','hybridRank'));
  }
  for(const [key,bars] of barsBySessionSymbol)if(key.startsWith(`${sessionDate}|`))previousTail.set(key.split('|')[1],bars.slice(-12).map(oldBar));
}

const native={NEW_LONG:newNative,CURRENT_V1:v1Native,FROZEN_V3:v3Native,FROZEN_MINIMAL_HYBRID:hybridNative};
const equalBudget={NEW_LONG:equalBudgetTopN(newNative),CURRENT_V1:equalBudgetTopN(v1Native),FROZEN_V3:equalBudgetTopN(v3Ranked),FROZEN_MINIMAL_HYBRID:equalBudgetTopN(hybridRanked)};
const metrics=sets=>Object.fromEntries(Object.entries(sets).map(([name,selected])=>[name,summarizeFrozenSelector({selected,targetRows:D.targets})]));
const report={schemaVersion:1,status:'FROZEN_SELECTOR_PAIRED_COMPARISON_COMPLETE_STOP',contract:PAIRED_SELECTOR_COMPARISON_CONTRACT,source:{selectorSourceRef,l2FreezeSha256:freezeReport.freeze.freezeSha256,newSelectorFitPartition:'DEVELOPMENT_C',evaluationPartition:'DEVELOPMENT_D',evaluationSessions:allocation.partitions.DEVELOPMENT_D,sessionListSha256:sessionsContract.sessionListSha256,v3Threshold:0.70,minimalHybridModelDigest:hybridModel.modelDigest,jquantsRequests:0},native:metrics(native),equalBudgetTop5:metrics(equalBudget),audit:{developmentCFeatureRows:C.features.length,developmentDFeatureRows:D.features.length,developmentDTargetRows:D.targets.length,sessions:D.audit,featureCutoffPhysical:true,oldSelectorSourceCopiedWithoutSemanticChange:true,validationOpened:false,oosOpened:false,newSelectorChanged:false,oldSelectorsChanged:false},safety:{executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,shortTrades:0,marginTrades:0,leverage:0}};
report.reportSha256=sha(report);fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,`${JSON.stringify(report,null,2)}\n`,{flag:'wx'});
console.log(JSON.stringify({status:report.status,native:Object.fromEntries(Object.entries(report.native).map(([k,v])=>[k,{n:v.candidateCount,meanBps:v.meanFutureReturnBps,positiveRatePct:v.positiveRatePct}])),equalBudgetTop5:Object.fromEntries(Object.entries(report.equalBudgetTop5).map(([k,v])=>[k,{n:v.candidateCount,meanBps:v.meanFutureReturnBps,positiveRatePct:v.positiveRatePct}])),reportSha256:report.reportSha256}));
