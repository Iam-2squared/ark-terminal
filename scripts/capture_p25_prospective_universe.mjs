import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {buildP252ProspectivePreopenUniverseRecord} from '../predict/daytrade/phase57-p25-2c-prospective-preopen-universe-capture.js';

const here=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(here,'..');
const snapshotPath=path.resolve(process.env.P25_SNAPSHOT_PATH||path.join(root,'data','screener-snapshot.json'));
const timelinePath=path.resolve(process.env.P25_TIMELINE_PATH||path.join(root,'data','p25-prospective-universe-timeline.ndjson'));

if(!fs.existsSync(snapshotPath))throw new Error(`P25 snapshot missing: ${snapshotPath}`);
const snapshot=JSON.parse(fs.readFileSync(snapshotPath,'utf8'));
const record=buildP252ProspectivePreopenUniverseRecord({snapshot});

const existing=fs.existsSync(timelinePath)
  ?fs.readFileSync(timelinePath,'utf8').split(/\r?\n/).filter(Boolean).map(line=>JSON.parse(line))
  :[];

const alreadyFrozen=existing.find(row=>row?.sessionDate===record.sessionDate&&row?.status==='PROSPECTIVE_PREOPEN_UNIVERSE_FROZEN');
if(alreadyFrozen){
  console.log(`P25_PROSPECTIVE_CAPTURE_ALREADY_FROZEN session=${record.sessionDate} generatedAt=${alreadyFrozen.sourceSnapshotGeneratedAt}`);
  process.exit(0);
}

const duplicateAttempt=existing.some(row=>
  row?.sessionDate===record.sessionDate&&
  row?.status===record.status&&
  row?.reason===record.reason&&
  row?.sourceSnapshotGeneratedAt===record.sourceSnapshotGeneratedAt
);
if(!duplicateAttempt){
  fs.mkdirSync(path.dirname(timelinePath),{recursive:true});
  fs.appendFileSync(timelinePath,`${JSON.stringify(record)}\n`,'utf8');
}

console.log(`P25_PROSPECTIVE_CAPTURE status=${record.status} session=${record.sessionDate} ready=${record.ready} eligible=${record.eligibleCount??0} output=${timelinePath}`);
