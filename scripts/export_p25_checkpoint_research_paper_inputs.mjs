import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { exportCheckpointedP25ResearchPaperInputs } from '../predict/paper/p25-checkpoint-research-export.js';
import { P25_SIGNAL_INTENT_SAFETY } from '../predict/paper/p25-signal-intent-adapter.js';

const arg=(name,fallback=null)=>{const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;};
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const load=file=>{const bytes=fs.readFileSync(file);return {bytes,sha256:sha(bytes),json:JSON.parse(bytes.toString('utf8'))};};

const historyPath=arg('--history-pack');
const captureDir=arg('--capture-dir');
const integrityPath=arg('--integrity-ledger');
const lineagePath=arg('--lineage-manifest');
const checkpointDir=arg('--checkpoint-dir');
const outputPath=arg('--output','data/p25-paper-export.json');
if(!historyPath||!captureDir||!integrityPath||!lineagePath||!checkpointDir){
  console.error('usage: node scripts/export_p25_checkpoint_research_paper_inputs.mjs --history-pack <json> --capture-dir <dir> --integrity-ledger <json> --lineage-manifest <json> --checkpoint-dir <dir> [--output <json>]');
  process.exit(2);
}

try{
  for(const [key,value] of Object.entries(P25_SIGNAL_INTENT_SAFETY))if(value!==false)throw new Error(`unsafe Paper export flag ${key}`);
  const history=load(historyPath),integrity=load(integrityPath),lineage=load(lineagePath);
  const captureFiles=fs.readdirSync(captureDir).filter(x=>x.endsWith('.json')).sort();
  const captureArtifacts=captureFiles.map(name=>{const loaded=load(path.join(captureDir,name));return {artifact:loaded.json,artifactSha256:loaded.sha256,artifactPath:name};});
  const checkpointFiles=fs.readdirSync(checkpointDir).filter(x=>x.endsWith('.json')).sort();
  const checkpointsBySession={};
  for(const name of checkpointFiles){
    const checkpoint=load(path.join(checkpointDir,name)).json;
    const sessionDate=String(checkpoint?.identities?.sessionDate??'');
    if(!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate))throw new Error(`checkpoint session identity invalid: ${name}`);
    (checkpointsBySession[sessionDate]??=[]).push(checkpoint);
  }
  const exported=exportCheckpointedP25ResearchPaperInputs({
    historyPack:history.json,
    captureArtifacts,
    sessionIntegrityLedger:integrity.json,
    lineageManifest:lineage.json,
    checkpointsBySession,
  });
  const payload={
    ...exported,
    schemaVersion:1,
    phase:'57.p25.3ac.checkpoint-research-paper-export-cli',
    status:'P25_CHECKPOINT_RESEARCH_PAPER_EXPORT_WRITTEN',
    createdAt:new Date().toISOString(),
    inputs:{
      historyPackSha256:history.sha256,
      integrityLedgerSha256:integrity.sha256,
      lineageManifestSha256:lineage.sha256,
      captureArtifactCount:captureFiles.length,
      checkpointArtifactCount:checkpointFiles.length,
    },
  };
  fs.mkdirSync(path.dirname(outputPath),{recursive:true});
  const tmp=`${outputPath}.tmp-${process.pid}`;
  fs.writeFileSync(tmp,JSON.stringify(payload,null,2)+'\n','utf8');
  fs.renameSync(tmp,outputPath);
  console.log(JSON.stringify({status:payload.status,output:outputPath,outputSha256:sha(fs.readFileSync(outputPath)),sessionCount:payload.sessionCount,lineageManifestHeadSha256:payload.lineageManifestHeadSha256,safety:payload.safety},null,2));
}catch(error){
  console.error(JSON.stringify({status:'BLOCKED_P25_CHECKPOINT_RESEARCH_PAPER_EXPORT',error:String(error?.message??error),safety:P25_SIGNAL_INTENT_SAFETY},null,2));
  process.exit(1);
}
