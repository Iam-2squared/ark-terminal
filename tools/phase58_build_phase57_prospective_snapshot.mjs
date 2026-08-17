import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {
  buildPhase57ProspectiveSnapshotPipeline,
  PHASE58_P13_FROZEN_POLICY,
  PHASE58_P13_SAFETY,
} from '../predict/scalping/phase58-phase57-prospective-pipeline.js';

function arg(name,fallback=null){
  const index=process.argv.indexOf(name);
  return index>=0&&index+1<process.argv.length?process.argv[index+1]:fallback;
}

function sha256(raw){return crypto.createHash('sha256').update(raw).digest('hex');}

function readJson(file){
  const raw=fs.readFileSync(file);
  return {raw,value:JSON.parse(raw.toString('utf8')),sha256:sha256(raw)};
}

function atomicWrite(file,payload){
  fs.mkdirSync(path.dirname(file),{recursive:true});
  const temp=`${file}.tmp-${process.pid}`;
  fs.writeFileSync(temp,JSON.stringify(payload,null,2)+'\n','utf8');
  fs.renameSync(temp,file);
}

const historyPath=arg('--history-sessions');
const prefixPath=arg('--current-prefix');
const outputPath=arg('--output','data/phase58/live-phase57-snapshot.json');

if(!historyPath||!prefixPath){
  console.error('usage: node tools/phase58_build_phase57_prospective_snapshot.mjs --history-sessions <historical-5m-sessions.json> --current-prefix <phase57-live-5m-prefix.json> [--output <snapshot.json>]');
  process.exit(2);
}

let historyInput,currentInput;
try{
  historyInput=readJson(historyPath);
  currentInput=readJson(prefixPath);
}catch(error){
  console.error(JSON.stringify({
    phase:'58.p13.phase57-prospective-snapshot-writer',
    status:'BLOCKED_INPUT_READ_OR_JSON',
    error:String(error?.message??error),
    safety:PHASE58_P13_SAFETY,
  },null,2));
  process.exit(1);
}

const historicalSessions=Array.isArray(historyInput.value)
  ? historyInput.value
  : Array.isArray(historyInput.value?.sessions)
    ? historyInput.value.sessions
    : null;
if(!historicalSessions){
  console.error(JSON.stringify({
    phase:'58.p13.phase57-prospective-snapshot-writer',
    status:'BLOCKED_HISTORY_SESSIONS_SHAPE',
    expected:'array or {sessions:[{symbol,sessionDate,bars5m:[]},...]}',
    safety:PHASE58_P13_SAFETY,
  },null,2));
  process.exit(1);
}

const currentPrefix=currentInput.value;
const built=buildPhase57ProspectiveSnapshotPipeline({
  historicalSessions,
  currentPrefix,
  policy:PHASE58_P13_FROZEN_POLICY,
});
if(!built.complete){
  console.error(JSON.stringify({
    phase:'58.p13.phase57-prospective-snapshot-writer',
    status:'BLOCKED_PHASE57_PROSPECTIVE_PIPELINE',
    pipelineStatus:built.status,
    historyFileSha256:historyInput.sha256,
    currentPrefixFileSha256:currentInput.sha256,
    details:built,
    safety:PHASE58_P13_SAFETY,
  },null,2));
  process.exit(1);
}
if(built.policyFrozen!==true){
  console.error(JSON.stringify({
    phase:'58.p13.phase57-prospective-snapshot-writer',
    status:'BLOCKED_NONFROZEN_POLICY',
    policyId:built.policyId,
    safety:PHASE58_P13_SAFETY,
  },null,2));
  process.exit(1);
}

const output={
  schemaVersion:1,
  phase:'58.p13.phase57-prospective-snapshot-writer',
  status:'FROZEN_PHASE57_PROSPECTIVE_SNAPSHOT_WRITTEN',
  createdAt:new Date().toISOString(),
  policyId:built.policyId,
  policyFrozen:true,
  historyFileSha256:historyInput.sha256,
  currentPrefixFileSha256:currentInput.sha256,
  snapshot:built.snapshot,
  phase57:{
    status:built.phase57.status,
    selectedHorizonBars:built.phase57.selectedHorizonBars,
    selectedFeatureFamily:built.phase57.selectedFeatureFamily,
    selectedModelType:built.phase57.selectedModelType,
    selectedThreshold:built.phase57.selectedThreshold,
  },
  provenance:built.provenance,
  methodology:{
    ...built.methodology,
    historyInputLocalFile:true,
    currentPrefixSource:'MARKETSPEED_II_RSS_RssChart_READ_ONLY',
    prospectiveOnly:true,
    historicalDecisionReconstructionAllowed:false,
    promotionEvidence:false,
  },
  safety:PHASE58_P13_SAFETY,
};

atomicWrite(outputPath,output);
const outputRaw=fs.readFileSync(outputPath);
console.log(JSON.stringify({
  status:output.status,
  output:outputPath,
  outputSha256:sha256(outputRaw),
  historyFileSha256:historyInput.sha256,
  currentPrefixFileSha256:currentInput.sha256,
  policyId:output.policyId,
  direction:output.snapshot.direction,
  confidence:output.snapshot.confidence,
  selectedHorizonBars:output.phase57.selectedHorizonBars,
  safety:PHASE58_P13_SAFETY,
},null,2));
