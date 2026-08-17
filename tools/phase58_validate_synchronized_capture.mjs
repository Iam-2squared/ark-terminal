import fs from 'node:fs';
import crypto from 'node:crypto';
import {validateFrozenPhase57Snapshot} from '../predict/scalping/phase58-phase57-snapshot-contract.js';

const path=process.argv[2];
if(!path){
  console.error('usage: node tools/phase58_validate_synchronized_capture.mjs <sync.jsonl>');
  process.exit(2);
}

const bytes=fs.readFileSync(path);
const datasetSha256=crypto.createHash('sha256').update(bytes).digest('hex');
const lines=bytes.toString('utf8').split(/\r?\n/).filter(Boolean);
const blockers=[];
let ready=0,wait=0,long=0,short=0;
const modelIds=new Set(),artifactShas=new Set(),snapshotFileShas=new Set();
let maxAgeSeconds=0;

for(let i=0;i<lines.length;i+=1){
  let row;
  try{row=JSON.parse(lines[i]);}catch{blockers.push(`ROW_${i+1}_MALFORMED_JSON`);continue;}
  if(row?.phase!=='58.p9.sync-capture')blockers.push(`ROW_${i+1}_WRONG_PHASE`);
  if(row?.sourceMode!=='MARKETSPEED_II_RSS_READ_ONLY')blockers.push(`ROW_${i+1}_WRONG_SOURCE_MODE`);
  const safety=row?.safety??{};
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed']){
    if(safety[key]!==false)blockers.push(`ROW_${i+1}_UNSAFE_${key}`);
  }
  if(row?.methodology?.phase58MayReverseDirection!==false)blockers.push(`ROW_${i+1}_PHASE58_DIRECTION_REVERSAL_GUARD_MISSING`);
  if(row?.methodology?.historicalDecisionReconstructionAllowed!==false)blockers.push(`ROW_${i+1}_HISTORICAL_RECONSTRUCTION_GUARD_MISSING`);
  const validation=validateFrozenPhase57Snapshot(row?.phase57Snapshot,{captureAsOf:row?.capturedAt});
  if(!validation.complete){
    for(const b of validation.blockers)blockers.push(`ROW_${i+1}_${b}`);
    continue;
  }
  ready+=1;
  const d=validation.normalized.direction;
  if(d>0)long+=1;else if(d<0)short+=1;else wait+=1;
  if(validation.normalized.modelId)modelIds.add(validation.normalized.modelId);
  if(validation.normalized.artifactSha256)artifactShas.add(validation.normalized.artifactSha256);
  if(typeof row?.phase57SnapshotFileSha256==='string')snapshotFileShas.add(row.phase57SnapshotFileSha256);
  const age=(Date.parse(row.capturedAt)-Date.parse(validation.normalized.asOf))/1000;
  if(Number.isFinite(age))maxAgeSeconds=Math.max(maxAgeSeconds,age);
}

const uniqueBlockers=[...new Set(blockers)];
const out={
  phase:'58.p9.sync-dataset-validator',
  status:uniqueBlockers.length?'BLOCKED':'PHASE58_SYNCHRONIZED_DATASET_READY',
  complete:uniqueBlockers.length===0&&ready===lines.length&&lines.length>0,
  path,
  datasetSha256,
  rowCount:lines.length,
  readyRows:ready,
  directions:{long,short,wait},
  provenance:{modelIds:[...modelIds],artifactSha256:[...artifactShas],snapshotFileSha256Count:snapshotFileShas.size},
  maxPhase57AgeSeconds:maxAgeSeconds,
  blockers:uniqueBlockers,
  methodology:{phase57DirectionIsFrozenBase:true,phase58MayReverseDirection:false,prospectiveOnly:true,freshHoldoutConsumed:false},
  safety:{executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,freshHoldoutConsumed:false},
};
console.log(JSON.stringify(out,null,2));
if(!out.complete)process.exitCode=1;
