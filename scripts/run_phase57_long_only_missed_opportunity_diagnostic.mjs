import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {loadFormalL0PartitionFromCache} from '../predict/long-only/phase57-long-only-l0-cache.js';
import {normalizeAndAggregateMinuteRows} from '../predict/long-only/phase57-long-only-integrated-dataset.js';
import {buildL1CrossSectionDataset} from '../predict/long-only/phase57-long-only-l1-cross-section.js';
import {buildFixedHorizonTargets} from '../predict/long-only/phase57-long-only-l2-fixed-horizon.js';
import {fitL2Candidate} from '../predict/long-only/phase57-long-only-l2-selector-v1.js';
import {rankFrozenScore} from '../predict/long-only/phase57-long-only-selector-capacity-diagnostic.js';
import {diagnoseMissedOpportunities} from '../predict/long-only/phase57-long-only-missed-opportunity-diagnostic.js';

const arg=name=>{const index=process.argv.indexOf(name);return index<0?null:process.argv[index+1];};
const cacheRoot=path.resolve(arg('--cache-root')??''),freezePath=path.resolve(arg('--freeze-report')??''),output=path.resolve(arg('--output')??'');
if(!cacheRoot||!freezePath||!output)throw new Error('usage: --cache-root <private cache> --freeze-report <L2 report> --output <sanitized report>');
const plan=JSON.parse(fs.readFileSync(new URL('../predict/long-only/phase57-long-only-data-plan.json',import.meta.url),'utf8'));
const allocation=JSON.parse(fs.readFileSync(new URL('../predict/long-only/phase57-long-only-session-allocation-v3.json',import.meta.url),'utf8'));
const sessionsContract=JSON.parse(fs.readFileSync(new URL('../predict/long-only/phase57-long-only-l2-development-sessions.json',import.meta.url),'utf8'));
const freezeReport=JSON.parse(fs.readFileSync(freezePath,'utf8'));
const shaText=value=>createHash('sha256').update(value).digest('hex'),sha=value=>shaText(JSON.stringify(value));
const base=path.join(cacheRoot,'phase57-long-only','raw','jquants-v2');
const codeOf=row=>String(row?.Code??row?.code??row?.symbol??'').trim().toUpperCase();
const sectorOf=row=>String(row?.S17??row?.Sec17??row?.Sector17Code??row?.Sector33Code??row?.S33??row?.sectorCode??'UNKNOWN');
const rowKey=row=>`${row.sessionDate}|${row.symbol}|${row.decisionTimeJst}`;
const append=(target,source)=>{for(const row of source)target.push(row);};

if(freezeReport.status!=='L2_SELECTOR_FROZEN'||freezeReport.freeze?.freezeSha256!=='e883168e49b0ee2cf75e4b5bb1053c170b1ca58621a50ff004cd0aa973bfdf15')throw new Error('unexpected Candidate v1 freeze evidence');
if(freezeReport.audit?.validationOpened!==false||freezeReport.audit?.oosOpened!==false)throw new Error('sealed partition violation');

function loadSession(partition,sessionDate){
  const l0=loadFormalL0PartitionFromCache({cacheRoot,partition,plan,allocation}),sessionDir=path.join(base,sessionDate);
  const manifest=JSON.parse(fs.readFileSync(path.join(sessionDir,'l2-minute-manifest.json'),'utf8')),pages=JSON.parse(fs.readFileSync(path.join(sessionDir,'minute-pages.json'),'utf8'));
  if(manifest.sessionDate!==sessionDate||manifest.partition!==partition||manifest.sessionListSha256!==sessionsContract.sessionListSha256||pages.length!==manifest.pageCount||pages.some(page=>shaText(page.responseText)!==page.responseSha256))throw new Error(`immutable Minute cache mismatch: ${sessionDate}`);
  const minuteRows=pages.flatMap(page=>JSON.parse(page.responseText).data??[]),intraday=normalizeAndAggregateMinuteRows(minuteRows);
  const masterPages=JSON.parse(fs.readFileSync(path.join(sessionDir,'master-pages.json'),'utf8')),sectorBySymbol={};
  for(const row of masterPages.flatMap(page=>JSON.parse(page.responseText).data??[])){const symbol=codeOf(row);if(symbol)sectorBySymbol[`${sessionDate}|${symbol}`]=sectorOf(row);}
  const dailyRows=l0.rows.filter(row=>row.sessionDate===sessionDate),cross=buildL1CrossSectionDataset({partition,dailyRows,bars5m:intraday.bars,terminalAuctions:intraday.terminalAuctions,sectorBySymbol});
  const targets=buildFixedHorizonTargets({featureRows:cross.featureRows,bars5m:intraday.bars,evaluatorOnlyLabels:cross.evaluatorOnlyLabels}),targetKeys=new Set(targets.map(rowKey));
  return {features:cross.featureRows.filter(row=>targetKeys.has(rowKey(row))),targets,bars:intraday.bars,audit:{sessionDate,pageCount:manifest.pageCount,rawRows:minuteRows.length,featureRows:cross.featureRows.length,targetRows:targets.length,corporateActionExclusions:cross.audit.exclusions.CORPORATE_ACTION_UNRESOLVED}};
}

