import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fetchP252Yahoo5mSession} from '../predict/daytrade/phase57-p25-2j-routine-nonrss-5m-source.js';
import {buildProspectiveP21HistoricalRows} from '../predict/daytrade/phase57-p21-prospective-history.js';
import {buildProspectiveP21FeatureFeed} from '../predict/daytrade/phase57-p21-prospective-feature-feed.js';
import {buildProspectiveP21FrozenDecision} from '../predict/daytrade/phase57-p21-prospective-frozen-base.js';
import {buildFrozenPhase57SnapshotFromRuntimeDecision} from '../predict/scalping/phase58-phase57-runtime-adapter.js';
import {PHASE58_P13_FROZEN_POLICY} from '../predict/scalping/phase58-phase57-prospective-pipeline.js';
import {runP253AKDynamicManagementSession,buildP253AKManagementRows} from '../predict/daytrade/phase57-p25-3ak-dynamic-management-prospective.js';
import {buildP25DataDrivenExitAnalogPool} from '../predict/daytrade/phase57-p25-data-driven-exit.js';
import {simulateP25ExitV3DualGate,P25_EXIT_V3_DUAL_GATE_POLICY_SHA256} from '../predict/daytrade/phase57-p25-exit-v3-dual-gate.js';
import {P25_EXIT_V3_INDEPENDENT_PROTOCOL,P25_EXIT_V3_SAFETY} from '../predict/daytrade/phase57-p25-exit-v3-independent-protocol.js';

const arg=(n,f=null)=>{const i=process.argv.indexOf(n);return i>=0&&i+1<process.argv.length?process.argv[i+1]:f;};
const partialDir=arg('--partial-dir');
const historyPath=arg('--history-pack');
const output=arg('--output','tmp/p25-partial-abcd.json');
if(!partialDir||!historyPath)throw new Error('usage: --partial-dir <dir> --history-pack <json> [--output file]');

const finite=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const mean=xs=>xs.length?xs.reduce((s,x)=>s+x,0)/xs.length:null;
const median=xs=>{if(!xs.length)return null;const a=[...xs].sort((x,y)=>x-y),m=Math.floor(a.length/2);return a.length%2?a[m]:(a[m-1]+a[m])/2;};
const profitFactor=xs=>{const gp=xs.filter(x=>x>0).reduce((s,x)=>s+x,0),gl=-xs.filter(x=>x<0).reduce((s,x)=>s+x,0);return gl>0?gp/gl:(gp>0?Infinity:null);};
const maxDD=xs=>{let e=1,p=1,m=0;for(const r of xs){e*=1+r/100;p=Math.max(p,e);m=Math.max(m,(p-e)/p*100);}return m;};
function summary(xs){const r=xs.filter(finite).map(Number);let e=1;for(const x of r)e*=1+x/100;return {n:r.length,netReturnPct:(e-1)*100,meanNetReturnPct:mean(r),medianNetReturnPct:median(r),winRate:r.length?r.filter(x=>x>0).length/r.length:null,profitFactor:profitFactor(r),maxDrawdownPct:maxDD(r)};}
const normalizeSymbol=v=>String(v??'').trim().toUpperCase();
const uniq=xs=>[...new Set(xs.map(normalizeSymbol).filter(Boolean))].sort();
const keyOf=row=>`${String(row?.sessionDate??'')}|${String(row?.entryTimestamp??'')}|${normalizeSymbol(row?.symbol)}`;

const freeze=JSON.parse(fs.readFileSync(path.join(partialDir,'freeze.json'),'utf8'));
const manifest=JSON.parse(fs.readFileSync(path.join(partialDir,'partial-manifest.json'),'utf8'));
const measurements=fs.readFileSync(path.join(partialDir,'partial-measurements.ndjson'),'utf8').split(/\r?\n/).filter(Boolean).map(line=>JSON.parse(line));
const historyPack=JSON.parse(fs.readFileSync(historyPath,'utf8'));
if(freeze?.ready!==true||freeze?.sessionType!=='PARTIAL_LATE_START'||freeze?.status!=='PARTIAL_LATE_START_D50_FROZEN')throw new Error('partial freeze invalid');
if(manifest?.status!=='PARTIAL_FRESH_SUBSTRATE_READY'||manifest?.sessionType!=='PARTIAL_LATE_START'||manifest?.formalFullSession!==false)throw new Error('partial manifest invalid');
if(manifest.sessionDate!==freeze.sessionDate)throw new Error('partial date mismatch');
if(measurements.length!==Number(manifest.dynamicPointCount))throw new Error('partial measurement count mismatch');
const sessionDate=freeze.sessionDate;
const startIso=new Date(Date.parse(`${sessionDate}T${freeze.startTimeJst}:00+09:00`)).toISOString();
const endIso=new Date(Date.parse(`${sessionDate}T${freeze.endTimeJst}:00+09:00`)).toISOString();
const startMs=Date.parse(startIso),endMs=Date.parse(endIso);
if(!Number.isFinite(startMs)||!Number.isFinite(endMs)||endMs<=startMs)throw new Error('partial window invalid');

