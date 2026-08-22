import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {runP253QCheckpointedEvaluation,PHASE57_P25_3Q_SAFETY} from '../predict/daytrade/phase57-p25-3q-checkpointed-evaluation.js';

const arg=(name,fallback=null)=>{const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;};
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const load=file=>{const bytes=fs.readFileSync(file);return {bytes,sha256:sha(bytes),json:JSON.parse(bytes.toString('utf8'))};};

const historyPath=arg('--history-pack');
const captureDir=arg('--capture-dir');
const integrityPath=arg('--integrity-ledger');
const lineagePath=arg('--lineage-manifest');
const checkpointDir=arg('--checkpoint-dir');
const outputPath=arg('--output','data/p25-checkpointed-evaluation.json');
if(!historyPath||!captureDir||!integrityPath||!lineagePath||!checkpointDir){
  console.error('usage: node scripts/recombine_p25_checkpoint_evaluation.mjs --history-pack <json> --capture-dir <dir> --integrity-ledger <json> --lineage-manifest <json> --checkpoint-dir <dir> [--output <json>]');
  process.exit(2);
}

try{
  const history=load(historyPath),integrity=load(integrityPath),lineage=load(lineagePath);
  const captureFiles=fs.readdirSync(captureDir).filter(x=>x.endsWith('.json')).sort();
  const captures=captureFiles.map(name=>{const loaded=load(path.join(captureDir,name));return {artifact:loaded.json,artifactSha256:loaded.sha256,artifactPath:name};});
  const checkpointFiles=fs.readdirSync(checkpointDir).filter(x=>x.endsWith('.json')).sort();
  const checkpointsBySession={};
  for(const name of checkpointFiles){
    const checkpoint=load(path.join(checkpointDir,name)).json;
    const sessionDate=String(checkpoint?.identities?.sessionDate??'');
    if(!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate))throw new Error(`checkpoint session identity invalid: ${name}`);
    (checkpointsBySession[sessionDate]??=[]).push(checkpoint);
  }
  const evaluation=runP253QCheckpointedEvaluation({
    historyPack:history.json,
    captureArtifacts:captures,
    sessionIntegrityLedger:integrity.json,
    lineageManifest:lineage.json,
    checkpointsBySession,
  });
  const payload={
    schemaVersion:1,
    phase:'57.p25.3d.autonomous-evidence-evaluation-cli',
    status:'P25_3_AUTONOMOUS_EVALUATION_ARTIFACT_WRITTEN',
    createdAt:new Date().toISOString(),
    inputs:{
      historyPack:path.normalize(historyPath),historyPackSha256:history.sha256,
      integrityLedger:path.normalize(integrityPath),integrityLedgerSha256:integrity.sha256,
      lineageManifest:path.normalize(lineagePath),lineageManifestSha256:lineage.sha256,
      lineageManifestHeadSha256:evaluation.lineageManifestHeadSha256,
      captureArtifactCount:captures.length,
      checkpointArtifactCount:checkpointFiles.length,
    },
    evaluation,
    methodology:{
      checkpointedComputeOnly:true,
      allFiveVariantsRetained:true,
      currentOuterOosDoesNotSelectDynamicN:true,
      entryThresholdRelaxed:false,
      postHocWinnerFiltering:false,
      dailyMarketSpeedRequired:false,
      boardOrTickUsed:false,
      microstructureUsed:false,
      freshHoldoutConsumed:false,
    },
    safety:PHASE57_P25_3Q_SAFETY,
  };
  fs.mkdirSync(path.dirname(outputPath),{recursive:true});
  const tmp=`${outputPath}.tmp-${process.pid}`;
  fs.writeFileSync(tmp,JSON.stringify(payload,null,2)+'\n','utf8');
  fs.renameSync(tmp,outputPath);
  console.log(JSON.stringify({
    status:payload.status,
    output:outputPath,
    outputSha256:sha(fs.readFileSync(outputPath)),
    checkpointArtifactCount:checkpointFiles.length,
    lineageManifestHeadSha256:evaluation.lineageManifestHeadSha256,
    readyPacketCount:evaluation.result?.readyPacketCount??0,
    safety:PHASE57_P25_3Q_SAFETY,
  },null,2));
}catch(error){
  console.error(JSON.stringify({status:'BLOCKED_P25_3Q_CHECKPOINTED_EVALUATION',error:String(error?.message??error),safety:PHASE57_P25_3Q_SAFETY},null,2));
  process.exit(1);
}
