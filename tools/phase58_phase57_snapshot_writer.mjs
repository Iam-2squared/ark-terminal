import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {buildFrozenPhase57SnapshotFromRuntimeDecision} from '../predict/scalping/phase58-phase57-runtime-adapter.js';

const SAFETY=Object.freeze({
  phase:'58.p9.phase57-snapshot-writer',
  mode:'READ_ONLY_RESEARCH',
  executionAllowed:false,
  brokerWriteAllowed:false,
  excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,
  paperTradingAllowed:false,
  automaticPromotionAllowed:false,
  productionUpdateAllowed:false,
  transmitted:false,
  freshHoldoutConsumed:false,
});

function arg(name, fallback=null){
  const i=process.argv.indexOf(name);
  return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;
}

const decisionPath=arg('--decision');
const outputPath=arg('--output','data/phase58/live-phase57-snapshot.json');
const modelId=arg('--model-id');
const artifactSha256=arg('--artifact-sha256');

if(!decisionPath||!modelId||!artifactSha256){
  console.error('usage: node tools/phase58_phase57_snapshot_writer.mjs --decision <point-in-time-phase57.json> --model-id <id> --artifact-sha256 <64hex> [--output <file>]');
  process.exit(2);
}

let raw;
try{raw=fs.readFileSync(decisionPath);}catch(error){
  console.error(JSON.stringify({status:'BLOCKED_PHASE57_DECISION_FILE_READ',error:String(error?.message??error),safety:SAFETY},null,2));
  process.exit(1);
}

let decision;
try{decision=JSON.parse(raw.toString('utf8'));}catch(error){
  console.error(JSON.stringify({status:'BLOCKED_PHASE57_DECISION_JSON',error:String(error?.message??error),safety:SAFETY},null,2));
  process.exit(1);
}

const built=buildFrozenPhase57SnapshotFromRuntimeDecision({decision,modelId,artifactSha256});
if(!built.complete){
  console.error(JSON.stringify({
    phase:'58.p9.phase57-snapshot-writer',
    status:'BLOCKED_PHASE57_RUNTIME_DECISION',
    blockers:built.blockers,
    forbiddenOutcomeFields:built.forbiddenOutcomeFields??[],
    decisionFileSha256:crypto.createHash('sha256').update(raw).digest('hex'),
    safety:SAFETY,
  },null,2));
  process.exit(1);
}

const out={
  schemaVersion:1,
  phase:'58.p9.phase57-snapshot-writer',
  status:'FROZEN_PHASE57_SNAPSHOT_WRITTEN',
  createdAt:new Date().toISOString(),
  decisionFileSha256:crypto.createHash('sha256').update(raw).digest('hex'),
  snapshot:built.snapshot,
  methodology:{
    prospectiveOnly:true,
    historicalDecisionReconstructionAllowed:false,
    futureOutcomeUsed:false,
    postCaptureThresholdSearchAllowed:false,
    entryRetuningAfterCaptureAllowed:false,
    phase58MayReverseDirection:false,
  },
  safety:SAFETY,
};

fs.mkdirSync(path.dirname(outputPath),{recursive:true});
const tmp=`${outputPath}.tmp-${process.pid}`;
fs.writeFileSync(tmp,JSON.stringify(out,null,2)+'\n',{encoding:'utf8'});
fs.renameSync(tmp,outputPath);
const outputSha256=crypto.createHash('sha256').update(fs.readFileSync(outputPath)).digest('hex');
console.log(JSON.stringify({status:'FROZEN_PHASE57_SNAPSHOT_WRITTEN',output:outputPath,outputSha256,modelId,artifactSha256,safety:SAFETY},null,2));
