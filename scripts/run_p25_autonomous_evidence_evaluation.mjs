import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {runP253AutonomousEvidenceEvaluation,PHASE57_P25_3D_SAFETY} from '../predict/daytrade/phase57-p25-3d-autonomous-evidence-evaluation.js';

function arg(name,fallback=null){const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;}
function sha(bytes){return crypto.createHash('sha256').update(bytes).digest('hex');}
function readJson(file,label){
  const bytes=fs.readFileSync(file);
  let parsed;
  try{parsed=JSON.parse(bytes.toString('utf8'));}catch(error){throw new Error(`${label} JSON parse failed: ${error?.message??error}`);}
  return {parsed,sha256:sha(bytes)};
}

const historyPath=arg('--history-pack');
const captureDir=arg('--capture-dir');
const integrityPath=arg('--integrity-ledger');
const lineagePath=arg('--lineage-manifest');
const outputPath=arg('--output','data/p25-autonomous-evidence-evaluation.json');
if(!historyPath||!captureDir||!integrityPath||!lineagePath){
  console.error('usage: node scripts/run_p25_autonomous_evidence_evaluation.mjs --history-pack <json> --capture-dir <daily-json-dir> --integrity-ledger <json> --lineage-manifest <json> [--output <json>]');
  process.exit(2);
}

try{
  const history=readJson(historyPath,'history pack');
  const integrity=readJson(integrityPath,'session integrity ledger');
  const lineage=readJson(lineagePath,'evidence lineage manifest');
  const files=fs.readdirSync(captureDir).filter(name=>name.endsWith('.json')).sort();
  const captures=files.map(name=>{
    const file=path.join(captureDir,name),loaded=readJson(file,`capture ${name}`);
    return {artifact:loaded.parsed,artifactSha256:loaded.sha256,artifactPath:name};
  });

  const evaluation=runP253AutonomousEvidenceEvaluation({
    historyPack:history.parsed,
    captureArtifacts:captures,
    sessionIntegrityLedger:integrity.parsed,
    lineageManifest:lineage.parsed,
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
    },
    evaluation,
    methodology:{
      allFiveVariantsRetained:true,
      currentOuterOosDoesNotSelectDynamicN:true,
      entryThresholdRelaxed:false,
      postHocWinnerFiltering:false,
      dailyMarketSpeedRequired:false,
      boardOrTickUsed:false,
      microstructureUsed:false,
      freshHoldoutConsumed:false,
    },
    safety:PHASE57_P25_3D_SAFETY,
  };
  fs.mkdirSync(path.dirname(outputPath),{recursive:true});
  const tmp=`${outputPath}.tmp-${process.pid}`;
  fs.writeFileSync(tmp,JSON.stringify(payload,null,2)+'\n','utf8');
  fs.renameSync(tmp,outputPath);
  const outputSha256=sha(fs.readFileSync(outputPath));
  console.log(JSON.stringify({
    status:payload.status,
    output:outputPath,
    outputSha256,
    lineageManifestHeadSha256:evaluation.lineageManifestHeadSha256,
    frozenReadySessionInputCount:evaluation.frozenReadySessionInputCount,
    expectedSessionCount:evaluation.expectedSessionCount,
    readyPacketCount:evaluation.result?.readyPacketCount??0,
    blockedSessionCount:evaluation.result?.blockedSessionCount??0,
    dynamicNSelectedFromCurrentOuterOos:false,
    dailyMarketSpeedRequired:false,
    safety:PHASE57_P25_3D_SAFETY,
  },null,2));
}catch(error){
  console.error(JSON.stringify({status:'BLOCKED_P25_3_AUTONOMOUS_EVIDENCE_EVALUATION',error:String(error?.message??error),safety:PHASE57_P25_3D_SAFETY},null,2));
  process.exit(1);
}
