import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {buildP253SessionIntegrityLedger,PHASE57_P25_3A_SAFETY} from '../predict/daytrade/phase57-p25-3a-session-integrity-ledger.js';

function arg(name,fallback=null){const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;}
function sha(bytes){return crypto.createHash('sha256').update(bytes).digest('hex');}
function readJson(file,label){
  const bytes=fs.readFileSync(file);
  let parsed;
  try{parsed=JSON.parse(bytes.toString('utf8'));}catch(error){throw new Error(`${label} JSON parse failed: ${error?.message??error}`);}
  return {parsed,sha256:sha(bytes)};
}

const inputDir=arg('--capture-dir');
const verifiedNonTradingPath=arg('--verified-nontrading',null);
const outputPath=arg('--output','data/p25-session-integrity-ledger.json');
if(!inputDir){
  console.error('usage: node scripts/build_p25_session_integrity_ledger.mjs --capture-dir <daily-json-dir> [--verified-nontrading <json>] [--output <json>]');
  process.exit(2);
}

try{
  const files=fs.readdirSync(inputDir).filter(name=>name.endsWith('.json')).sort();
  const captureArtifacts=files.map(name=>{
    const file=path.join(inputDir,name),loaded=readJson(file,`capture ${name}`);
    return {artifact:loaded.parsed,artifactSha256:loaded.sha256,artifactPath:name};
  });
  let verifiedNonTradingSessions=[];
  let verifiedNonTradingSha256=null;
  if(verifiedNonTradingPath){
    const loaded=readJson(verifiedNonTradingPath,'verified non-trading sessions');
    verifiedNonTradingSessions=Array.isArray(loaded.parsed)?loaded.parsed:(loaded.parsed?.sessions??[]);
    if(!Array.isArray(verifiedNonTradingSessions))throw new Error('verified non-trading file must be an array or contain sessions[]');
    verifiedNonTradingSha256=loaded.sha256;
  }
  const ledger=buildP253SessionIntegrityLedger({captureArtifacts,verifiedNonTradingSessions});
  const payload={
    schemaVersion:1,
    phase:'57.p25.3a.session-integrity-ledger-cli',
    status:'P25_3_SESSION_INTEGRITY_ARTIFACT_WRITTEN',
    createdAt:new Date().toISOString(),
    captureArtifactCount:captureArtifacts.length,
    verifiedNonTradingSha256,
    ledger,
    safety:PHASE57_P25_3A_SAFETY,
  };
  fs.mkdirSync(path.dirname(outputPath),{recursive:true});
  const tmp=`${outputPath}.tmp-${process.pid}`;
  fs.writeFileSync(tmp,JSON.stringify(payload,null,2)+'\n','utf8');
  fs.renameSync(tmp,outputPath);
  console.log(JSON.stringify({
    status:payload.status,
    output:outputPath,
    outputSha256:sha(fs.readFileSync(outputPath)),
    captureArtifactCount:ledger.captureArtifactCount,
    readyTradingSessionCount:ledger.readyTradingSessionCount,
    blockedConfirmedTradingSessionCount:ledger.blockedConfirmedTradingSessionCount,
    unresolvedSessionCount:ledger.unresolvedSessionCount,
    verifiedNonTradingSessionCount:ledger.verifiedNonTradingSessionCount,
    recommendedExpectedSessionDatesForP252H:ledger.recommendedExpectedSessionDatesForP252H,
    dailyMarketSpeedRequired:false,
    safety:PHASE57_P25_3A_SAFETY,
  },null,2));
}catch(error){
  console.error(JSON.stringify({status:'BLOCKED_P25_3_SESSION_INTEGRITY_LEDGER',error:String(error?.message??error),safety:PHASE57_P25_3A_SAFETY},null,2));
  process.exit(1);
}
