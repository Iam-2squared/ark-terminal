import fs from 'node:fs';
import path from 'node:path';
import {buildProspectiveP21HistoricalRows} from '../predict/daytrade/phase57-p21-prospective-history.js';
import {buildProspectiveP21FeatureFeed} from '../predict/daytrade/phase57-p21-prospective-feature-feed.js';
import {buildProspectiveP21FrozenDecision} from '../predict/daytrade/phase57-p21-prospective-frozen-base.js';
import {buildFrozenPhase57SnapshotFromRuntimeDecision} from '../predict/scalping/phase58-phase57-runtime-adapter.js';
import {PHASE58_P13_FROZEN_POLICY} from '../predict/scalping/phase58-phase57-prospective-pipeline.js';
import {buildP25DataDrivenExitAnalogPool} from '../predict/daytrade/phase57-p25-data-driven-exit.js';
import {simulateP25ExitV3DualGate,P25_EXIT_V3_DUAL_GATE_POLICY_SHA256} from '../predict/daytrade/phase57-p25-exit-v3-dual-gate.js';
import {simulateP25ExitV4,P25_EXIT_V4_POLICY_SHA256,P25_EXIT_V4_POLICY} from '../predict/daytrade/phase57-p25-exit-v4-structural-risk.js';
import {P25_EXIT_V3_INDEPENDENT_PROTOCOL,P25_EXIT_V3_SAFETY} from '../predict/daytrade/phase57-p25-exit-v3-independent-protocol.js';
import {simulateLaneCPortfolio,PHASE57_P25_LANE_C_ALLOCATION_PROFILES,PHASE57_P25_LANE_C_SAFETY} from '../predict/portfolio/phase57-p25-lane-c-portfolio-simulator.js';

const arg=(n,f=null)=>{const i=process.argv.indexOf(n);return i>=0&&i+1<process.argv.length?process.argv[i+1]:f;};
const bundlePath=arg('--bundle'),historyPath=arg('--history-pack'),output=arg('--output','tmp/p25-dynamic5m-challenger-matrix.json');
if(!bundlePath||!historyPath)throw new Error('usage: --bundle <daily.json> --history-pack <json> [--output file]');
const bundle=JSON.parse(fs.readFileSync(bundlePath,'utf8')),historyPack=JSON.parse(fs.readFileSync(historyPath,'utf8'));
const sessionDate=String(bundle.sessionDate??'');
if(!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate)||bundle.barsReady!==true)throw new Error('Dynamic5m challenger matrix daily bundle not ready');

const finite=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const mean=xs=>xs.length?xs.reduce((s,x)=>s+x,0)/xs.length:null;
const median=xs=>{if(!xs.length)return null;const a=[...xs].sort((a,b)=>a-b),m=Math.floor(a.length/2);return a.length%2?a[m]:(a[m-1]+a[m])/2;};
const profitFactor=xs=>{const gp=xs.filter(x=>x>0).reduce((s,x)=>s+x,0),gl=-xs.filter(x=>x<0).reduce((s,x)=>s+x,0);return gl>0?gp/gl:(gp>0?Infinity:null);};
const maxDD=xs=>{let e=1,p=1,m=0;for(const r of xs){e*=1+r/100;p=Math.max(p,e);m=Math.max(m,(p-e)/p*100);}return m;};
function summary(xs){const r=xs.filter(finite).map(Number);let e=1;for(const x of r)e*=1+x/100;return {n:r.length,netReturnPct:(e-1)*100,meanNetReturnPct:mean(r),medianNetReturnPct:median(r),winRate:r.length?r.filter(x=>x>0).length/r.length:null,profitFactor:profitFactor(r),maxDrawdownPct:maxDD(r)};}
function uniq(xs){return [...new Set(xs.map(x=>String(x?.symbol??'').trim().toUpperCase()).filter(Boolean))].sort();}

