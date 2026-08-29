import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fetchP252Yahoo5mSession,PHASE57_P25_2J_SAFETY} from '../predict/daytrade/phase57-p25-2j-routine-nonrss-5m-source.js';

const arg=(name,fallback=null)=>{const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;};
const inputDir=arg('--input-dir');
const sessionDate=arg('--session-date');
const output=arg('--output',`tmp/p25-dynamic5m-daily-${sessionDate}.json`);
if(!inputDir||!/^\d{4}-\d{2}-\d{2}$/.test(String(sessionDate??'')))throw new Error('usage: --input-dir <dir> --session-date YYYY-MM-DD [--output file]');
const sha=value=>crypto.createHash('sha256').update(typeof value==='string'?value:JSON.stringify(value)).digest('hex');
const JST=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'});
function parts(ts){const p=Object.fromEntries(JST.formatToParts(new Date(ts)).map(x=>[x.type,x.value]));return {date:`${p.year}-${p.month}-${p.day}`,hm:`${p.hour}:${p.minute}`};}
function inSession(hm){return (hm>='09:00'&&hm<='11:30')||(hm>='12:30'&&hm<='15:30');}
function bucket(ts){return Math.floor(Date.parse(ts)/(5*60_000))*5*60_000;}
function walk(dir){const out=[];for(const ent of fs.readdirSync(dir,{withFileTypes:true})){const p=path.join(dir,ent.name);if(ent.isDirectory())out.push(...walk(p));else if(ent.isFile()&&ent.name==='measurement.json')out.push(p);}return out;}
const pointsByBucket=new Map();
for(const file of walk(inputDir)){
  let x;try{x=JSON.parse(fs.readFileSync(file,'utf8'));}catch{continue;}
  if(x?.status!=='MARKETWIDE_DYNAMIC_5M_MEASUREMENT_READY'||!Array.isArray(x?.selected)||Number(x?.inputSymbols)<3000)continue;
  const observedAt=String(x.observedAt??'');if(!Number.isFinite(Date.parse(observedAt)))continue;
  const p=parts(observedAt);if(p.date!==sessionDate||!inSession(p.hm))continue;
  const b=bucket(observedAt),key=new Date(b).toISOString();
  const selected=x.selected.map(r=>({symbol:String(r?.symbol??'').trim().toUpperCase(),sector:String(r?.sector??'UNKNOWN'),currentPrice:Number(r?.currentPrice),sourceScannedAt:r?.sourceScannedAt??observedAt,opportunityScore:Number(r?.opportunityScore),turnoverYen:Number(r?.turnoverYen)})).filter(r=>r.symbol);
  if(selected.length<20)continue;
  const candidate={bucket:key,observedAt,sourceFile:file,inputSymbols:Number(x.inputSymbols),selected,methodology:x.methodology,policy:x.policy,safety:x.safety};
  const prev=pointsByBucket.get(key);if(!prev||observedAt<prev.observedAt)pointsByBucket.set(key,candidate);
}
const points=[...pointsByBucket.values()].sort((a,b)=>a.bucket.localeCompare(b.bucket));
if(!points.length)throw new Error(`no valid Dynamic 5m point-in-time measurements for ${sessionDate}`);
const expected=[];
for(const [start,end] of [['09:00','11:30'],['12:30','15:30']]){
  let t=Date.parse(`${sessionDate}T${start}:00+09:00`),e=Date.parse(`${sessionDate}T${end}:00+09:00`);
  for(;t<=e;t+=5*60_000)expected.push(new Date(t).toISOString());
}
const actual=new Set(points.map(x=>x.bucket));
const missingExpectedBuckets=expected.filter(x=>!actual.has(x));
const symbols=[...new Set(points.flatMap(p=>p.selected.map(x=>x.symbol)))].sort();
const barsBySymbol={},failures=[];
let cursor=0;
async function worker(){while(cursor<symbols.length){const symbol=symbols[cursor++];try{const r=await fetchP252Yahoo5mSession({symbol,sessionDate});barsBySymbol[symbol]=r.bars;}catch(error){failures.push({symbol,reason:String(error?.message??error)});}}}
await Promise.all(Array.from({length:Math.min(8,symbols.length)},()=>worker()));
const completeBars=failures.length===0&&Object.keys(barsBySymbol).length===symbols.length;
const safety={...PHASE57_P25_2J_SAFETY,phase:'57.p25.dynamic5m-daily-bundle',mode:'READ_ONLY_DYNAMIC5M_DAILY_POINT_IN_TIME_BUNDLE'};
const payload={schemaVersion:1,phase:'57.p25.dynamic5m-daily-bundle',status:completeBars?'P25_DYNAMIC5M_DAILY_BUNDLE_READY':'BLOCKED_P25_DYNAMIC5M_DAILY_BUNDLE',sessionDate,createdAt:new Date().toISOString(),pointCount:points.length,expectedPointCount:expected.length,missingExpectedBucketCount:missingExpectedBuckets.length,missingExpectedBuckets,completeFiveMinuteCoverage:missingExpectedBuckets.length===0,selectedSymbolUnionCount:symbols.length,selectedSymbolUnion:symbols,points,barsReady:completeBars,barFailureCount:failures.length,barFailures:failures,sessionBarsBySymbol:barsBySymbol,methodology:{selectionMembershipCapturedPointInTime:true,scannerPriceRetainedAtObservedAt:true,postCloseBarsMayBeUsedOnlyAsPrefixAtRecordedSelectionCutoff:true,missingIntradayBucketsNeverBackfilledOrFabricated:true,fullDayValidityRequiresCompleteFiveMinuteCoverage:true,entryThresholdRelaxed:false,resultBasedRetuning:false,freshHoldoutConsumed:false},safety};
fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(payload,null,2)+'\n');
console.log(JSON.stringify({status:payload.status,sessionDate,pointCount:points.length,expectedPointCount:expected.length,missingExpectedBucketCount:missingExpectedBuckets.length,selectedSymbolUnionCount:symbols.length,barsReady:completeBars,sha256:sha(fs.readFileSync(output))},null,2));
if(!completeBars)process.exit(1);
