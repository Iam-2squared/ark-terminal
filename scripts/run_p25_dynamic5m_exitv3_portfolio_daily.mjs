import fs from 'node:fs';
import path from 'node:path';
import {buildProspectiveP21HistoricalRows} from '../predict/daytrade/phase57-p21-prospective-history.js';
import {buildProspectiveP21FeatureFeed} from '../predict/daytrade/phase57-p21-prospective-feature-feed.js';
import {buildProspectiveP21FrozenDecision} from '../predict/daytrade/phase57-p21-prospective-frozen-base.js';
import {buildFrozenPhase57SnapshotFromRuntimeDecision} from '../predict/scalping/phase58-phase57-runtime-adapter.js';
import {PHASE58_P13_FROZEN_POLICY} from '../predict/scalping/phase58-phase57-prospective-pipeline.js';
import {buildP25DataDrivenExitAnalogPool} from '../predict/daytrade/phase57-p25-data-driven-exit.js';
import {simulateP25ExitV3DualGate,P25_EXIT_V3_DUAL_GATE_POLICY_SHA256} from '../predict/daytrade/phase57-p25-exit-v3-dual-gate.js';
import {P25_EXIT_V3_INDEPENDENT_PROTOCOL,P25_EXIT_V3_SAFETY} from '../predict/daytrade/phase57-p25-exit-v3-independent-protocol.js';
import {simulateLaneCPortfolio,PHASE57_P25_LANE_C_ALLOCATION_PROFILES,PHASE57_P25_LANE_C_SAFETY} from '../predict/portfolio/phase57-p25-lane-c-portfolio-simulator.js';