const actualHist=uniq(historyPack.sessions??[]),expectedHist=[...PHASE58_P13_FROZEN_POLICY.historicalUniverse].sort();
if(JSON.stringify(actualHist)!==JSON.stringify(expectedHist))throw new Error('Dynamic5m challenger matrix frozen historical universe mismatch');
const cached=buildProspectiveP21HistoricalRows({sessions:historyPack.sessions??[],horizons:PHASE58_P13_FROZEN_POLICY.horizonsBars});
if(cached.complete!==true)throw new Error(`historical materialization blocked: ${cached.status}`);
const priorOnlyCache=new Map();
function scorePrefix(currentPrefix){
  const feed=buildProspectiveP21FeatureFeed({symbol:currentPrefix.symbol,sessionDate:currentPrefix.sessionDate,bars5m:currentPrefix.bars5m,horizons:PHASE58_P13_FROZEN_POLICY.horizonsBars,latestBarClosed:true});
  if(!feed.complete)return {complete:false,status:'BLOCKED_P21_CURRENT_FEATURE_FEED'};
  const base=buildProspectiveP21FrozenDecision({historicalHorizonRowsByBars:cached.historicalHorizonRowsByBars,currentRowsByHorizon:feed.currentRowsByHorizon,options:PHASE58_P13_FROZEN_POLICY.selectionOptions,priorOnlyCache});
  if(!base.complete)return {complete:false,status:'BLOCKED_P21_PROSPECTIVE_BASE'};
  const built=buildFrozenPhase57SnapshotFromRuntimeDecision({decision:base.decision,modelId:base.modelId,artifactSha256:base.artifactSha256});
  if(!built.complete)return {complete:false,status:'BLOCKED_PHASE57_RUNTIME_ADAPTER'};
  return {complete:true,decision:base.decision,modelId:base.modelId,artifactSha256:base.artifactSha256};
}

const analogPool=buildP25DataDrivenExitAnalogPool({historicalSessions:historyPack.sessions??[]}).filter(x=>String(x.sessionDate)<=P25_EXIT_V3_INDEPENDENT_PROTOCOL.developmentCutoff);
if(!analogPool.length||analogPool.some(x=>String(x.sessionDate)>P25_EXIT_V3_INDEPENDENT_PROTOCOL.developmentCutoff))throw new Error('frozen EXIT analog pool cutoff violation');
const barsBySymbol=bundle.sessionBarsBySymbol??{};

function freezeVariant({variantId,selectionField,minSelected}){
  const frozenTrades=[],pointAudit=[],seen=new Set();
  for(const point of bundle.points??[]){
    const observedAt=String(point.observedAt??'');if(!Number.isFinite(Date.parse(observedAt)))continue;
    const source=Array.isArray(point?.[selectionField])?point[selectionField]:[];
    const selected=source.filter(x=>x?.symbol&&finite(x?.currentPrice)&&Number(x.currentPrice)>0);
    if(selected.length!==source.length||selected.length<minSelected){pointAudit.push({observedAt,status:'BLOCKED_DYNAMIC_POINT_MISSING_ENTRY_REFERENCE',variantId,selectedCount:selected.length});continue;}
    const scored=[];let blockedReason=null;
    for(const row of selected){
      const symbol=String(row.symbol).trim().toUpperCase(),full=barsBySymbol[symbol]??[];
      const prefix=full.filter(bar=>Date.parse(bar.timestamp)+5*60_000<=Date.parse(observedAt));
      if(prefix.length<6){blockedReason=`INSUFFICIENT_CLOSED_PREFIX:${symbol}`;break;}
      const currentPrefix={schemaVersion:1,phase:'57.p25.dynamic5m-matrix-frozen-entry',status:'DYNAMIC5M_PREFIX_READY',symbol,sessionDate,capturedAt:observedAt,latestBarClosed:true,bars5m:prefix,closedBarCount:prefix.length,sourceBarCount:prefix.length,methodology:{selectionCapturedPointInTime:true,currentPrefixOnly:true,futureBarsPassedToScorer:false,currentOutcomeUsed:false}};
      let result;try{result=scorePrefix(currentPrefix);}catch(error){blockedReason=`SCORER_EXCEPTION:${String(error?.message??error)}`;break;}
      if(!result?.complete||!result?.decision){blockedReason=String(result?.status??'SCORER_NOT_READY');break;}
      const d=result.decision,context=d.context??{};
      if(d.futureOutcomeUsed!==false||d.frozenByPhase57!==true||d.pointInTimeOnly!==true){blockedReason='FROZEN_ENTRY_ATTESTATION_FAILED';break;}
      scored.push({row,symbol,result,d,context,prefix});
    }
    if(blockedReason){pointAudit.push({observedAt,status:'BLOCKED_DYNAMIC_POINT_ENTRY_SET',variantId,reason:blockedReason,selectedCount:selected.length});continue;}
    let signalCount=0;
    for(const s of scored){
      const direction=Number(s.d.direction);if(s.context.signalEligible!==true||![-1,1].includes(direction))continue;
      const key=`${sessionDate}|${observedAt}|${s.symbol}`;if(seen.has(key))continue;seen.add(key);signalCount++;
      frozenTrades.push({key,entryAccepted:true,symbol:s.symbol,sessionDate,entryTimestamp:observedAt,featureCutoff:String(s.d.asOf??s.prefix.at(-1)?.timestamp??observedAt),signalDirection:direction,direction:direction===1?'LONG':'SHORT',baseHorizonBars:Number(s.context.selectedHorizonBars),confidence:finite(s.d.confidence)?Number(s.d.confidence):null,probability:finite(s.context.probability)?Number(s.context.probability):null,selectedFeatureFamily:s.context.selectedFeatureFamily??s.d.setup??null,selectedModelType:s.context.selectedModelType??null,selectedConfigId:s.context.selectedConfigId??null,selectedThreshold:finite(s.context.selectedThreshold)?Number(s.context.selectedThreshold):null,modelId:s.result.modelId,artifactSha256:s.result.artifactSha256,sector:String(s.row.sector??'UNKNOWN'),variantMemberships:[variantId],entryPrice:Number(s.row.currentPrice),contextBars:s.prefix,futureBars:(barsBySymbol[s.symbol]??[]).filter(bar=>Date.parse(bar.timestamp)>=Math.ceil(Date.parse(observedAt)/(5*60_000))*(5*60_000)),outcomePending:true,frozenBeforeOutcome:true,currentOutcomeUsed:false,selectionObservedAt:observedAt,selectionOpportunityScore:finite(s.row.opportunityScore)?Number(s.row.opportunityScore):null,selectionV2Score:finite(s.row.v2Score)?Number(s.row.v2Score):null});
    }
    pointAudit.push({observedAt,status:'DYNAMIC_POINT_ENTRY_SET_FROZEN',variantId,selectedCount:selected.length,signalCount});
  }
  return {frozenTrades,pointAudit};
}

