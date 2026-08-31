import fs from 'node:fs';
import path from 'node:path';
import {buildP252PointInTimeUniverseAtDecision} from '../predict/daytrade/phase57-p25-2b-point-in-time-oos-substrate.js';
import {PHASE57_P25_2C_SAFETY,PHASE57_P25_2C_POLICY} from '../predict/daytrade/phase57-p25-2c-prospective-preopen-universe-capture.js';

const args=new Map();
for(let i=2;i<process.argv.length;i+=2)args.set(process.argv[i],process.argv[i+1]);
const input=args.get('--input')||'data/screener-snapshot.json';
const output=args.get('--output')||'tmp/p25-partial-freeze.json';
const snapshot=JSON.parse(fs.readFileSync(input,'utf8'));
const generatedAt=snapshot?.meta?.generatedAt??snapshot?.generatedAt;
if(!generatedAt||!Number.isFinite(Date.parse(generatedAt)))throw new Error('partial freeze requires valid snapshot generatedAt');
if(snapshot?.meta?.refreshProgress?.cycleComplete!==true)throw new Error('partial freeze requires a completed screener cycle');

const jst=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'});
const parts=Object.fromEntries(jst.formatToParts(new Date(generatedAt)).map(x=>[x.type,x.value]));
const sessionDate=`${parts.year}-${parts.month}-${parts.day}`;
const captureHmJst=`${parts.hour}:${parts.minute}`;
const nowJstHm=captureHmJst;
if(nowJstHm<'09:00'||nowJstHm>='11:30')throw new Error(`partial recovery freeze must occur during morning session: ${nowJstHm}`);

const pit=buildP252PointInTimeUniverseAtDecision({
  sessionDate,
  decisionTimestamp:generatedAt,
  snapshots:[snapshot],
  minimumEligibleCrossSection:PHASE57_P25_2C_POLICY.minimumEligibleCrossSection,
  maxPerSector:PHASE57_P25_2C_POLICY.maxPerSector,
  maxSnapshotAgeMs:0,
  maxRowAgeMs:PHASE57_P25_2C_POLICY.maxRowAgeMs,
});
if(!pit.ready)throw new Error(`partial D50 PIT not ready: ${pit.reason}`);

const ms=Date.parse(generatedAt);
const nextBoundary=new Date(Math.ceil(ms/(5*60*1000))*(5*60*1000));
const nextParts=Object.fromEntries(jst.formatToParts(nextBoundary).map(x=>[x.type,x.value]));
const startTimeJst=`${nextParts.hour}:${nextParts.minute}`;
if(startTimeJst>'11:25')throw new Error(`too late to create useful morning partial session: ${startTimeJst}`);

const record={
  phase:'57.p25.partial-fresh-recovery',
  status:'PARTIAL_LATE_START_D50_FROZEN',
  ready:true,
  sessionType:'PARTIAL_LATE_START',
  sessionDate,
  frozenAt:generatedAt,
  captureHmJst,
  startTimeJst,
  endTimeJst:'11:30',
  sourceSnapshotFingerprint:pit.sourceSnapshotFingerprint,
  inputCount:pit.inputCount,
  eligibleCount:pit.eligibleCount,
  variants:pit.variants,
  rankAudit:pit.rankAudit,
  methodology:{
    prospectiveOnly:true,
    historicalBackfill:false,
    partialSession:true,
    preOpenBaseline:false,
    exactStartFrozenBeforeOutcomeWindow:true,
    currentOuterOosPerformanceUsed:false,
    entryThresholdRelaxed:false,
    missingEarlierBucketsNeverBackfilledOrFabricated:true,
    freshHoldoutConsumed:false,
  },
  safety:PHASE57_P25_2C_SAFETY,
};
fs.mkdirSync(path.dirname(output),{recursive:true});
fs.writeFileSync(output,JSON.stringify(record,null,2)+'\n','utf8');
console.log(JSON.stringify({status:record.status,sessionDate,startTimeJst,eligibleCount:record.eligibleCount,d50:record.variants?.DYNAMIC_50?.symbols?.length??record.variants?.DYNAMIC_50?.length??null},null,2));