const barVwap=bars=>{const volume=bars.reduce((sum,bar)=>sum+(Number(bar.volume)||0),0),turnover=bars.reduce((sum,bar)=>sum+(Number(bar.turnover)||0),0);return volume>0&&turnover>0?turnover/volume:null;};
function addEvaluationDiagnostics(features,targets,bars){
  const bySymbol=new Map();for(const bar of bars){if(!bySymbol.has(bar.symbol))bySymbol.set(bar.symbol,[]);bySymbol.get(bar.symbol).push(bar);}for(const rows of bySymbol.values())rows.sort((a,b)=>a.availableAtJst.localeCompare(b.availableAtJst));
  const targetMap=new Map(targets.map(target=>[rowKey(target),target])),outFeatures=[],outTargets=[];
  for(const feature of features){
    const rows=bySymbol.get(feature.symbol)??[];let index=rows.findIndex(row=>row.availableAtJst===feature.decisionAtJst);if(index<0)index=rows.findLastIndex(row=>row.availableAtJst<=feature.decisionAtJst);
    const target=targetMap.get(rowKey(feature));if(index<0||!target)continue;
    const observed=rows.slice(0,index+1),prior=observed.slice(0,-1),currentVwap=barVwap(observed),priorVwap=barVwap(prior),vwapReclaim5m=Boolean(prior.length&&priorVwap&&currentVwap&&Number(prior.at(-1).close)<priorVwap&&Number(observed.at(-1).close)>=currentVwap);
    const path30=rows.slice(index+1,index+7);let timeToMfe30Minutes=null;
    if(path30.length){const maximum=Math.max(...path30.map(row=>Number(row.high))),mfeBar=path30.find(row=>Number(row.high)===maximum);timeToMfe30Minutes=(new Date(mfeBar.availableAtJst)-new Date(feature.decisionAtJst))/60000;}
    outFeatures.push(Object.freeze({...feature,vwapReclaim5m}));outTargets.push(Object.freeze({...target,timeToMfe30Minutes}));
  }
  return {features:Object.freeze(outFeatures),targets:Object.freeze(outTargets)};
}

const C={features:[],targets:[]},D={features:[],targets:[],audit:[]};
for(const sessionDate of allocation.partitions.DEVELOPMENT_C){
  const loaded=loadSession('DEVELOPMENT_C',sessionDate);append(C.features,loaded.features);append(C.targets,loaded.targets);
  console.log(JSON.stringify({status:'MISSED_DIAGNOSTIC_C_SCORE_RECONSTRUCTION',sessionDate,featureRows:loaded.features.length}));
}
for(const sessionDate of allocation.partitions.DEVELOPMENT_D){
  const loaded=loadSession('DEVELOPMENT_D',sessionDate),augmented=addEvaluationDiagnostics(loaded.features,loaded.targets,loaded.bars);append(D.features,augmented.features);append(D.targets,augmented.targets);D.audit.push(loaded.audit);
  console.log(JSON.stringify({status:'MISSED_DIAGNOSTIC_D_READY',sessionDate,featureRows:augmented.features.length}));
}

