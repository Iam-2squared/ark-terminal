import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {buildSwingS1ProspectiveUniverseRecord,PHASE56_SWING_S1_SAFETY} from '../predict/swing/phase56-s1-jpx-prospective-universe.js';

function arg(name,fallback=null){const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;}
function sha(bytes){return crypto.createHash('sha256').update(bytes).digest('hex');}

const snapshotPath=arg('--snapshot');
const outputPath=arg('--output','data/swing-s1-prospective-universe.json');
if(!snapshotPath){
  console.error('usage: node scripts/capture_swing_s1_prospective_universe.mjs --snapshot <screener-snapshot.json> [--output <json>]');
  process.exit(2);
}

try{
  const bytes=fs.readFileSync(snapshotPath);
  let snapshot;
  try{snapshot=JSON.parse(bytes.toString('utf8'));}catch(error){throw new Error(`snapshot JSON parse failed: ${error?.message??error}`);}
  const record=buildSwingS1ProspectiveUniverseRecord({snapshot});
  const payload={
    schemaVersion:1,
    phase:'56.swing.s1.jpx-prospective-universe-cli',
    status:record.ready?'SWING_S1_PROSPECTIVE_UNIVERSE_ARTIFACT_WRITTEN':'BLOCKED_SWING_S1_PROSPECTIVE_UNIVERSE_ARTIFACT_WRITTEN',
    createdAt:new Date().toISOString(),
    inputs:{snapshot:path.normalize(snapshotPath),snapshotSha256:sha(bytes)},
    record,
    methodology:{
      pointInTimeOnly:true,
      directionAgnosticOpportunityStrength:true,
      currentOuterOosDoesNotSelectUniverseSize:true,
      currentOuterOosDoesNotSelectHorizon:true,
      dailyMarketSpeedRequired:false,
      boardOrTickUsed:false,
      microstructureUsed:false,
      freshHoldoutConsumed:false,
    },
    safety:PHASE56_SWING_S1_SAFETY,
  };
  fs.mkdirSync(path.dirname(outputPath),{recursive:true});
  const tmp=`${outputPath}.tmp-${process.pid}`;
  fs.writeFileSync(tmp,JSON.stringify(payload,null,2)+'\n','utf8');
  fs.renameSync(tmp,outputPath);
  console.log(JSON.stringify({
    status:payload.status,
    output:outputPath,
    outputSha256:sha(fs.readFileSync(outputPath)),
    ready:record.ready,
    sessionDate:record.sessionDate,
    eligibleCount:record.eligibleCount,
    dynamic30:record.variants?.SWING_DYNAMIC_30?.length??0,
    dynamic40:record.variants?.SWING_DYNAMIC_40?.length??0,
    dynamic50:record.variants?.SWING_DYNAMIC_50?.length??0,
    dailyMarketSpeedRequired:false,
    safety:PHASE56_SWING_S1_SAFETY,
  },null,2));
  if(!record.ready)process.exitCode=1;
}catch(error){
  console.error(JSON.stringify({status:'BLOCKED_SWING_S1_PROSPECTIVE_UNIVERSE',error:String(error?.message??error),safety:PHASE56_SWING_S1_SAFETY},null,2));
  process.exit(1);
}
