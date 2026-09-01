import fs from 'node:fs';
import path from 'node:path';

const arg=(name,fallback=null)=>{const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;};
const timelinePath=arg('--timeline');
const marketwideRoot=arg('--marketwide-root');
const sessionDate=arg('--session-date');
const outputDir=arg('--output-dir','tmp/p25-incomplete-session');
if(!timelinePath||!marketwideRoot||!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate??''))throw new Error('usage: --timeline <ndjson> --marketwide-root <dir> --session-date YYYY-MM-DD [--output-dir dir]');

const SAFETY_KEYS=['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed'];
const assertSafe=s=>{for(const k of SAFETY_KEYS)if(s?.[k]!==false)throw new Error(`unsafe ${k}`);};
const jstParts=iso=>{const d=new Date(iso);if(!Number.isFinite(d.getTime()))throw new Error(`invalid timestamp ${iso}`);const parts=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(d);const p=Object.fromEntries(parts.map(x=>[x.type,x.value]));return {date:`${p.year}-${p.month}-${p.day}`,hm:`${p.hour}:${p.minute}`};};
const floor5=hm=>{const [h,m]=hm.split(':').map(Number),x=h*60+m,y=Math.floor(x/5)*5;return `${String(Math.floor(y/60)).padStart(2,'0')}:${String(y%60).padStart(2,'0')}`;};
const mins=hm=>{const [h,m]=hm.split(':').map(Number);return h*60+m;};
const hm=t=>`${String(Math.floor(t/60)).padStart(2,'0')}:${String(t%60).padStart(2,'0')}`;

const timeline=fs.readFileSync(timelinePath,'utf8').split(/\r?\n/).filter(Boolean).map(line=>JSON.parse(line));
const preopen=timeline.filter(x=>x?.sessionDate===sessionDate&&x?.status==='PROSPECTIVE_PREOPEN_UNIVERSE_FROZEN'&&x?.ready===true).at(-1);
if(!preopen)throw new Error(`prospective pre-open freeze missing for ${sessionDate}`);
assertSafe(preopen.safety);
const expectedVariants={FIXED_5:5,OLD_FIXED_30:30,DYNAMIC_30:30,DYNAMIC_40:40,DYNAMIC_50:50};
for(const [k,n] of Object.entries(expectedVariants))if(!Array.isArray(preopen.variants?.[k])||preopen.variants[k].length!==n)throw new Error(`pre-open ${k} cardinality mismatch`);
const d30=preopen.variants.DYNAMIC_30,d40=preopen.variants.DYNAMIC_40,d50=preopen.variants.DYNAMIC_50;
if(!d30.every((x,i)=>d40[i]===x)||!d40.every((x,i)=>d50[i]===x))throw new Error('pre-open D30/D40/D50 nesting mismatch');

const dateRoot=path.join(marketwideRoot,sessionDate);
if(!fs.existsSync(dateRoot))throw new Error(`marketwide durable date missing ${dateRoot}`);
const measurementFiles=[];
for(const e of fs.readdirSync(dateRoot,{withFileTypes:true})){
  if(!e.isDirectory())continue;
  const f=path.join(dateRoot,e.name,'measurement.json');
  if(fs.existsSync(f))measurementFiles.push(f);
}
const byBucket=new Map();
for(const f of measurementFiles){
  const x=JSON.parse(fs.readFileSync(f,'utf8'));
  if(x?.status!=='MARKETWIDE_DYNAMIC_5M_MEASUREMENT_READY'||Number(x?.inputSymbols)<3000)continue;
  assertSafe(x.safety);
  const p=jstParts(x.observedAt);if(p.date!==sessionDate)continue;
  const bucket=floor5(p.hm),m=mins(bucket);if(m<9*60||m>15*60+30)continue;
  const prev=byBucket.get(bucket);if(!prev||String(x.observedAt)<String(prev.observedAt))byBucket.set(bucket,x);
}
const points=[...byBucket.entries()].sort((a,b)=>a[0].localeCompare(b[0]));
if(!points.length)throw new Error(`no genuine marketwide points for ${sessionDate}`);
const firstBucket=points[0][0],lastBucket=points.at(-1)[0];
if(lastBucket<'15:00')throw new Error(`session evidence ends too early: ${lastBucket}`);

