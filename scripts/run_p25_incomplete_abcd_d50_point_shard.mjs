import fs from 'node:fs';
import path from 'node:path';
import {buildProspectiveP21HistoricalRows} from '../predict/daytrade/phase57-p21-prospective-history.js';
import {buildProspectiveP21FeatureFeed} from '../predict/daytrade/phase57-p21-prospective-feature-feed.js';
import {buildProspectiveP21FrozenDecision} from '../predict/daytrade/phase57-p21-prospective-frozen-base.js';
import {buildFrozenPhase57SnapshotFromRuntimeDecision} from '../predict/scalping/phase58-phase57-runtime-adapter.js';
import {PHASE58_P13_FROZEN_POLICY} from '../predict/scalping/phase58-phase57-prospective-pipeline.js';

const arg=(n,f=null)=>{const i=process.argv.indexOf(n);return i>=0&&i+1<process.argv.length?process.argv[i+1]:f;};
const partialDir=arg('--partial-dir');
const historyPath=arg('--history-pack');
const barsPath=arg('--bars');
const output=arg('--output');
const shardIndex=Number(arg('--shard-index','0'));
const shardCount=Number(arg('--shard-count','1'));
if(!partialDir||!historyPath||!barsPath||!output||!Number.isInteger(shardIndex)||!Number.isInteger(shardCount)||shardCount<1||shardIndex<0||shardIndex>=shardCount)throw new Error('usage: --partial-dir <dir> --history-pack <json> --bars <json> --output <json> --shard-index <n> --shard-count <n>');

const safety={executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,freshHoldoutConsumed:false};
const finite=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const sym=v=>String(v??'').trim().toUpperCase();
const uniq=xs=>[...new Set(xs.map(sym).filter(Boolean))].sort();

const freeze=JSON.parse(fs.readFileSync(path.join(partialDir,'freeze.json'),'utf8'));
const measurements=fs.readFileSync(path.join(partialDir,'partial-measurements.ndjson'),'utf8').split(/\r?\n/).filter(Boolean).map(line=>JSON.parse(line));
const historyPack=JSON.parse(fs.readFileSync(historyPath,'utf8'));
const barsCombined=JSON.parse(fs.readFileSync(barsPath,'utf8'));
if(barsCombined.status!=='P25_INCOMPLETE_ABCD_BARS_COMBINED'||barsCombined.sessionDate!==freeze.sessionDate)throw new Error('combined bars invalid');
const sessionBarsBySymbol=barsCombined.sessionBarsBySymbol??{};
const usableSymbolSet=new Set(Object.keys(sessionBarsBySymbol));
const d50=(freeze.variants?.DYNAMIC_50??[]).map(sym);
if(d50.length!==50)throw new Error('DYNAMIC_50 cardinality mismatch');

const totalPairs=measurements.length*d50.length;
const assignedPairs=[];
for(let pointIndex=0;pointIndex<measurements.length;pointIndex++){
  if(pointIndex%shardCount!==shardIndex)continue;
  for(let symbolIndex=0;symbolIndex<d50.length;symbolIndex++){
    assignedPairs.push({flatIndex:pointIndex*d50.length+symbolIndex,pointIndex,symbolIndex,symbol:d50[symbolIndex],observedAt:String(measurements[pointIndex].observedAt)});
  }
}

const actualHist=uniq((historyPack.sessions??[]).map(x=>x?.symbol));
const expectedHist=[...PHASE58_P13_FROZEN_POLICY.historicalUniverse].sort();
if(JSON.stringify(actualHist)!==JSON.stringify(expectedHist))throw new Error('frozen historical universe mismatch');
const historicalStarted=Date.now();
const cached=buildProspectiveP21HistoricalRows({sessions:historyPack.sessions??[],horizons:PHASE58_P13_FROZEN_POLICY.horizonsBars});
if(cached.complete!==true)throw new Error(`historical materialization blocked: ${cached.status}`);
const historicalMs=Date.now()-historicalStarted;
const priorOnlyCache=new Map();
let cacheHits=0,cacheMisses=0;

