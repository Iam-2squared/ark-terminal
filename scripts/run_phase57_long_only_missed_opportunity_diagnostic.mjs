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
import {selectCurrentSelectorCandidates} from '../predict/long-only/phase57-long-only-current-integration.js';
import {scorePhase57SelectorV3CrossSection,selectPhase57SelectorV3} from '../predict/daytrade/phase57-selector-v3.js';
import {runPhase57MinimalHybrid} from '../predict/daytrade/phase57-selector-minimal-hybrid.js';
import {PAIRED_SELECTOR_COMPARISON_CONTRACT} from '../predict/long-only/phase57-long-only-selector-paired-comparison.js';

const arg=name=>{const index=process.argv.indexOf(name);return index<0?null:process.argv[index+1];};
const cacheRoot=path.resolve(arg('--cache-root')??''),freezePath=path.resolve(arg('--freeze-report')??''),output=path.resolve(arg('--output')??'');
if(!cacheRoot||!freezePath||!output)throw new Error('usage: --cache-root <private cache> --freeze-report <L2 report> --output <sanitized report>');
const plan=JSON.parse(fs.readFileSync(new URL('../predict/long-only/phase57-long-only-data-plan.json',import.meta.url),'utf8'));
const allocation=JSON.parse(fs.readFileSync(new URL('../predict/long-only/phase57-long-only-session-allocation-v3.json',import.meta.url),'utf8'));
const sessionsContract=JSON.parse(fs.readFileSync(new URL('../predict/long-only/phase57-long-only-l2-development-sessions.json',import.meta.url),'utf8'));
const freezeReport=JSON.parse(fs.readFileSync(freezePath,'utf8'));
const hybridModel=JSON.parse(fs.readFileSync(new URL('../predict/research/phase57-selector-minimal-hybrid-development-model.json',import.meta.url),'utf8'));
const shaText=value=>createHash('sha256').update(value).digest('hex'),sha=value=>shaText(JSON.stringify(value));
const base=path.join(cacheRoot,'phase57-long-only','raw','jquants-v2');
const codeOf=row=>String(row?.Code??row?.code??row?.symbol??'').trim().toUpperCase();
const sectorOf=row=>String(row?.S17??row?.Sec17??row?.Sector17Code??row?.Sector33Code??row?.S33??row?.sectorCode??'UNKNOWN');
const rowKey=row=>`${row.sessionDate}|${row.symbol}|${row.decisionTimeJst}`;
const append=(target,source)=>{for(const row of source)target.push(row);};

if(freezeReport.status!=='L2_SELECTOR_FROZEN'||freezeReport.freeze?.freezeSha256!=='e883168e49b0ee2cf75e4b5bb1053c170b1ca58621a50ff004cd0aa973bfdf15')throw new Error('unexpected Candidate v1 freeze evidence');
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

const C={features:[],targets:[]},D={features:[],targets:[],bars:[],audit:[]},previousTail=new Map();
const oldBar=bar=>({timestamp:bar.barStartJst,availableAt:bar.availableAtJst,sessionDate:bar.sessionDate,open:bar.open,high:bar.high,low:bar.low,close:bar.close,volume:bar.volume,turnover:bar.turnover});
for(const sessionDate of allocation.partitions.DEVELOPMENT_C){
  const loaded=loadSession('DEVELOPMENT_C',sessionDate);append(C.features,loaded.features);append(C.targets,loaded.targets);
  const grouped=new Map();for(const bar of loaded.bars){if(!grouped.has(bar.symbol))grouped.set(bar.symbol,[]);grouped.get(bar.symbol).push(bar);}for(const [symbol,bars] of grouped)previousTail.set(symbol,bars.sort((a,b)=>a.availableAtJst.localeCompare(b.availableAtJst)).slice(-12).map(oldBar));
  console.log(JSON.stringify({status:'MISSED_DIAGNOSTIC_C_SCORE_RECONSTRUCTION',sessionDate,featureRows:loaded.features.length}));
}
for(const sessionDate of allocation.partitions.DEVELOPMENT_D){
  const loaded=loadSession('DEVELOPMENT_D',sessionDate),augmented=addEvaluationDiagnostics(loaded.features,loaded.targets,loaded.bars);append(D.features,augmented.features);append(D.targets,augmented.targets);append(D.bars,loaded.bars);D.audit.push(loaded.audit);
  console.log(JSON.stringify({status:'MISSED_DIAGNOSTIC_D_READY',sessionDate,featureRows:augmented.features.length}));
}

