// Existing 76-session Development cache ONLY. No provider client, model or order imports.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gunzipSync,gzipSync} from 'node:zlib';
import {pathToFileURL} from 'node:url';
const sha=b=>createHash('sha256').update(b).digest('hex');
const parse=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const EV='docs/evidence/phase57-msh-entry-long-v1-preimplementation-feasibility-events.ndjson.gz';
const PATHS='docs/evidence/phase57-msh-entry-long-v2-development/paths.json.gz';
const NORMAL='predict/long-only/phase57-long-only-integrated-dataset.js';
const PINS={[EV]:'73e566aba4d1a3f5af33b74be52ae90736c088b1091841f1eb44e93d5476084c',[PATHS]:'9b051b630c1e5ac59fac42f0da32830f38e07c48ded56a26e2dec4c054a4b7ba',[NORMAL]:'390e2df4ddc0be571d285e05754ce9ad90f2618eb5902797cf8e7bae4a5f667f'};
const SAFETY=Object.fromEntries(['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted'].map(k=>[k,false]));
const numeric=(r,...keys)=>{for(const k of keys){const x=r[k];if(x===null||x===undefined||x===''||typeof x==='boolean')continue;const v=Number(x);if(Number.isFinite(v))return v;}return null;};
const minute=t=>{const x=String(t??'').match(/(\d{2}):(\d{2})/);return x?Number(x[1])*60+Number(x[2]):NaN;};
const regular=(m,date)=>(m>=540&&m<690)||(m>=750&&m<(date<'2024-11-05'?900:930));
const iso=(date,m)=>`${date}T${String(Math.floor(m/60)).padStart(2,'0')}:${String(m%60).padStart(2,'0')}:00+09:00`;
export function indexMinutes(raw,date,symbols){
 const maps=new Map([...symbols].map(s=>[s,new Map()]));const audit={accepted:0,invalid:0,duplicates:0};
 for(const r of raw){
  assert.equal(r.Date??r.date,date,'DATE_SCOPE');
  const symbol=String(r.Code??r.code??r.symbol??'').trim().toUpperCase();if(!symbols.has(symbol))continue;
  const m=minute(r.Time??r.time);if(!regular(m,date))continue;
  const vals={o:numeric(r,'O','Open','open'),h:numeric(r,'H','High','high'),l:numeric(r,'L','Low','low'),c:numeric(r,'C','Close','close')};
  if(!Object.values(vals).every(x=>x!==null&&x>0)||vals.h<Math.max(vals.o,vals.c)||vals.l>Math.min(vals.o,vals.c)||vals.h<vals.l){audit.invalid++;continue;}
  const map=maps.get(symbol);
  if(map.has(m)){assert.deepEqual(map.get(m),vals,'CONFLICTING_MINUTE_PRICE');audit.duplicates++;continue;}
  map.set(m,vals);audit.accepted++;
 }
 return {maps,audit};
}
export function project(e,map){
 const date=e.sessionDate,t0=minute(e.decisionTimestamp),ref=e.decisionPrice;
 assert.ok(ref>0&&Number.isFinite(ref),'BAD_REFERENCE');
 const one=d=>{const m=t0+d;if(!regular(m,date))return {offsetStart:d,availableOffset:d+1,boundary:true,missing:true};
  const r=map.get(m);if(!r)return {offsetStart:d,availableOffset:d+1,start:iso(date,m),end:iso(date,m+1),missing:true};
  return {offsetStart:d,availableOffset:d+1,start:iso(date,m),end:iso(date,m+1),missing:false,...Object.fromEntries(Object.entries(r).map(([k,v])=>[k,100*(v/ref-1)]))};};
 return {eventId:e.selectorEventId,symbolSessionId:e.symbolSessionId,symbol:e.symbol,sessionDate:date,decisionTimestamp:e.decisionTimestamp,
  prefix:[-5,-4,-3,-2,-1].map(one),future:Array.from({length:60},(_,i)=>one(i))};
}
function selfTest(){
 let n=0;const test=fn=>{fn();n++;};
 test(()=>assert.equal(numeric({O:null},'O'),null));test(()=>assert.equal(numeric({O:0},'O'),0));test(()=>assert.equal(numeric({O:''},'O'),null));
 test(()=>assert.equal(regular(690,'2024-09-17'),false));test(()=>assert.equal(regular(900,'2024-09-17'),false));test(()=>assert.equal(regular(900,'2024-11-05'),true));
 const r={Date:'2024-09-17',Code:'12340',Time:'09:30',O:100,H:102,L:99,C:101};
 const a=indexMinutes([r],r.Date,new Set(['12340']));test(()=>assert.equal(a.audit.accepted,1));
 test(()=>assert.equal(indexMinutes([r,r],r.Date,new Set(['12340'])).audit.duplicates,1));
 test(()=>assert.throws(()=>indexMinutes([r,{...r,C:100}],r.Date,new Set(['12340']))));
 test(()=>assert.throws(()=>indexMinutes([{...r,Date:'2026-01-01'}],r.Date,new Set(['12340']))));
 test(()=>assert.equal(indexMinutes([{...r,O:null}],r.Date,new Set(['12340'])).audit.invalid,1));
 const e={selectorEventId:'a',symbolSessionId:'d|12340',symbol:'12340',sessionDate:r.Date,decisionTimestamp:'2024-09-17T09:30:00+09:00',decisionPrice:100};
 const p=project(e,a.maps.get('12340'));test(()=>assert.equal(p.future.length,60));test(()=>assert.equal(p.prefix.length,5));
 test(()=>assert.equal(p.future[0].availableOffset,1));test(()=>assert.equal(p.future[0].start,'2024-09-17T09:30:00+09:00'));
 test(()=>assert.equal(p.future[1].missing,true));test(()=>assert.ok(Math.abs(p.future[0].c-1)<1e-10));
 test(()=>assert.equal(project({...e,decisionTimestamp:'2024-09-17T11:29:00+09:00'},new Map()).future[1].boundary,true));
 test(()=>assert.ok(Object.values(SAFETY).every(v=>v===false)));
 console.log(JSON.stringify({syntheticTests:n,passed:n,fit:0,providerRequests:0,safety:SAFETY}));
}
async function main(cacheRoot,outDir){
 if(!cacheRoot||!outDir||fs.existsSync(outDir))throw Error('NEW_OUTPUT_REQUIRED');
 for(const [file,h]of Object.entries(PINS))assert.equal(sha(fs.readFileSync(file)),h,`SOURCE_SHA:${file}`);
 const {normalizeAndAggregateMinuteRows}=await import('../predict/long-only/phase57-long-only-integrated-dataset.js');
 const rows=gunzipSync(fs.readFileSync(EV)).toString().trim().split('\n').map(JSON.parse);
 const lineage=JSON.parse(gunzipSync(fs.readFileSync(PATHS)));
 assert.equal(rows.length,3800);assert.equal(new Set(rows.map(r=>r.selectorEventId)).size,3800);
 const first=new Map();for(const e of rows.sort((a,b)=>Date.parse(a.decisionTimestamp)-Date.parse(b.decisionTimestamp)||a.symbol.localeCompare(b.symbol)))if(!first.has(e.symbolSessionId))first.set(e.symbolSessionId,e);
 assert.equal(first.size,2743);const dates=[...new Set(rows.map(r=>r.sessionDate))].sort();assert.equal(dates.length,76);
 const output=[],sources=[];
 for(const date of dates){
  const events=[...first.values()].filter(e=>e.sessionDate===date),symbols=new Set(events.map(e=>e.symbol));
  const file=path.join(cacheRoot,'phase57-long-only/raw/jquants-v2',date,'minute-pages.json'),bytes=fs.readFileSync(file);
  const saved=lineage.sources.find(s=>s.sessionDate===date);assert.ok(saved?.partition.startsWith('DEVELOPMENT_'));
  assert.equal(sha(bytes),saved.rawPagesSHA,'RAW_PAGES_SHA');
  const pages=JSON.parse(bytes);for(const p of pages)assert.equal(sha(p.responseText),p.responseSha256,'RAW_PAGE_SHA');
  const raw=pages.flatMap(p=>JSON.parse(p.responseText).data??[]);assert.ok(raw.every(r=>(r.Date??r.date)===date));
  const normalized=normalizeAndAggregateMinuteRows(raw);assert.equal(sha(JSON.stringify(normalized.bars)),saved.normalizedSHA,'NORMALIZED_PARITY');
  const indexed=indexMinutes(raw,date,symbols);for(const e of events)output.push(project(e,indexed.maps.get(e.symbol)));
  sources.push({sessionDate:date,partition:saved.partition,rawPagesSHA:saved.rawPagesSHA,normalizedSHA:saved.normalizedSHA,...indexed.audit,anchors:events.length});
  console.log(JSON.stringify({sessionDate:date,anchors:events.length,status:'EXISTING_CACHE_PROJECTED',providerRequests:0}));
 }
 assert.equal(output.length,2743);assert.equal(new Set(output.map(r=>r.eventId)).size,2743);
 fs.mkdirSync(outDir,{recursive:true});const bytes=gzipSync(Buffer.from(JSON.stringify(output)+'\n'));
 fs.writeFileSync(path.join(outDir,'minute-paths.json.gz'),bytes,{flag:'wx'});
 const audit={id:'NEW_LONG_ENTRY_MINUTE_RESOLUTION_EXPORT_V1',sourceHead:'7599df41199a8c4d1ea86d5f3cb595edd599dd21',role:'EVALUATOR_PATHS_RELEASE_CAUSALLY_NOT_T0_FEATURES',
  sourcePins:PINS,sources,anchors:2743,events:3800,sessions:76,minutePathSHA:sha(bytes),fields:'relative OHLC only; no volume/turnover imputation; first5m prefix and forward60m',
  timeline:'BAR_START_JST; reconstructed availability=start+1m, not measured arrival. No missing-minute fill, auction exclusion, exact next-minute OPEN reference only.',
  limitations:['Exposed Development and frozen Selector training exposure','Source candidate membership conditioned on future-label availability','Reference prices are not verified executable fills','No assumption that absent minute equals no trade'],
  newFit:0,newModelPredictions:0,newTradingDecisions:0,priceProviderRequests:0,freshAccess:0,oosAccess:0,safety:SAFETY};
 fs.writeFileSync(path.join(outDir,'audit.json'),JSON.stringify(audit,null,2)+'\n',{flag:'wx'});
 console.log(JSON.stringify({status:'MINUTE_RESOLUTION_EXPORT_COMPLETE',anchors:2743,sha256:sha(bytes),providerRequests:0}));
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){if(process.argv[2]==='--self-test')selfTest();else await main(process.argv[2],process.argv[3]);}
