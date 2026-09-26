// Derived-feature export only. No model imports, fit, predictions or provider clients.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync,gzipSync} from 'node:zlib';
import {pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';
import {normalizeAndAggregateMinuteRows} from '../predict/long-only/phase57-long-only-integrated-dataset.js';
const sha=b=>createHash('sha256').update(b).digest('hex');
const rootPath='docs/evidence/phase57-msh-entry-long-v1-preimplementation-feasibility-events.ndjson.gz';
const pathsPath='docs/evidence/phase57-msh-entry-long-v2-development/paths.json.gz';
const normalizerPath='predict/long-only/phase57-long-only-integrated-dataset.js';
const pins={
 [rootPath]:'73e566aba4d1a3f5af33b74be52ae90736c088b1091841f1eb44e93d5476084c',
 [pathsPath]:'9b051b630c1e5ac59fac42f0da32830f38e07c48ded56a26e2dec4c054a4b7ba',
 [normalizerPath]:'390e2df4ddc0be571d285e05754ce9ad90f2618eb5902797cf8e7bae4a5f667f'
};
const parse=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const readGz=p=>JSON.parse(gunzipSync(fs.readFileSync(p)));
const minute=t=>{const m=String(t??'').match(/(\d{2}):(\d{2})/);return m?Number(m[1])*60+Number(m[2]):NaN;};
const numeric=(r,...keys)=>{for(const k of keys){const x=r?.[k];if(x===null||x===undefined||x===''||typeof x==='boolean')continue;const y=Number(x);if(Number.isFinite(y))return y;}return null;};
const key=(s,m)=>`${s}|${m}`;
function expectedStarts(t){
 const mins=minute(t),d=t.slice(0,10),end=d<'2024-11-05'?900:930;
 const all=[];for(let m=540;m<690;m+=5)if(m+5<=mins)all.push(m);
 for(let m=750;m<end;m+=5)if(m+5<=mins)all.push(m);
 return all;
}
function featuresAt(event,barByMinute,badTurnoverSlots){
 const expected=expectedStarts(event.decisionTimestamp),last=barByMinute.get(expected.at(-1));
 const six=expected.slice(-6).map(m=>barByMinute.get(m));
 const result={range6Pct:null,lastCloseLocation:null,lastUpperWickFraction:null,turnover6Jpy:null};
 const reasons={},quality={lastBarPresent:Boolean(last),sixBarsPresent:expected.length>=6&&six.length===6&&six.every(Boolean),observedMinutes6:null};
 if(last){
  assert.ok(Date.parse(last.availableAtJst)<=Date.parse(event.decisionTimestamp),'FUTURE_BAR');
  const r=last.high-last.low;
  if(r>0){result.lastCloseLocation=(last.close-last.low)/r;result.lastUpperWickFraction=(last.high-Math.max(last.open,last.close))/r;}
  else reasons.lastCloseLocation=reasons.lastUpperWickFraction='ZERO_RANGE';
 }else reasons.lastCloseLocation=reasons.lastUpperWickFraction='IMMEDIATE_PRECEDING_BAR_MISSING';
 if(quality.sixBarsPresent){
  for(const b of six)assert.ok(Date.parse(b.availableAtJst)<=Date.parse(event.decisionTimestamp),'FUTURE_BAR');
  result.range6Pct=100*(Math.max(...six.map(b=>b.high))-Math.min(...six.map(b=>b.low)))/six.at(-1).close;
  quality.observedMinutes6=six.reduce((a,b)=>a+b.observedMinutes,0);
  if(expected.slice(-6).some(m=>badTurnoverSlots.has(m)))reasons.turnover6Jpy='SOURCE_TURNOVER_MISSING_OR_INVALID';
  else result.turnover6Jpy=six.reduce((a,b)=>a+b.turnover,0);
 }else reasons.range6Pct=reasons.turnover6Jpy='SIX_COMPLETED_SCHEDULED_BARS_MISSING';
 return {values:result,reasons,quality};
}
function selfTest(){
 let count=0;const check=(f)=>{f();count++;};
 check(()=>assert.equal(numeric({Va:null},'Va'),null));
 check(()=>assert.equal(numeric({Va:0},'Va'),0));
 check(()=>assert.equal(numeric({Va:''},'Va'),null));
 check(()=>assert.deepEqual(expectedStarts('2024-09-17T09:30:00+09:00').slice(-6),[540,545,550,555,560,565]));
 check(()=>assert.deepEqual(expectedStarts('2024-09-17T13:00:00+09:00').slice(-6),[750,755,760,765,770,775]));
 check(()=>assert.equal(expectedStarts('2024-09-17T12:30:00+09:00').at(-1),685));
 const e={decisionTimestamp:'2024-09-17T09:30:00+09:00'};
 const b=new Map([540,545,550,555,560,565].map(m=>[m,{open:100,high:104,low:98,close:103,turnover:1000,observedMinutes:5,availableAtJst:`2024-09-17T09:${String(m+5-540).padStart(2,'0')}:00+09:00`}]));
 const f=featuresAt(e,b,new Set());
 check(()=>assert.equal(f.values.turnover6Jpy,6000));
 check(()=>assert.equal(f.values.lastCloseLocation,5/6));
 check(()=>assert.equal(f.values.lastUpperWickFraction,1/6));
 check(()=>assert.equal(featuresAt(e,b,new Set([550])).values.turnover6Jpy,null));
 b.set(570,{open:1,high:99999,low:1,close:1,turnover:1e12,availableAtJst:'2024-09-17T09:35:00+09:00'});
 check(()=>assert.deepEqual(featuresAt(e,b,new Set()),f));
 const missing=new Map(b);missing.delete(560);
 check(()=>assert.equal(featuresAt(e,missing,new Set()).values.range6Pct,null));
 const flat=new Map(b);flat.set(565,{...flat.get(565),open:100,high:100,low:100,close:100});
 check(()=>assert.equal(featuresAt(e,flat,new Set()).values.lastCloseLocation,null));
 const gap=new Map(b);gap.delete(565);
 check(()=>assert.equal(featuresAt(e,gap,new Set()).values.lastUpperWickFraction,null));
 console.log(JSON.stringify({syntheticTests:count,passed:count,modelFits:0,modelPredictions:0}));
}
function main(cacheRoot,outDir){
 if(!cacheRoot||!outDir||fs.existsSync(outDir))throw Error('NEW_OUTPUT_REQUIRED');
 for(const [f,h]of Object.entries(pins))assert.equal(sha(fs.readFileSync(f)),h,`SOURCE_SHA:${f}`);
 const rows=gunzipSync(fs.readFileSync(rootPath)).toString().trim().split('\n').map(JSON.parse);
 const lineage=readGz(pathsPath);const dates=[...new Set(rows.map(r=>r.sessionDate))].sort();
 assert.equal(rows.length,3800);assert.equal(new Set(rows.map(r=>r.selectorEventId)).size,3800);assert.equal(dates.length,76);
 const outputs=[],sourceAudit=[];
 for(const date of dates){
  const events=rows.filter(r=>r.sessionDate===date).sort((a,b)=>Date.parse(a.decisionTimestamp)-Date.parse(b.decisionTimestamp)||a.symbol.localeCompare(b.symbol));
  const symbols=new Set(events.map(r=>r.symbol));
  const dir=path.join(cacheRoot,'phase57-long-only/raw/jquants-v2',date);
  const file=path.join(dir,'minute-pages.json'),rawBytes=fs.readFileSync(file),saved=lineage.sources.find(s=>s.sessionDate===date);
  assert.ok(saved?.partition.startsWith('DEVELOPMENT_'));assert.equal(sha(rawBytes),saved.rawPagesSHA,'RAW_SHA');
  const pages=JSON.parse(rawBytes);for(const p of pages)assert.equal(sha(p.responseText),p.responseSha256,'PAGE_SHA');
  const raw=pages.flatMap(p=>JSON.parse(p.responseText).data??[]);
  assert.ok(raw.every(r=>(r.Date??r.date)===date),'DATE_SCOPE');
  const normalized=normalizeAndAggregateMinuteRows(raw);assert.equal(sha(JSON.stringify(normalized.bars)),saved.normalizedSHA,'NORMALIZED_SHA');
  const map=new Map(),bad=new Map();
  for(const s of symbols){map.set(s,new Map());bad.set(s,new Set());}
  for(const b of normalized.bars)if(symbols.has(b.symbol))map.get(b.symbol).set(minute(b.barStartJst),b);
  for(const r of raw){
   const s=String(r.Code??r.code??r.symbol??'').trim().toUpperCase();if(!symbols.has(s))continue;
   const m=minute(r.Time??r.time);if(!((m>=540&&m<690)||(m>=750&&m<930)))continue;
   const o=numeric(r,'O','Open','open'),h=numeric(r,'H','High','high'),l=numeric(r,'L','Low','low'),c=numeric(r,'C','Close','close');
   if(![o,h,l,c].every(x=>x!==null&&x>0)||h<Math.max(o,c)||l>Math.min(o,c))continue;
   const t=numeric(r,'Va','Turnover','turnover');if(t===null||t<0)bad.get(s).add(Math.floor(m/5)*5);
  }
  const previous=new Map();
  for(const e of events){
   const p=previous.get(e.symbol);if(p)assert.ok(Date.parse(p.decisionTimestamp)<Date.parse(e.decisionTimestamp),'NON_PRIOR_SELECTION');
   const f=featuresAt(e,map.get(e.symbol),bad.get(e.symbol));
   for(const name of ['relativeVolume5','directionalVwapDistancePct']){
    const x=e.features?.[name];f.values[name]=x?.status==='AVAILABLE'&&Number.isFinite(x.value)?x.value:null;
    if(f.values[name]===null)f.reasons[name]=x?.reason??x?.status??'MISSING';
   }
   f.values.priorSelectionCount=e.priorSelectionCount;
   f.values.ridgeDeltaPreviousSelection=p?e.ridgeScore-p.ridgeScore:null;
   if(!p)f.reasons.ridgeDeltaPreviousSelection='NO_PREVIOUS_SAME_SESSION_SELECTION';
   outputs.push({eventId:e.selectorEventId,sessionDate:date,symbol:e.symbol,decisionTimestamp:e.decisionTimestamp,...f});previous.set(e.symbol,e);
  }
  sourceAudit.push({...saved,rawRows:raw.length,normalizedBars:normalized.bars.length,candidateEvents:events.length});
  console.log(JSON.stringify({session:date,candidates:events.length,rawHashVerified:true,normalizedHashVerified:true,providerRequests:0}));
 }
 assert.equal(outputs.length,3800);fs.mkdirSync(outDir,{recursive:true});
 const data=gzipSync(Buffer.from(JSON.stringify(outputs)+'\n'));fs.writeFileSync(path.join(outDir,'feature-matrix.json.gz'),data,{flag:'wx'});
 const audit={id:'PHASE57_ENTRY_ADDITIONAL_INFORMATION_EXPORT_V1',sourceHead:'7599df41199a8c4d1ea86d5f3cb595edd599dd21',sourcePins:pins,sourceAudit,rows:outputs.length,featureSHA:sha(data),modelFit:0,modelPrediction:0,providerRequests:0,freshAccess:0,oosAccess:0,safety:lineage.safety};
 fs.writeFileSync(path.join(outDir,'export-audit.json'),JSON.stringify(audit,null,2)+'\n',{flag:'wx'});
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){if(process.argv[2]==='--self-test')selfTest();else main(process.argv[2],process.argv[3]);}
export {featuresAt,expectedStarts,numeric};
