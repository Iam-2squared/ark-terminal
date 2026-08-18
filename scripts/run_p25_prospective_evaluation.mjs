import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {runP252EndToEndProspectiveEvaluation,PHASE57_P25_2I_SAFETY} from '../predict/daytrade/phase57-p25-2i-end-to-end-prospective-evaluation.js';

function arg(name,fallback=null){const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;}
function sha(bytes){return crypto.createHash('sha256').update(bytes).digest('hex');}
function readJson(file,label){
  const bytes=fs.readFileSync(file);
  let parsed;
  try{parsed=JSON.parse(bytes.toString('utf8'));}catch(error){throw new Error(`${label} JSON parse failed: ${error?.message??error}`);}
  return {parsed,sha256:sha(bytes)};
}

const historyPath=arg('--history-pack');
const bundlePath=arg('--session-bundle');
const outputPath=arg('--output','data/p25-prospective-evaluation.json');
if(!historyPath||!bundlePath){
  console.error('usage: node scripts/run_p25_prospective_evaluation.mjs --history-pack <json> --session-bundle <json> [--output <json>]');
  process.exit(2);
}

try{
  const history=readJson(historyPath,'history pack');
  const bundle=readJson(bundlePath,'session bundle');
  const historicalSessions=Array.isArray(history.parsed)?history.parsed:history.parsed?.sessions;
  const sessionInputs=Array.isArray(bundle.parsed)?bundle.parsed:(bundle.parsed?.sessionInputs??bundle.parsed?.sessions);
  const expectedSessionDates=Array.isArray(bundle.parsed?.expectedSessionDates)?bundle.parsed.expectedSessionDates:[];
  if(!Array.isArray(historicalSessions))throw new Error('history pack must be an array or contain sessions[]');
  if(!Array.isArray(sessionInputs))throw new Error('session bundle must be an array or contain sessionInputs[]/sessions[]');

  const result=runP252EndToEndProspectiveEvaluation({historicalSessions,sessionInputs,expectedSessionDates});
  const payload={
    schemaVersion:1,
    phase:'57.p25.2i.end-to-end-prospective-evaluation-cli',
    status:'P25_2_END_TO_END_ARTIFACT_WRITTEN',
    createdAt:new Date().toISOString(),
    inputs:{
      historyPack:path.normalize(historyPath),
      historyPackSha256:history.sha256,
      sessionBundle:path.normalize(bundlePath),
      sessionBundleSha256:bundle.sha256,
    },
    result,
    methodology:{
      providerAgnosticSessionBars:true,
      dailyMarketSpeedRequired:false,
      marketSpeedVerificationSeparate:true,
      boardOrTickUsed:false,
      currentOuterOosDoesNotSelectDynamicN:true,
      freshHoldoutConsumed:false,
    },
    safety:PHASE57_P25_2I_SAFETY,
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
    readyPacketCount:result.readyPacketCount,
    blockedSessionCount:result.blockedSessionCount,
    expectedTradingSessionCount:result.expectedTradingSessionCount,
    dailyMarketSpeedRequired:false,
    safety:PHASE57_P25_2I_SAFETY,
  },null,2));
}catch(error){
  console.error(JSON.stringify({status:'BLOCKED_P25_2_END_TO_END_EVALUATION',error:String(error?.message??error),safety:PHASE57_P25_2I_SAFETY},null,2));
  process.exit(1);
}
