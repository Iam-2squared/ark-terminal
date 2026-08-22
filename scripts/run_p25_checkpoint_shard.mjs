import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {buildPhase57ProspectiveSnapshotPipeline,PHASE58_P13_FROZEN_POLICY,PHASE58_TARGET_MODES} from '../predict/scalping/phase58-phase57-prospective-pipeline.js';
import {replayP253PrefixShard} from '../predict/daytrade/phase57-p25-3o-sharded-prefix-replay.js';
import {buildP253PCheckpointPlan} from '../predict/daytrade/phase57-p25-3p-checkpoint-plan.js';

const arg=(name,fallback=null)=>{const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;};
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const load=file=>{const bytes=fs.readFileSync(file);return {bytes,sha256:sha(bytes),json:JSON.parse(bytes.toString('utf8'))};};
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
  const scorePrefix=({historicalSessions,currentPrefix})=>buildPhase57ProspectiveSnapshotPipeline({historicalSessions,currentPrefix,policy:PHASE58_P13_FROZEN_POLICY,targetMode:PHASE58_TARGET_MODES.REUSABLE_RESEARCH_TARGET});
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
    methodology:{computePlacementOnly:true,fullUnionFairCutoffGridPreserved:true,currentOuterOosUsedForPartitioning:false,entryThresholdRelaxed:false,modelChanged:false,universeChanged:false,freshHoldoutConsumed:false},
    safety:{executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,freshHoldoutConsumed:false},
  };
  fs.mkdirSync(path.dirname(outputPath),{recursive:true});
  fs.writeFileSync(outputPath,JSON.stringify(payload,null,2)+'\n','utf8');
  console.log(JSON.stringify({status:payload.status,batchId:payload.batchId,batchIndex:payload.batchIndex,batchCount:payload.batchCount,shardSymbolCount:payload.shardSymbols.length,output:outputPath,outputSha256:sha(fs.readFileSync(outputPath))},null,2));
}catch(error){
  console.error(JSON.stringify({status:'BLOCKED_P25_3P_CHECKPOINT',error:String(error?.message??error)},null,2));
  process.exit(1);
}