function buildPortfolioBars(pairs){
  const out={};for(const [symbol,rows] of Object.entries(barsBySymbol)){
    const map=new Map((rows??[]).map(bar=>[String(bar.timestamp),{timestamp:String(bar.timestamp),close:Number(bar.close)}]));
    for(const p of pairs.filter(x=>x.symbol===symbol))map.set(p.entry.entryTimestamp,{timestamp:p.entry.entryTimestamp,close:Number(p.entry.entryPrice)});
    out[symbol]=[...map.values()].sort((a,b)=>a.timestamp.localeCompare(b.timestamp));
  }return out;
}
function evaluateCombo({selectionId,exitId,frozenTrades}){
  const pairs=[],blocked=[];
  for(const trade of frozenTrades){
    if(!trade.futureBars.length){blocked.push({key:trade.key,reason:'NO_FUTURE_BAR'});continue;}
    try{
      const outcome=exitId==='V3'?simulateP25ExitV3DualGate({row:trade,analogPool,roundTripCostPct:0.05}):simulateP25ExitV4({row:trade,analogPool,roundTripCostPct:0.05});
      const expected=exitId==='V3'?P25_EXIT_V3_DUAL_GATE_POLICY_SHA256:P25_EXIT_V4_POLICY_SHA256;
      if(outcome.policySha256!==expected)throw new Error(`${exitId} policy hash mismatch`);
      pairs.push({key:trade.key,sessionDate,symbol:trade.symbol,entry:{...trade,contextBars:undefined,futureBars:undefined},outcome});
    }catch(error){blocked.push({key:trade.key,reason:String(error?.message??error)});}
  }
  pairs.sort((a,b)=>a.entry.entryTimestamp.localeCompare(b.entry.entryTimestamp)||a.symbol.localeCompare(b.symbol));
  const portfolioBars=buildPortfolioBars(pairs);
  const portfolioTrades=pairs.map(p=>({entryAccepted:true,frozenBeforeOutcome:true,currentOutcomeUsed:false,symbol:p.symbol,sector:p.entry.sector,signalDirection:p.entry.signalDirection,sessionDate,entryTimestamp:p.entry.entryTimestamp,entryPrice:Number(p.entry.entryPrice),exitTimestamp:p.outcome.exitTimestamp,exitPrice:Number(p.outcome.exitPrice),exitReason:p.outcome.exitReason,netReturnPct:Number(p.outcome.netReturnPct)}));
  const profiles={};for(const profile of PHASE57_P25_LANE_C_ALLOCATION_PROFILES)profiles[profile.id]=simulateLaneCPortfolio({sessions:[{sessionDate,sessionBarsBySymbol:portfolioBars,trades:portfolioTrades}],profile,managementMode:`EXIT_${exitId}`,universeVariant:selectionId});
  return {route:`${selectionId} -> Frozen Entry -> EXIT ${exitId}`,frozenEntryCount:frozenTrades.length,resolvedCount:pairs.length,blockedCount:blocked.length,summary:summary(pairs.map(x=>x.outcome.netReturnPct)),pairs,blocked,allocation:{initialEquityJpy:1_000_000,profileWinnerSelected:false,profiles}};
}