for(const x of measurements){
  if(x?.status!=='MARKETWIDE_DYNAMIC_5M_MEASUREMENT_READY'||Number(x?.inputSymbols)<3000)throw new Error(`invalid Dynamic5m point ${x?.observedAt}`);
  const t=Date.parse(x.observedAt);if(t<startMs||t>endMs+60_000)throw new Error(`Dynamic5m point outside partial window ${x.observedAt}`);
}

const expectedVariants={FIXED_5:5,OLD_FIXED_30:30,DYNAMIC_30:30,DYNAMIC_40:40,DYNAMIC_50:50};
for(const [k,n] of Object.entries(expectedVariants))if(!Array.isArray(freeze.variants?.[k])||freeze.variants[k].length!==n)throw new Error(`partial freeze ${k} cardinality mismatch`);
const d30=freeze.variants.DYNAMIC_30.map(normalizeSymbol),d40=freeze.variants.DYNAMIC_40.map(normalizeSymbol),d50=freeze.variants.DYNAMIC_50.map(normalizeSymbol);
if(!d30.every((x,i)=>d40[i]===x)||!d40.every((x,i)=>d50[i]===x))throw new Error('partial D30/40/50 nesting mismatch');

const fixedUnion=uniq(Object.values(freeze.variants).flat());
const dynamicUnion=uniq(measurements.flatMap(x=>(x.selected??[]).map(r=>r.symbol)));
const allSymbols=uniq([...fixedUnion,...dynamicUnion]);
const sessionBarsBySymbol={};
const failures=[];
let cursor=0;
async function worker(){
  while(cursor<allSymbols.length){
    const symbol=allSymbols[cursor++];
    try{const r=await fetchP252Yahoo5mSession({symbol,sessionDate});sessionBarsBySymbol[symbol]=r.bars;}
    catch(error){failures.push({symbol,reason:String(error?.message??error)});}
  }
}
await Promise.all(Array.from({length:Math.min(10,allSymbols.length)},()=>worker()));
if(failures.length||Object.keys(sessionBarsBySymbol).length!==allSymbols.length)throw new Error(`post-close 5m bar collection incomplete ${Object.keys(sessionBarsBySymbol).length}/${allSymbols.length}: ${JSON.stringify(failures.slice(0,12))}`);

const actualHist=uniq(historyPack.sessions??[]),expectedHist=[...PHASE58_P13_FROZEN_POLICY.historicalUniverse].sort();
if(JSON.stringify(actualHist)!==JSON.stringify(expectedHist))throw new Error('partial ABCD frozen historical universe mismatch');
const cached=buildProspectiveP21HistoricalRows({sessions:historyPack.sessions??[],horizons:PHASE58_P13_FROZEN_POLICY.horizonsBars});
if(cached.complete!==true)throw new Error(`historical materialization blocked: ${cached.status}`);
const priorOnlyCache=new Map();
function scorePrefixBase({currentPrefix}){
  const feed=buildProspectiveP21FeatureFeed({symbol:currentPrefix.symbol,sessionDate:currentPrefix.sessionDate,bars5m:currentPrefix.bars5m,horizons:PHASE58_P13_FROZEN_POLICY.horizonsBars,latestBarClosed:true});
  if(!feed.complete)return {complete:false,status:'BLOCKED_P21_CURRENT_FEATURE_FEED'};
  const base=buildProspectiveP21FrozenDecision({historicalHorizonRowsByBars:cached.historicalHorizonRowsByBars,currentRowsByHorizon:feed.currentRowsByHorizon,options:PHASE58_P13_FROZEN_POLICY.selectionOptions,priorOnlyCache});
  if(!base.complete)return {complete:false,status:'BLOCKED_P21_PROSPECTIVE_BASE'};
  const built=buildFrozenPhase57SnapshotFromRuntimeDecision({decision:base.decision,modelId:base.modelId,artifactSha256:base.artifactSha256});
  if(!built.complete)return {complete:false,status:'BLOCKED_PHASE57_RUNTIME_ADAPTER'};
  return {complete:true,status:'PHASE57_PROSPECTIVE_SNAPSHOT_READY',policyId:PHASE58_P13_FROZEN_POLICY.policyId,currentSymbol:currentPrefix.symbol,snapshot:built.snapshot,phase57:{status:base.status,decision:base.decision,modelId:base.modelId,artifactSha256:base.artifactSha256}};
}
function partialScorePrefix(args){
  const observedMs=Date.parse(args?.currentPrefix?.capturedAt??'');
  if(!Number.isFinite(observedMs)||observedMs<startMs||observedMs>endMs)return {complete:false,status:'BLOCKED_OUTSIDE_PARTIAL_LATE_START_WINDOW'};
  return scorePrefixBase(args);
}