const cFit=fitL2Candidate({candidateId:freezeReport.freeze.selectedCandidate,featureRows:C.features,targetRows:C.targets,featureNames:freezeReport.freeze.selectedFeatureNames});
const frozenCandidate=freezeReport.freeze.allCandidates.find(row=>row.candidateId===freezeReport.freeze.selectedCandidate&&row.topN===freezeReport.freeze.topN&&row.horizonBars===freezeReport.freeze.horizonBars);
if(!frozenCandidate||cFit.artifactSha256!==frozenCandidate.fitArtifactSha256)throw new Error('reconstructed Development C score differs from fixed Candidate v1 evidence');
const ranked=rankFrozenScore({featureRows:D.features,targetRows:D.targets,artifact:cFit});

const currentV1Selected=selectCurrentSelectorCandidates(D.features),featuresByPoint=new Map();for(const row of D.features){const k=`${row.sessionDate}|${row.decisionTimeJst}`;if(!featuresByPoint.has(k))featuresByPoint.set(k,[]);featuresByPoint.get(k).push(row);}
const barsBySessionSymbol=new Map();for(const bar of D.bars){const k=`${bar.sessionDate}|${bar.symbol}`;if(!barsBySessionSymbol.has(k))barsBySessionSymbol.set(k,[]);barsBySessionSymbol.get(k).push(bar);}for(const rows of barsBySessionSymbol.values())rows.sort((a,b)=>a.availableAtJst.localeCompare(b.availableAtJst));
const v3Selected=[],v3Ranked=[],hybridSelected=[],hybridRanked=[];
const attach=(picks,source,scoreField,rankField)=>picks.flatMap(pick=>{const row=source.get(String(pick.symbol));return row?[Object.freeze({...row,selectorScore:Number(pick[scoreField]),selectorRank:Number(pick[rankField])})]:[];});
for(const sessionDate of allocation.partitions.DEVELOPMENT_D){
  const pointKeys=[...featuresByPoint.keys()].filter(k=>k.startsWith(`${sessionDate}|`)).sort();
  for(const point of pointKeys){
    const rows=featuresByPoint.get(point),source=new Map(rows.map(row=>[String(row.symbol),row])),cutoff=rows[0].decisionAtJst;
    const entries=rows.map(row=>({symbol:row.symbol,sector:row.sector??'UNKNOWN',market:row.segment,bars:[...(previousTail.get(row.symbol)??[]),...(barsBySessionSymbol.get(`${sessionDate}|${row.symbol}`)??[]).filter(bar=>bar.availableAtJst<=cutoff).map(oldBar)]}));
    const scoredV3=scorePhase57SelectorV3CrossSection({featureCutoff:cutoff,entries}),selectedV3=selectPhase57SelectorV3({featureCutoff:cutoff,entries,threshold:PAIRED_SELECTOR_COMPARISON_CONTRACT.v3Threshold});
    const hybrid=runPhase57MinimalHybrid({featureCutoff:cutoff,entries,model:hybridModel,baselineDiagnostics:{v3SelectedSymbols:selectedV3.selected.map(row=>row.symbol)}});
    append(v3Selected,attach(selectedV3.selected,source,'utilityScore','rank'));append(v3Ranked,attach(scoredV3.ranked,source,'utilityScore','rank'));append(hybridSelected,attach(hybrid.selected,source,'hybridScore','hybridRank'));append(hybridRanked,attach(hybrid.ranked,source,'hybridScore','hybridRank'));
  }
  for(const [identity,bars] of barsBySessionSymbol)if(identity.startsWith(`${sessionDate}|`))previousTail.set(identity.split('|')[1],bars.slice(-12).map(oldBar));
}