const v1=freezeVariant({variantId:'DYNAMIC5M_V1',selectionField:'selected',minSelected:20});
const v2=freezeVariant({variantId:'DYNAMIC5M_V2',selectionField:'selectedV2',minSelected:15});
const matrix={
  V1_V3:evaluateCombo({selectionId:'DYNAMIC5M_V1',exitId:'V3',frozenTrades:v1.frozenTrades}),
  V1_V4:evaluateCombo({selectionId:'DYNAMIC5M_V1',exitId:'V4',frozenTrades:v1.frozenTrades}),
  V2_V3:evaluateCombo({selectionId:'DYNAMIC5M_V2',exitId:'V3',frozenTrades:v2.frozenTrades}),
  V2_V4:evaluateCombo({selectionId:'DYNAMIC5M_V2',exitId:'V4',frozenTrades:v2.frozenTrades}),
};
const freshCompleteDay=bundle.completeFiveMinuteCoverage===true&&bundle.hasDynamic5mV2EveryPoint===true&&bundle.barsReady===true;
const freshEligible=sessionDate>=P25_EXIT_V4_POLICY.firstFreshEligibleDate;
const safety={...P25_EXIT_V3_SAFETY,...PHASE57_P25_LANE_C_SAFETY,phase:'57.p25.dynamic5m-challenger-matrix-daily',mode:'READ_ONLY_DYNAMIC5M_V1_V2_EXIT_V3_V4_ALLOCATION_MATRIX'};
const payload={schemaVersion:1,phase:'57.p25.dynamic5m-challenger-matrix-daily',status:'P25_DYNAMIC5M_CHALLENGER_MATRIX_EVALUATED',sessionDate,createdAt:new Date().toISOString(),freshCompleteDay,classification:{formalOos:false,promotionEligible:false,prospectivePointInTimeSelection:true,completeSessionEvidence:freshCompleteDay,freshChallengerEligible:freshEligible,august31FailureAnalysisOnly:sessionDate==='2026-08-31'},matrix,selectionAudits:{DYNAMIC5M_V1:v1.pointAudit,DYNAMIC5M_V2:v2.pointAudit},methodology:{sameFrozenEntryScorerAcrossAllCells:true,selectionMembershipPointInTime:true,v1BaselineUntouched:true,v2ChallengerUntouched:true,exitV3PolicyFrozen:true,exitV4PolicyFrozen:true,capitalAllocationPolicyUnchanged:true,allocationProfileWinnerSelection:false,missingIntradayBucketsNeverFabricated:true,resultBasedRetuning:false,postHocWinnerFiltering:false,freshHoldoutConsumed:false},policyHashes:{exitV3:P25_EXIT_V3_DUAL_GATE_POLICY_SHA256,exitV4:P25_EXIT_V4_POLICY_SHA256},safety};
for(const k of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed'])if(payload.safety?.[k]!==false)throw new Error(`unsafe ${k}`);
fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(payload,null,2)+'\n');
console.log(JSON.stringify({status:payload.status,sessionDate,freshCompleteDay,cells:Object.fromEntries(Object.entries(matrix).map(([k,v])=>[k,{n:v.summary.n,netReturnPct:v.summary.netReturnPct,profitFactor:v.summary.profitFactor,maxDrawdownPct:v.summary.maxDrawdownPct,allocations:Object.fromEntries(Object.entries(v.allocation.profiles).map(([p,x])=>[p,{totalReturnPct:x.return?.totalReturnPct,maxDrawdownPct:x.risk?.maxDrawdownPct}]))}]))},null,2));