function scorePrefix(currentPrefix){
  const feed=buildProspectiveP21FeatureFeed({symbol:currentPrefix.symbol,sessionDate:currentPrefix.sessionDate,bars5m:currentPrefix.bars5m,horizons:PHASE58_P13_FROZEN_POLICY.horizonsBars,latestBarClosed:true});
  if(!feed.complete)return {complete:false,status:'BLOCKED_P21_CURRENT_FEATURE_FEED'};
  const before=priorOnlyCache.size;
  const base=buildProspectiveP21FrozenDecision({historicalHorizonRowsByBars:cached.historicalHorizonRowsByBars,currentRowsByHorizon:feed.currentRowsByHorizon,options:PHASE58_P13_FROZEN_POLICY.selectionOptions,priorOnlyCache});
  if(priorOnlyCache.size===before)cacheHits++;else cacheMisses++;
  if(!base.complete)return {complete:false,status:'BLOCKED_P21_PROSPECTIVE_BASE'};
  const built=buildFrozenPhase57SnapshotFromRuntimeDecision({decision:base.decision,modelId:base.modelId,artifactSha256:base.artifactSha256});
  if(!built.complete)return {complete:false,status:'BLOCKED_PHASE57_RUNTIME_ADAPTER'};
  return {complete:true,decision:base.decision,modelId:base.modelId,artifactSha256:base.artifactSha256};
}

const sectorMap=new Map((freeze?.rankAudit?.day50??[]).map(r=>[sym(r.symbol),String(r.sector??'UNKNOWN')]));
const pointMap=new Map();
const pairTimings=[];
for(const pair of assignedPairs){
  const started=Date.now();
  const point=measurements[pair.pointIndex];
  const observedAt=pair.observedAt;
  let out=pointMap.get(observedAt);
  if(!out){out={observedAt,blockedReason:null,scoredCount:0,signals:[],pairIndices:[]};pointMap.set(observedAt,out);}
  out.pairIndices.push(pair.flatIndex);
  const symbol=pair.symbol;
  if(!usableSymbolSet.has(symbol)){pairTimings.push({flatIndex:pair.flatIndex,symbol,ms:Date.now()-started,status:'UNUSABLE_SYMBOL'});continue;}
  const observedMs=Date.parse(observedAt);
  const full=sessionBarsBySymbol[symbol]??[];
  const prefix=full.filter(bar=>Date.parse(bar.timestamp)+5*60_000<=observedMs);
  if(prefix.length<6){out.blockedReason=out.blockedReason??`INSUFFICIENT_CLOSED_PREFIX:${symbol}:${prefix.length}`;pairTimings.push({flatIndex:pair.flatIndex,symbol,ms:Date.now()-started,status:'INSUFFICIENT_PREFIX'});continue;}
  const currentPrefix={schemaVersion:1,phase:'57.p25.partial-d50-frozen-entry',status:'PARTIAL_D50_PREFIX_READY',symbol,sessionDate:freeze.sessionDate,capturedAt:observedAt,latestBarClosed:true,bars5m:prefix,closedBarCount:prefix.length,sourceBarCount:prefix.length,methodology:{currentPrefixOnly:true,futureBarsPassedToScorer:false,currentOutcomeUsed:false,partialLateStart:true}};
  let result;
  try{result=scorePrefix(currentPrefix);}catch(error){out.blockedReason=out.blockedReason??`SCORER_EXCEPTION:${symbol}:${String(error?.message??error)}`;pairTimings.push({flatIndex:pair.flatIndex,symbol,ms:Date.now()-started,status:'SCORER_EXCEPTION'});continue;}
  if(!result?.complete||!result?.decision){out.blockedReason=out.blockedReason??`SCORER_NOT_READY:${symbol}:${result?.status??'UNKNOWN'}`;pairTimings.push({flatIndex:pair.flatIndex,symbol,ms:Date.now()-started,status:'SCORER_NOT_READY'});continue;}
  const d=result.decision,context=d.context??{};
  if(d.futureOutcomeUsed!==false||d.frozenByPhase57!==true||d.pointInTimeOnly!==true){out.blockedReason=out.blockedReason??`FROZEN_ENTRY_ATTESTATION_FAILED:${symbol}`;pairTimings.push({flatIndex:pair.flatIndex,symbol,ms:Date.now()-started,status:'ATTESTATION_FAILED'});continue;}
  out.scoredCount++;
  const direction=Number(d.direction);
  if(context.signalEligible===true&&[-1,1].includes(direction)){
    const featureCutoff=String(d.asOf??prefix.at(-1)?.timestamp??'');
    if(!Number.isFinite(Date.parse(featureCutoff)))throw new Error(`invalid D50 feature cutoff ${symbol}`);
    out.signals.push({d50Index:pair.symbolIndex,entry:{entryAccepted:true,symbol,sessionDate:freeze.sessionDate,entryTimestamp:featureCutoff,featureCutoff,signalDirection:direction,direction:direction===1?'LONG':'SHORT',baseHorizonBars:Number(context.selectedHorizonBars),confidence:finite(d.confidence)?Number(d.confidence):null,probability:finite(context.probability)?Number(context.probability):null,selectedFeatureFamily:context.selectedFeatureFamily??d.setup??null,selectedModelType:context.selectedModelType??null,selectedConfigId:context.selectedConfigId??null,selectedThreshold:finite(context.selectedThreshold)?Number(context.selectedThreshold):null,modelId:result.modelId,artifactSha256:result.artifactSha256,sector:sectorMap.get(symbol)??'UNKNOWN',variantMemberships:['DYNAMIC_50'],selectionObservedAt:observedAt,outcomePending:true,frozenBeforeOutcome:true,currentOutcomeUsed:false}});
  }
  pairTimings.push({flatIndex:pair.flatIndex,symbol,ms:Date.now()-started,status:'SCORED'});
}