const expected=[];
for(let t=Math.max(mins(firstBucket),9*60);t<=11*60+30;t+=5)expected.push(hm(t));
for(let t=12*60+30;t<=Math.min(mins(lastBucket),15*60+30);t+=5)expected.push(hm(t));
const present=new Set(points.map(([b])=>b));
const missing=expected.filter(x=>!present.has(x));
const internalMissing=missing.filter(x=>mins(x)>=mins(firstBucket)&&mins(x)<=mins(lastBucket));
if(!missing.length)throw new Error('incomplete-session builder must not be used for a complete session');

const safety={...preopen.safety};assertSafe(safety);
const freeze={...preopen,phase:'57.p25.incomplete-session-partial-wrapper',status:'PARTIAL_LATE_START_D50_FROZEN',ready:true,sessionType:'PARTIAL_LATE_START',frozenAt:preopen.sourceSnapshotGeneratedAt??new Date(`${sessionDate}T00:00:00+09:00`).toISOString(),startTimeJst:firstBucket,endTimeJst:lastBucket,classification:{requestedSessionType:'PARTIAL_INCOMPLETE_SESSION',formalFullSession:false,formalOos:false,promotionEligible:false,missingExpectedBuckets:missing,hasInternalGap:internalMissing.length>0},methodology:{...(preopen.methodology??{}),sourceProspectivelyFrozenBeforeOpen:true,wrapperCreatedAfterSession:true,selectionRetuned:false,historicalBackfill:false,missingBucketsFabricated:false,formalFullSession:false,formalOos:false,promotionEligible:false},safety};
const manifest={schemaVersion:1,phase:'57.p25.incomplete-session-partial-substrate',status:'PARTIAL_FRESH_SUBSTRATE_READY',sessionType:'PARTIAL_LATE_START',requestedSessionType:'PARTIAL_INCOMPLETE_SESSION',formalFullSession:false,formalOos:false,promotionEligible:false,sessionDate,createdAt:new Date().toISOString(),dynamicPointCount:points.length,firstObservedBucketJst:firstBucket,lastObservedBucketJst:lastBucket,expectedBucketCount:expected.length,missingExpectedBucketCount:missing.length,missingExpectedBuckets:missing,hasInternalGap:internalMissing.length>0,internalMissingBuckets:internalMissing,sourceProspectiveFreeze:{captureHmJst:preopen.captureHmJst,sourceSnapshotGeneratedAt:preopen.sourceSnapshotGeneratedAt,sourceSnapshotFingerprint:preopen.sourceSnapshotFingerprint},methodology:{actualDurablePointsOnly:true,pointInTimeSelectionMembership:true,noBackfillOrFabrication:true,noOutcomeRetuning:true,fullSessionClaimForbidden:true},safety};

fs.mkdirSync(outputDir,{recursive:true});
fs.writeFileSync(path.join(outputDir,'freeze.json'),JSON.stringify(freeze,null,2)+'\n');
fs.writeFileSync(path.join(outputDir,'partial-manifest.json'),JSON.stringify(manifest,null,2)+'\n');
fs.writeFileSync(path.join(outputDir,'partial-measurements.ndjson'),points.map(([,x])=>JSON.stringify(x)).join('\n')+'\n');
console.log(JSON.stringify({status:manifest.status,sessionDate,pointCount:points.length,firstBucket,lastBucket,missingExpectedBucketCount:missing.length,missingExpectedBuckets:missing,classification:'PARTIAL_INCOMPLETE_SESSION'},null,2));