const acBase=runP253AKDynamicManagementSession({universeRecord:freeze,historicalSessions:historyPack.sessions??[],sessionBarsBySymbol,scorePrefix:partialScorePrefix});
const frozenD50=(acBase?.replay?.ledger?.frozenTrades??[]).filter(t=>(t.variantMemberships??[]).includes('DYNAMIC_50'));
const fixedByKey=new Map((acBase?.fixedOutcomes?.resolvedTrades??[]).map(r=>[keyOf(r),r]));
const managed=buildP253AKManagementRows({frozenTrades:frozenD50,sessionBarsBySymbol});
const managedByKey=new Map(managed.rows.map(r=>[keyOf(r),r]));
const analogPool=buildP25DataDrivenExitAnalogPool({historicalSessions:historyPack.sessions??[]}).filter(x=>String(x.sessionDate)<=P25_EXIT_V3_INDEPENDENT_PROTOCOL.developmentCutoff);
if(!analogPool.length)throw new Error('frozen EXIT v3 analog pool empty');
const aRows=[],cRows=[],acPairs=[],cBlocked=[];
for(const trade of frozenD50){
  const key=keyOf(trade),fixed=fixedByKey.get(key),row=managedByKey.get(key);
  if(fixed){
    const fixedNet=Number(fixed.netReturnPct??fixed.afterCostReturnPct??fixed.returnPct);
    if(Number.isFinite(fixedNet))aRows.push({...fixed,netReturnPct:fixedNet});
  }
  if(!row){cBlocked.push({key,reason:'MANAGEMENT_ROW_MISSING'});continue;}
  try{
    const v3=simulateP25ExitV3DualGate({row,analogPool,roundTripCostPct:0.05});
    if(v3.policySha256!==P25_EXIT_V3_DUAL_GATE_POLICY_SHA256)throw new Error('EXIT v3 policy hash mismatch');
    cRows.push({key,symbol:trade.symbol,entry:trade,v3});
    if(fixed){const fixedNet=Number(fixed.netReturnPct??fixed.afterCostReturnPct??fixed.returnPct);if(Number.isFinite(fixedNet))acPairs.push({key,symbol:trade.symbol,fixedNetReturnPct:fixedNet,v3NetReturnPct:Number(v3.netReturnPct),deltaNetReturnPct:Number(v3.netReturnPct)-fixedNet});}
  }catch(error){cBlocked.push({key,reason:String(error?.message??error)});}
}
const A={route:'DYNAMIC_50 -> Frozen Entry -> Fixed EXIT',frozenEntryCount:frozenD50.length,resolvedCount:aRows.length,summary:summary(aRows.map(x=>x.netReturnPct)),rows:aRows};
const C={route:'DYNAMIC_50 -> Frozen Entry -> EXIT v3',frozenEntryCount:frozenD50.length,resolvedCount:cRows.length,blockedCount:cBlocked.length,summary:summary(cRows.map(x=>x.v3.netReturnPct)),rows:cRows,blocked:cBlocked};
const acDelta=acPairs.map(x=>x.deltaNetReturnPct);
const ACComparison={pairedCount:acPairs.length,meanDeltaNetReturnPct:mean(acDelta),medianDeltaNetReturnPct:median(acDelta),v3BetterCount:acDelta.filter(x=>x>0).length,v3WorseCount:acDelta.filter(x=>x<0).length,equalCount:acDelta.filter(x=>x===0).length,pairs:acPairs};