const points=[...pointMap.values()].map(p=>({...p,pairIndices:[...p.pairIndices].sort((a,b)=>a-b),signals:[...p.signals].sort((a,b)=>a.d50Index-b.d50Index)})).sort((a,b)=>String(a.observedAt).localeCompare(String(b.observedAt)));
const payload={schemaVersion:2,phase:'57.p25.incomplete-abcd-d50-shard',status:'P25_INCOMPLETE_ABCD_D50_SHARD_READY',sessionDate:freeze.sessionDate,shardIndex,shardCount,totalPairs,assignedPairs,points,methodology:{partitionByMeasurementPointModuloShardCount:true,cacheLocalityByExactFeatureCutoff:true,flattenOrder:'pointIndex*50+symbolIndex',unavailablePostCloseSymbolsSkippedExactlyAsIncompleteWrapper:true,pointBlockPropagatedToFinalRecombiner:true,entryScorerReceivesPrefixOnly:true,futureBarsExcludedFromEntryScorer:true,resultBasedRetuning:false},diagnostics:{historicalMs,cacheHits,cacheMisses,cacheEntries:priorOnlyCache.size,pairTimings},safety};
fs.mkdirSync(path.dirname(output),{recursive:true});
fs.writeFileSync(output,JSON.stringify(payload,null,2)+'\n');
console.log(JSON.stringify({status:payload.status,shardIndex,assignedPairs:assignedPairs.length,points:points.length,blocked:points.filter(x=>x.blockedReason).length,signals:points.reduce((s,x)=>s+x.signals.length,0),historicalMs,cacheHits,cacheMisses,cacheEntries:priorOnlyCache.size,maxPairMs:Math.max(0,...pairTimings.map(x=>x.ms))},null,2));