const arg=(n,f=null)=>{const i=process.argv.indexOf(n);return i>=0&&i+1<process.argv.length?process.argv[i+1]:f;};
const bundlePath=arg('--bundle'),historyPath=arg('--history-pack'),output=arg('--output','tmp/p25-dynamic5m-bd.json');
if(!bundlePath||!historyPath)throw new Error('usage: --bundle <daily.json> --history-pack <json> [--output file]');
const bundle=JSON.parse(fs.readFileSync(bundlePath,'utf8')),historyPack=JSON.parse(fs.readFileSync(historyPath,'utf8'));
const sessionDate=String(bundle.sessionDate??'');
if(!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate)||bundle.barsReady!==true)throw new Error('Dynamic5m daily bundle not ready');
const finite=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const mean=xs=>xs.length?xs.reduce((s,x)=>s+x,0)/xs.length:null;
const profitFactor=xs=>{const gp=xs.filter(x=>x>0).reduce((s,x)=>s+x,0),gl=-xs.filter(x=>x<0).reduce((s,x)=>s+x,0);return gl>0?gp/gl:(gp>0?Infinity:null);};
const maxDD=xs=>{let e=1,p=1,m=0;for(const r of xs){e*=1+r/100;p=Math.max(p,e);m=Math.max(m,(p-e)/p*100);}return m;};
function summary(xs){const r=xs.filter(finite).map(Number);let e=1;for(const x of r)e*=1+x/100;return {n:r.length,netReturnPct:(e-1)*100,meanNetReturnPct:mean(r),winRate:r.length?r.filter(x=>x>0).length/r.length:null,profitFactor:profitFactor(r),maxDrawdownPct:maxDD(r)};}
function uniq(xs){return [...new Set(xs.map(x=>String(x?.symbol??'').trim().toUpperCase()).filter(Boolean))].sort();}
const actualHist=uniq(historyPack.sessions??[]),expectedHist=[...PHASE58_P13_FROZEN_POLICY.historicalUniverse].sort();
if(JSON.stringify(actualHist)!==JSON.stringify(expectedHist))throw new Error('Dynamic5m B/D frozen historical universe mismatch');
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
  return {complete:true,status:'PHASE57_PROSPECTIVE_SNAPSHOT_READY',decision:base.decision,snapshot:built.snapshot,modelId:base.modelId,artifactSha256:base.artifactSha256};
}
const analogPool=buildP25DataDrivenExitAnalogPool({historicalSessions:historyPack.sessions??[]}).filter(x=>String(x.sessionDate)<=P25_EXIT_V3_INDEPENDENT_PROTOCOL.developmentCutoff);
if(!analogPool.length)throw new Error('frozen EXIT v3 analog pool empty');
const barsBySymbol=bundle.sessionBarsBySymbol??{};
const frozenTrades=[],pointAudit=[],seenTradeKeys=new Set();
for(const point of bundle.points??[]){
  const observedAt=String(point.observedAt??'');
  if(!Number.isFinite(Date.parse(observedAt)))continue;
  const selected=(point.selected??[]).filter(x=>x?.symbol&&finite(x?.currentPrice)&&Number(x.currentPrice)>0);
  if(selected.length!==(point.selected??[]).length||selected.length<20){pointAudit.push({observedAt,status:'BLOCKED_DYNAMIC_POINT_MISSING_ENTRY_REFERENCE',selectedCount:selected.length});continue;}
  const scored=[];let blockedReason=null;
  for(const row of selected){
    const symbol=String(row.symbol).trim().toUpperCase(),full=barsBySymbol[symbol]??[];
    const prefix=full.filter(bar=>Date.parse(bar.timestamp)+5*60_000<=Date.parse(observedAt));
    if(prefix.length<6){blockedReason='INSUFFICIENT_CLOSED_PREFIX';break;}
    const currentPrefix={schemaVersion:1,phase:'57.p25.dynamic5m-frozen-entry',status:'DYNAMIC5M_PREFIX_READY',symbol,sessionDate,capturedAt:observedAt,latestBarClosed:true,bars5m:prefix,closedBarCount:prefix.length,sourceBarCount:prefix.length,methodology:{selectionCapturedPointInTime:true,currentPrefixOnly:true,futureBarsPassedToScorer:false,currentOutcomeUsed:false}};
    let result;try{result=scorePrefix(currentPrefix);}catch(error){blockedReason=`SCORER_EXCEPTION:${String(error?.message??error)}`;break;}
    if(!result?.complete||!result?.decision){blockedReason=String(result?.status??'SCORER_NOT_READY');break;}
    const d=result.decision,context=d.context??{};
    if(d.futureOutcomeUsed!==false||d.frozenByPhase57!==true||d.pointInTimeOnly!==true){blockedReason='FROZEN_ENTRY_ATTESTATION_FAILED';break;}
    scored.push({row,symbol,result,d,context,prefix});
  }
  if(blockedReason){pointAudit.push({observedAt,status:'BLOCKED_DYNAMIC_POINT_ENTRY_SET',reason:blockedReason,selectedCount:selected.length});continue;}
  let signals=0;
  for(const s of scored){
    const direction=Number(s.d.direction),signalEligible=s.context.signalEligible===true;
    if(!signalEligible||![-1,1].includes(direction))continue;
    const key=`${sessionDate}|${observedAt}|${s.symbol}`;if(seenTradeKeys.has(key))continue;seenTradeKeys.add(key);signals++;
    frozenTrades.push({key,entryAccepted:true,symbol:s.symbol,sessionDate,entryTimestamp:observedAt,featureCutoff:String(s.d.asOf??s.prefix.at(-1)?.timestamp??observedAt),signalDirection:direction,direction:direction===1?'LONG':'SHORT',baseHorizonBars:Number(s.context.selectedHorizonBars),confidence:finite(s.d.confidence)?Number(s.d.confidence):null,probability:finite(s.context.probability)?Number(s.context.probability):null,selectedFeatureFamily:s.context.selectedFeatureFamily??s.d.setup??null,selectedModelType:s.context.selectedModelType??null,selectedConfigId:s.context.selectedConfigId??null,selectedThreshold:finite(s.context.selectedThreshold)?Number(s.context.selectedThreshold):null,modelId:s.result.modelId,artifactSha256:s.result.artifactSha256,sector:String(s.row.sector??'UNKNOWN'),variantMemberships:['DYNAMIC_5M'],entryPrice:Number(s.row.currentPrice),contextBars:s.prefix,futureBars:(barsBySymbol[s.symbol]??[]).filter(bar=>Date.parse(bar.timestamp)>=Math.ceil(Date.parse(observedAt)/(5*60_000))*(5*60_000)),outcomePending:true,frozenBeforeOutcome:true,currentOutcomeUsed:false,selectionObservedAt:observedAt,selectionOpportunityScore:finite(s.row.opportunityScore)?Number(s.row.opportunityScore):null});
  }
  pointAudit.push({observedAt,status:'DYNAMIC_POINT_ENTRY_SET_FROZEN',selectedCount:selected.length,signalCount:signals});
}
const pairs=[],blocked=[];
for(const trade of frozenTrades){
  if(!trade.futureBars.length){blocked.push({key:trade.key,reason:'NO_FUTURE_BAR'});continue;}
  try{
    const v3=simulateP25ExitV3DualGate({row:trade,analogPool,roundTripCostPct:0.05});
    if(v3.policySha256!==P25_EXIT_V3_DUAL_GATE_POLICY_SHA256)throw new Error('EXIT v3 policy hash mismatch');
    pairs.push({key:trade.key,sessionDate,symbol:trade.symbol,entry:{...trade,contextBars:undefined,futureBars:undefined},v3});
  }catch(error){blocked.push({key:trade.key,reason:String(error?.message??error)});}
}
pairs.sort((a,b)=>a.entry.entryTimestamp.localeCompare(b.entry.entryTimestamp)||a.symbol.localeCompare(b.symbol));
const bSummary=summary(pairs.map(x=>x.v3.netReturnPct));
const portfolioBars={};
for(const [symbol,rows] of Object.entries(barsBySymbol)){
  const map=new Map((rows??[]).map(bar=>[String(bar.timestamp),{timestamp:String(bar.timestamp),close:Number(bar.close)}]));
  for(const p of pairs.filter(x=>x.symbol===symbol))map.set(p.entry.entryTimestamp,{timestamp:p.entry.entryTimestamp,close:Number(p.entry.entryPrice)});
  portfolioBars[symbol]=[...map.values()].sort((a,b)=>a.timestamp.localeCompare(b.timestamp));
}
const portfolioTrades=pairs.map(p=>({entryAccepted:true,frozenBeforeOutcome:true,currentOutcomeUsed:false,symbol:p.symbol,sector:p.entry.sector,signalDirection:p.entry.signalDirection,sessionDate,entryTimestamp:p.entry.entryTimestamp,entryPrice:Number(p.entry.entryPrice),exitTimestamp:p.v3.exitTimestamp,exitPrice:Number(p.v3.exitPrice),exitReason:p.v3.exitReason,netReturnPct:Number(p.v3.netReturnPct)}));
const portfolioSessions=[{sessionDate,sessionBarsBySymbol:portfolioBars,trades:portfolioTrades}];
const dProfiles={};
for(const profile of PHASE57_P25_LANE_C_ALLOCATION_PROFILES)dProfiles[profile.id]=simulateLaneCPortfolio({sessions:portfolioSessions,profile,managementMode:'EXIT_V3',universeVariant:'DYNAMIC_5M'});
const freshCompleteDay=bundle.completeFiveMinuteCoverage===true&&bundle.barsReady===true;
const safety={...P25_EXIT_V3_SAFETY,...PHASE57_P25_LANE_C_SAFETY,phase:'57.p25.dynamic5m-bd-daily',mode:'READ_ONLY_DYNAMIC5M_FROZEN_ENTRY_EXITV3_PORTFOLIO'};
const payload={schemaVersion:1,phase:'57.p25.dynamic5m-bd-daily',status:'P25_DYNAMIC5M_BD_DAILY_EVALUATED',sessionDate,createdAt:new Date().toISOString(),freshCompleteDay,classification:{formalOos:false,promotionEligible:false,prospectivePointInTimeSelection:true,completeSessionEvidence:freshCompleteDay},B:{route:'Dynamic 5m Selection -> Frozen Entry -> EXIT v3',pointCount:Number(bundle.pointCount),expectedPointCount:Number(bundle.expectedPointCount),missingExpectedBucketCount:Number(bundle.missingExpectedBucketCount),frozenEntryCount:frozenTrades.length,resolvedCount:pairs.length,blockedCount:blocked.length,summary:bSummary,pairs,blocked},D:{route:'Dynamic 5m Selection -> Frozen Entry -> EXIT v3 -> Capital Allocation',initialEquityJpy:1_000_000,profileWinnerSelected:false,profiles:dProfiles},pointAudit,methodology:{dynamicSelectionMembershipPointInTime:true,entryScorerReceivesClosedPrefixOnly:true,scannerObservedPriceUsedAsVirtualEntryReference:true,futureBarsExcludedFromEntryScorer:true,exitV3PolicyFrozen:true,capitalAllocationPolicyUnchanged:true,allocationProfileWinnerSelection:false,missingIntradayBucketsNeverFabricated:true,resultBasedRetuning:false,freshHoldoutConsumed:false},safety};
fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(payload,null,2)+'\n');
console.log(JSON.stringify({status:payload.status,sessionDate,freshCompleteDay,B:payload.B.summary,D:Object.fromEntries(Object.entries(dProfiles).map(([k,v])=>[k,{totalReturnPct:v.return?.totalReturnPct,finalEquityJpy:v.return?.finalEquityJpy,maxDrawdownPct:v.risk?.maxDrawdownPct}]))},null,2));