const cFit=fitL2Candidate({candidateId:freezeReport.freeze.selectedCandidate,featureRows:C.features,targetRows:C.targets,featureNames:freezeReport.freeze.selectedFeatureNames});
const frozenCandidate=freezeReport.freeze.allCandidates.find(row=>row.candidateId===freezeReport.freeze.selectedCandidate&&row.topN===freezeReport.freeze.topN&&row.horizonBars===freezeReport.freeze.horizonBars);
if(!frozenCandidate||cFit.artifactSha256!==frozenCandidate.fitArtifactSha256)throw new Error('reconstructed Development C score differs from fixed Candidate v1 evidence');
const ranked=rankFrozenScore({featureRows:D.features,targetRows:D.targets,artifact:cFit});
const diagnostic=diagnoseMissedOpportunities({ranked,oldSelectors:{OLD_SELECTOR_COMPLEMENTARITY:{status:'UNAVAILABLE',reason:'CANCELLED_BY_OPERATOR_AS_OUT_OF_SCOPE'}}});
const report={
  schemaVersion:1,status:'MISSED_OPPORTUNITY_DIAGNOSTIC_COMPLETE_STOP',selectorState:'CANDIDATE_V1_DIAGNOSTIC',
  source:{l2FreezeSha256:freezeReport.freeze.freezeSha256,developmentCArtifactSha256:cFit.artifactSha256,artifactMatch:true,selectedCandidate:freezeReport.freeze.selectedCandidate,selectedFeatureNames:freezeReport.freeze.selectedFeatureNames,horizonBars:freezeReport.freeze.horizonBars,barSemantics:'6_CLOSED_5M_BARS_EQUALS_30_TRADING_MINUTES',evaluationPartition:'DEVELOPMENT_D',evaluationSessions:allocation.partitions.DEVELOPMENT_D,sessionListSha256:sessionsContract.sessionListSha256,jquantsRequests:0,oldSelectorComplementarity:'CANCELLED_BY_OPERATOR_AS_OUT_OF_SCOPE'},
  diagnostic,
  definitions:{relativeVolumePercentile:'WITHIN_DECISION_CROSS_SECTION_PERCENTILE_OF_CAUSAL_CUMULATIVE_VOLUME; NOT A HISTORICAL_AVERAGE RVOL',vwapReclaim5m:'PRIOR_CLOSED_5M_BAR_BELOW_PRIOR_CAUSAL_CUMULATIVE_VWAP_AND_DECISION_BAR_CLOSE_AT_OR_ABOVE_CURRENT_CAUSAL_CUMULATIVE_VWAP',ordinaryControl:'DETERMINISTIC_TIME_MATCHED_SAMPLE_OF_RANK_GT_20_AND_Y30_LT_50_BPS',archetypes:'FIXED_WITHIN_DECISION_PERCENTILE_RULES; DIAGNOSTIC_ONLY; NOT A SELECTOR POLICY'},
  audit:{developmentCFeatureRows:C.features.length,developmentCTargetRows:C.targets.length,developmentDFeatureRows:D.features.length,developmentDTargetRows:D.targets.length,developmentDRankedRows:ranked.length,decisionCount:new Set(ranked.map(row=>`${row.feature.sessionDate}|${row.feature.decisionTimeJst}`)).size,sessions:D.audit,featureCutoffPhysical:true,outcomeFieldsUsedOnlyForCohortAndEvaluation:true,modelWeightsChanged:false,featuresChanged:false,targetChanged:false,topNChanged:false,thresholdTuned:false,entryChanged:false,exitChanged:false,allocationChanged:false,validationOpened:false,oosOpened:false},
  safety:{executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,shortTrades:0,marginTrades:0,leverage:0},
};
report.reportSha256=sha(report);fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,`${JSON.stringify(report,null,2)}\n`,{flag:'wx'});
console.log(JSON.stringify({status:report.status,cohorts:Object.fromEntries(Object.entries(report.diagnostic.featureContrast.cohorts).map(([name,value])=>[name,value.n])),archetype100:Object.fromEntries(Object.entries(report.diagnostic.archetypes.GE_100_BPS.exclusive).map(([name,value])=>[name,value.count])),archetype200:Object.fromEntries(Object.entries(report.diagnostic.archetypes.GE_200_BPS.exclusive).map(([name,value])=>[name,value.count])),reportSha256:report.reportSha256}));
