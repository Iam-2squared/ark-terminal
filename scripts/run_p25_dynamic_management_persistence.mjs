import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {runP253ALDynamicManagementMultisession,PHASE57_P25_3AL_SAFETY} from '../predict/daytrade/phase57-p25-3al-dynamic-management-multisession.js';

function arg(name,fallback=null){const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;}
function sha(bytes){return crypto.createHash('sha256').update(bytes).digest('hex');}
function readJson(file,label){const bytes=fs.readFileSync(file);let parsed;try{parsed=JSON.parse(bytes.toString('utf8'));}catch(error){throw new Error(`${label} JSON parse failed: ${error?.message??error}`);}return {parsed,sha256:sha(bytes)};}
function writeAtomic(file,value){fs.mkdirSync(path.dirname(file),{recursive:true});const tmp=`${file}.tmp-${process.pid}`;fs.writeFileSync(tmp,JSON.stringify(value,null,2)+'\n','utf8');fs.renameSync(tmp,file);}

const historyPath=arg('--history-pack');
const captureDir=arg('--capture-dir');
const integrityPath=arg('--integrity-ledger');
const lineagePath=arg('--lineage-manifest');
const sessionDate=arg('--session-date');
const outputPath=arg('--output','data/p25-dynamic-management/evaluation.json');
const scorecardPath=arg('--scorecard','data/p25-dynamic-management/scorecard.json');
if(!historyPath||!captureDir||!integrityPath||!lineagePath){console.error('usage: node scripts/run_p25_dynamic_management_persistence.mjs --history-pack <json> --capture-dir <dir> --integrity-ledger <json> --lineage-manifest <json> [--session-date YYYY-MM-DD] [--output <json>] [--scorecard <json>]');process.exit(2);}
if(sessionDate&&!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate)){console.error('invalid --session-date');process.exit(2);}

try{
  const history=readJson(historyPath,'history pack');
  const integrity=readJson(integrityPath,'session integrity ledger');
  const lineage=readJson(lineagePath,'evidence lineage manifest');
  const files=fs.readdirSync(captureDir).filter(name=>name.endsWith('.json')).sort();
  const captures=files.map(name=>{const file=path.join(captureDir,name),loaded=readJson(file,`capture ${name}`);return {artifact:loaded.parsed,artifactSha256:loaded.sha256,artifactPath:name};});
  const evaluation=runP253ALDynamicManagementMultisession({historyPack:history.parsed,captureArtifacts:captures,sessionIntegrityLedger:integrity.parsed,lineageManifest:lineage.parsed,sessionDates:sessionDate?[sessionDate]:null});
  const createdAt=new Date().toISOString();
  const payload={
    schemaVersion:1,
    phase:'57.p25.3am.dynamic-management-sharded-persistence-cli',
    status:'P25_3AM_DYNAMIC_MANAGEMENT_SHARD_WRITTEN',
    createdAt,
    shard:{sessionDate:sessionDate??null,executionOnly:true},
    inputs:{
      historyPackSha256:history.sha256,
      integrityLedgerSha256:integrity.sha256,
      lineageManifestSha256:lineage.sha256,
      lineageManifestHeadSha256:evaluation.lineageManifestHeadSha256,
      captureArtifactCount:captures.length,
    },
    evaluation,
    methodology:{appendOnlyTarget:true,idempotentByEvidenceDateAndLineage:true,fixedBaselineUntouched:true,executionShardSelectionOnly:true,resultBasedRetuning:false,winnerSelection:false,freshHoldoutConsumed:false},
    safety:PHASE57_P25_3AL_SAFETY,
  };
  const scorecard={
    schemaVersion:1,
    phase:'57.p25.3am.dynamic-management-shard-scorecard',
    status:'P25_3AM_DYNAMIC_MANAGEMENT_SHARD_SCORECARD_READY',
    createdAt,
    shard:{sessionDate:sessionDate??null,executionOnly:true},
    lineageManifestHeadSha256:evaluation.lineageManifestHeadSha256,
    expectedSessionCount:evaluation.expectedSessionCount,
    readySessionCount:evaluation.readySessionCount,
    sessions:evaluation.sessions,
    summary:evaluation.summary,
    byVariant:evaluation.byVariant,
    methodology:{descriptiveOnly:true,fixedVsDynamicPaired:true,executionShardSelectionOnly:true,winnerSelection:false,resultBasedRetuning:false,freshHoldoutConsumed:false},
    safety:PHASE57_P25_3AL_SAFETY,
  };
  writeAtomic(outputPath,payload);
  writeAtomic(scorecardPath,scorecard);
  console.log(JSON.stringify({status:payload.status,sessionDate:sessionDate??null,output:outputPath,outputSha256:sha(fs.readFileSync(outputPath)),scorecard:scorecardPath,scorecardSha256:sha(fs.readFileSync(scorecardPath)),lineageManifestHeadSha256:evaluation.lineageManifestHeadSha256,pairedCount:evaluation.summary.pairedCount,readySessionCount:evaluation.readySessionCount,safety:PHASE57_P25_3AL_SAFETY},null,2));
}catch(error){console.error(JSON.stringify({status:'BLOCKED_P25_3AM_DYNAMIC_MANAGEMENT_SHARD',sessionDate:sessionDate??null,error:String(error?.message??error),safety:PHASE57_P25_3AL_SAFETY},null,2));process.exit(1);}