const oldSelectors={
  CURRENT_V1:{status:'AVAILABLE',selectedRows:currentV1Selected,rankedRows:currentV1Selected},
  FROZEN_V3:{status:'AVAILABLE',selectedRows:v3Selected,rankedRows:v3Ranked},
  CURRENT_FROZEN_MINIMAL_HYBRID:{status:'AVAILABLE',selectedRows:hybridSelected,rankedRows:hybridRanked},
};
const diagnostic=diagnoseMissedOpportunities({ranked,oldSelectors});
const report={
  schemaVersion:1,status:'MISSED_OPPORTUNITY_DIAGNOSTIC_COMPLETE_STOP',selectorState:'CANDIDATE_V1_DIAGNOSTIC',
  source:{l2FreezeSha256:freezeReport.freeze.freezeSha256,developmentCArtifactSha256:cFit.artifactSha256,artifactMatch:true,selectedCandidate:freezeReport.freeze.selectedCandidate,selectedFeatureNames:freezeReport.freeze.selectedFeatureNames,horizonBars:freezeReport.freeze.horizonBars,barSemantics:'6_CLOSED_5M_BARS_EQUALS_30_TRADING_MINUTES',evaluationPartition:'DEVELOPMENT_D',evaluationSessions:allocation.partitions.DEVELOPMENT_D,sessionListSha256:sessionsContract.sessionListSha256,jquantsRequests:0,oldSelectorSourceRef:'research/phase57-selector-v1-v3-minimal-hybrid@c70cb168358b1aedd9785a18ca76fde1832d7a53'},
  diagnostic,
  definitions:{relativeVolumePercentile:'WITHIN_DECISION_CROSS_SECTION_PERCENTILE_OF_CAUSAL_CUMULATIVE_VOLUME; NOT A HISTORICAL_AVERAGE RVOL',vwapReclaim5m:'PRIOR_CLOSED_5M_BAR_BELOW_PRIOR_CAUSAL_CUMULATIVE_VWAP_AND_DECISION_BAR_CLOSE_AT_OR_ABOVE_CURRENT_CAUSAL_CUMULATIVE_VWAP',ordinaryControl:'DETERMINISTIC_TIME_MATCHED_SAMPLE_OF_RANK_GT_20_AND_Y30_LT_50_BPS',archetypes:'FIXED_WITHIN_DECISION_PERCENTILE_RULES; DIAGNOSTIC_ONLY; NOT A SELECTOR POLICY'},
  audit:{developmentCFeatureRows:C.features.length,developmentCTargetRows:C.targets.length,developmentDFeatureRows:D.features.length,developmentDTargetRows:D.targets.length,developmentDRankedRows:ranked.length,decisionCount:new Set(ranked.map(row=>`${row.feature.sessionDate}|${row.feature.decisionTimeJst}`)).size,sessions:D.audit,featureCutoffPhysical:true,outcomeFieldsUsedOnlyForCohortAndEvaluation:true,modelWeightsChanged:false,featuresChanged:false,targetChanged:false,topNChanged:false,thresholdTuned:false,entryChanged:false,exitChanged:false,allocationChanged:false,validationOpened:false,oosOpened:false},
  safety:{executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,shortTrades:0,marginTrades:0,leverage:0},
};
report.reportSha256=sha(report);fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,`${JSON.stringify(report,null,2)}\n`,{flag:'wx'});
console.log(JSON.stringify({status:report.status,cohorts:Object.fromEntries(Object.entries(report.diagnostic.featureContrast.cohorts).map(([name,value])=>[name,value.n])),archetype100:Object.fromEntries(Object.entries(report.diagnostic.archetypes.GE_100_BPS.exclusive).map(([name,value])=>[name,value.count])),archetype200:Object.fromEntries(Object.entries(report.diagnostic.archetypes.GE_200_BPS.exclusive).map(([name,value])=>[name,value.count])),reportSha256:report.reportSha256}));
