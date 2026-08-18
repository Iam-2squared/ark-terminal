import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {buildP253EvidenceLineageManifest,PHASE57_P25_3B_SAFETY} from '../predict/daytrade/phase57-p25-3b-evidence-lineage-manifest.js';

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
const outputPath=arg('--output','data/p25-evidence-lineage-manifest.json');
if(!historyPath||!captureDir||!integrityPath){
  console.error('usage: node scripts/build_p25_evidence_lineage_manifest.mjs --history-pack <json> --capture-dir <daily-json-dir> --integrity-ledger <json> [--output <json>]');
  process.exit(2);
}

try{
  const history=readJson(historyPath,'history pack');
  const integrity=readJson(integrityPath,'session integrity ledger');
  const files=fs.readdirSync(captureDir).filter(name=>name.endsWith('.json')).sort();
  const captures=files.map(name=>{
    const file=path.join(captureDir,name),loaded=readJson(file,`capture ${name}`);
    return {artifact:loaded.parsed,artifactSha256:loaded.sha256,artifactPath:name};
  });
  const manifest=buildP253EvidenceLineageManifest({
    historyPack:history.parsed,
    captureArtifacts:captures,
    sessionIntegrityLedger:integrity.parsed,
  });
  const payload={
    schemaVersion:1,
    phase:'57.p25.3b.evidence-lineage-manifest-cli',
    status:'P25_3_EVIDENCE_LINEAGE_ARTIFACT_WRITTEN',
    createdAt:new Date().toISOString(),
    inputs:{
      historyPack:path.normalize(historyPath),historyPackSha256:history.sha256,
      integrityLedger:path.normalize(integrityPath),integrityLedgerSha256:integrity.sha256,
      captureArtifactCount:captures.length,
    },
    manifest,
    safety:PHASE57_P25_3B_SAFETY,
  };
  fs.mkdirSync(path.dirname(outputPath),{recursive:true});
  const tmp=`${outputPath}.tmp-${process.pid}`;
  fs.writeFileSync(tmp,JSON.stringify(payload,null,2)+'\n','utf8');
  fs.renameSync(tmp,outputPath);
  console.log(JSON.stringify({
    status:payload.status,
    output:outputPath,
    outputSha256:sha(fs.readFileSync(outputPath)),
    nodeCount:manifest.nodeCount,
    chainSeedSha256:manifest.chainSeedSha256,
    manifestHeadSha256:manifest.manifestHeadSha256,
    dailyMarketSpeedRequired:false,
    safety:PHASE57_P25_3B_SAFETY,
  },null,2));
}catch(error){
  console.error(JSON.stringify({status:'BLOCKED_P25_3_EVIDENCE_LINEAGE',error:String(error?.message??error),safety:PHASE57_P25_3B_SAFETY},null,2));
  process.exit(1);
}