const dynamicBundle={
  schemaVersion:1,
  phase:'57.p25.partial-dynamic5m-postclose-bundle',
  status:'P25_PARTIAL_DYNAMIC5M_POSTCLOSE_BUNDLE_READY',
  sessionDate,
  createdAt:new Date().toISOString(),
  pointCount:measurements.length,
  expectedPointCount:measurements.length,
  missingExpectedBucketCount:0,
  missingExpectedBuckets:[],
  completeFiveMinuteCoverage:false,
  selectedSymbolUnionCount:dynamicUnion.length,
  selectedSymbolUnion:dynamicUnion,
  points:measurements.map(x=>({bucket:new Date(Math.floor(Date.parse(x.observedAt)/(5*60_000))*5*60_000).toISOString(),observedAt:x.observedAt,inputSymbols:Number(x.inputSymbols),selected:(x.selected??[]).map(r=>({symbol:normalizeSymbol(r.symbol),sector:String(r.sector??'UNKNOWN'),currentPrice:Number(r.currentPrice),sourceScannedAt:r.sourceScannedAt??x.observedAt,opportunityScore:Number(r.opportunityScore),turnoverYen:Number(r.turnoverYen)})),methodology:x.methodology,policy:x.policy,safety:x.safety})),
  barsReady:true,
  barFailureCount:0,
  barFailures:[],
  sessionBarsBySymbol:Object.fromEntries(dynamicUnion.map(s=>[s,sessionBarsBySymbol[s]])),
  methodology:{selectionMembershipCapturedPointInTime:true,postCloseBarsUsedOnlyAsPrefixAtRecordedSelectionCutoff:true,partialLateStart:true,formalFullSession:false,missingEarlierBucketsNeverBackfilledOrFabricated:true,resultBasedRetuning:false,freshHoldoutConsumed:false},
  safety:freeze.safety,
};
const tmpBundle=path.join(path.dirname(output),'p25-partial-dynamic-bundle.json');
const tmpBD=path.join(path.dirname(output),'p25-partial-bd.json');
fs.mkdirSync(path.dirname(output),{recursive:true});
fs.writeFileSync(tmpBundle,JSON.stringify(dynamicBundle,null,2)+'\n');
const child=spawnSync(process.execPath,['scripts/run_p25_dynamic5m_exitv3_portfolio_daily.mjs','--bundle',tmpBundle,'--history-pack',historyPath,'--output',tmpBD],{encoding:'utf8',stdio:['ignore','pipe','pipe']});
if(child.status!==0)throw new Error(`B/D evaluator failed: ${child.stderr||child.stdout}`);
const bd=JSON.parse(fs.readFileSync(tmpBD,'utf8'));

const safety={...P25_EXIT_V3_SAFETY,phase:'57.p25.partial-abcd-postclose',mode:'READ_ONLY_PARTIAL_LATE_START_ABCD_MEASUREMENT',researchOnly:true,executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,freshHoldoutConsumed:false};
for(const k of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed'])if(safety[k]!==false)throw new Error(`unsafe ${k}`);
const payload={
  schemaVersion:1,
  phase:'57.p25.partial-abcd-postclose',
  status:'P25_PARTIAL_ABCD_POSTCLOSE_EVALUATED',
  sessionDate,
  createdAt:new Date().toISOString(),
  classification:{sessionType:'PARTIAL_LATE_START',formalFullSession:false,formalOos:false,promotionEligible:false,partialStartJst:freeze.startTimeJst,partialEndJst:freeze.endTimeJst,missingEarlierBucketsNeverBackfilledOrFabricated:true},
  inputs:{partialPointCount:measurements.length,dynamicSelectedSymbolUnionCount:dynamicUnion.length,postCloseBarsSymbolCount:allSymbols.length,postCloseBarsProvider:'YAHOO_FINANCE_CHART_5M',frozenHistoricalUniverseCount:actualHist.length},
  A,
  B:bd.B,
  C,
  D:bd.D,
  comparisons:{A_vs_C:ACComparison},
  methodology:{d50FrozenAt:freeze.frozenAt,partialWindowEntryGateUsesObservedCompletedBarTime:true,fullSessionBarsAvailableOnlyPostClose:true,entryScorerReceivesPrefixOnly:true,futureBarsExcludedFromEntryScorer:true,fixedExitUntouched:true,exitV3PolicyFrozen:true,capitalAllocationPolicyUnchanged:true,allocationProfileWinnerSelection:false,resultBasedRetuning:false,formalFullSession:false,formalOos:false,promotionEligible:false,freshHoldoutConsumed:false},
  safety,
};
fs.writeFileSync(output,JSON.stringify(payload,null,2)+'\n');
console.log(JSON.stringify({status:payload.status,sessionDate,classification:payload.classification,A:A.summary,B:bd.B.summary,C:C.summary,D:Object.fromEntries(Object.entries(bd.D.profiles??{}).map(([k,v])=>[k,{totalReturnPct:v.return?.totalReturnPct,finalEquityJpy:v.return?.finalEquityJpy,maxDrawdownPct:v.risk?.maxDrawdownPct}]))},null,2));
