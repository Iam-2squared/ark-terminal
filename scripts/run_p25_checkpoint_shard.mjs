import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {buildProspectiveP21HistoricalRows} from '../predict/daytrade/phase57-p21-prospective-history.js';
import {buildProspectiveP21FeatureFeed} from '../predict/daytrade/phase57-p21-prospective-feature-feed.js';
import {buildProspectiveP21FrozenDecision} from '../predict/daytrade/phase57-p21-prospective-frozen-base.js';
import {buildFrozenPhase57SnapshotFromRuntimeDecision} from '../predict/scalping/phase58-phase57-runtime-adapter.js';
import {PHASE58_P13_FROZEN_POLICY} from '../predict/scalping/phase58-phase57-prospective-pipeline.js';
import {replayP253PrefixShard} from '../predict/daytrade/phase57-p25-3o-sharded-prefix-replay.js';
import {buildP253PCheckpointPlan} from '../predict/daytrade/phase57-p25-3p-checkpoint-plan.js';

const arg=(name,fallback=null)=>{const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;};
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const load=file=>{const bytes=fs.readFileSync(file);return {bytes,sha256:sha(bytes),json:JSON.parse(bytes.toString('utf8'))};};
const uniqueSortedSymbols=sessions=>[...new Set((Array.isArray(sessions)?sessions:[]).map(session=>String(session?.symbol??'').trim()).filter(Boolean))].sort();
const sameArray=(a,b)=>a.length===b.length&&a.every((value,index)=>value===b[index]);
const historyPath=arg('--history-pack');
const capturePath=arg('--capture');
const batchIndex=Number(arg('--batch-index'));
const batchSize=Number(arg('--batch-size','5'));
const outputPath=arg('--output');
if(!historyPath||!capturePath||!Number.isInteger(batchIndex)||batchIndex<0||!outputPath){
  console.error('usage: node scripts/run_p25_checkpoint_shard.mjs --history-pack <json> --capture <json> --batch-index <n> [--batch-size 5] --output <json>');
  process.exit(2);
}

try{
  const history=load(historyPath),capture=load(capturePath);
  if(history.json?.phase!=='57.p25.2k.pinned-history-bridge-cli'||history.json?.status!=='P25_2_PINNED_HISTORY_PACK_READY')throw new Error('P25.3P pinned history pack required');
  if(capture.json?.collection?.ready!==true||!Array.isArray(capture.json?.sessions)||capture.json.sessions.length!==1)throw new Error('P25.3P one ready immutable capture required');
  const session=capture.json.sessions[0];
  const plan=buildP253PCheckpointPlan({universeRecord:session.universeRecord,batchSize});
  const batch=plan.batches[batchIndex];
  if(!batch)throw new Error(`P25.3P batch index out of range: ${batchIndex}/${plan.batchCount}`);

  const actualHistoricalUniverse=uniqueSortedSymbols(history.json.sessions);
  const expectedHistoricalUniverse=[...PHASE58_P13_FROZEN_POLICY.historicalUniverse].sort();
  if(!sameArray(actualHistoricalUniverse,expectedHistoricalUniverse))throw new Error(`P25.3P frozen historical universe mismatch expected=${expectedHistoricalUniverse.join(',')} actual=${actualHistoricalUniverse.join(',')}`);

  const historyStartedAt=Date.now();
  const cachedHistory=buildProspectiveP21HistoricalRows({sessions:history.json.sessions,horizons:PHASE58_P13_FROZEN_POLICY.horizonsBars});
  if(cachedHistory.complete!==true)throw new Error(`P25.3P historical materialization blocked: ${cachedHistory.status}`);
  const historicalMaterializationMs=Date.now()-historyStartedAt;
  let scorerCallCount=0;
  let scorerElapsedMs=0;

  const scorePrefix=({currentPrefix})=>{
    const startedAt=Date.now();
    scorerCallCount+=1;
    try{
      const feed=buildProspectiveP21FeatureFeed({
        symbol:currentPrefix.symbol,
        sessionDate:currentPrefix.sessionDate,
        bars5m:currentPrefix.bars5m,
        horizons:PHASE58_P13_FROZEN_POLICY.horizonsBars,
        latestBarClosed:true,
      });
      if(!feed.complete)return {complete:false,status:'BLOCKED_P21_CURRENT_FEATURE_FEED'};
      const base=buildProspectiveP21FrozenDecision({
        historicalHorizonRowsByBars:cachedHistory.historicalHorizonRowsByBars,
        currentRowsByHorizon:feed.currentRowsByHorizon,
        options:PHASE58_P13_FROZEN_POLICY.selectionOptions,
      });
      if(!base.complete)return {complete:false,status:'BLOCKED_P21_PROSPECTIVE_BASE'};
      if(!base.decision||typeof base.modelId!=='string'||!/^[a-f0-9]{64}$/i.test(String(base.artifactSha256??'')))return {complete:false,status:'BLOCKED_P21_PROVENANCE_NOT_READY'};
      const built=buildFrozenPhase57SnapshotFromRuntimeDecision({decision:base.decision,modelId:base.modelId,artifactSha256:base.artifactSha256});
      if(!built.complete)return {complete:false,status:'BLOCKED_PHASE57_RUNTIME_ADAPTER'};
      return {
        complete:true,
        status:'PHASE57_PROSPECTIVE_SNAPSHOT_READY',
        snapshot:built.snapshot,
        phase57:{status:base.status,decision:base.decision,modelId:base.modelId,artifactSha256:base.artifactSha256},
      };
    }finally{
      scorerElapsedMs+=Date.now()-startedAt;
    }
  };

  const shard=replayP253PrefixShard({
    universeRecord:session.universeRecord,
    historicalSessions:history.json.sessions,
    sessionBarsBySymbol:session.sessionBarsBySymbol??{},
    scoreSymbols:batch.shardSymbols,
    scorePrefix,
  });
  const payload={
    schemaVersion:1,
    phase:'57.p25.3p.checkpoint',
    status:'P25_3P_CHECKPOINT_COMPLETE',
    createdAt:new Date().toISOString(),
    batchId:batch.batchId,
    batchIndex:batch.batchIndex,
    batchSize:plan.batchSize,
    batchCount:plan.batchCount,
    shardSymbols:[...batch.shardSymbols],
    identities:{historyPackSha256:history.sha256,captureSha256:capture.sha256,sessionDate:String(session.sessionDate??session.universeRecord?.sessionDate??'')},
    shard,
    computeDiagnostics:{historicalMaterializationCount:1,historicalMaterializationMs,scorerCallCount,scorerElapsedMs},
    methodology:{computePlacementOnly:true,historicalMaterializationCachedPerShard:true,fullUnionFairCutoffGridPreserved:true,currentOuterOosUsedForPartitioning:false,entryThresholdRelaxed:false,modelChanged:false,universeChanged:false,freshHoldoutConsumed:false},
    safety:{executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,freshHoldoutConsumed:false},
  };
  fs.mkdirSync(path.dirname(outputPath),{recursive:true});
  fs.writeFileSync(outputPath,JSON.stringify(payload,null,2)+'\n','utf8');
  console.log(JSON.stringify({status:payload.status,batchId:payload.batchId,batchIndex:payload.batchIndex,batchCount:payload.batchCount,shardSymbolCount:payload.shardSymbols.length,computeDiagnostics:payload.computeDiagnostics,output:outputPath,outputSha256:sha(fs.readFileSync(outputPath))},null,2));
}catch(error){
  console.error(JSON.stringify({status:'BLOCKED_P25_3P_CHECKPOINT',error:String(error?.message??error)},null,2));
  process.exit(1);
}
