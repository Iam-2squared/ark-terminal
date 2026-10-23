import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {normalizeAndAggregateMinuteRows} from '../predict/long-only/phase57-long-only-integrated-dataset.js';
const sha=b=>createHash('sha256').update(b).digest('hex');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const hm=t=>new Date(Date.parse(t)+32400000).toISOString().slice(11,16);
const minutes=t=>Number(hm(t).slice(0,2))*60+Number(hm(t).slice(3,5));
const regular=(m,end)=>m>=540&&m<end&&!(m>=690&&m<750);
export function projectPath(bars,e){
  const start=Date.parse(e.decisionTimestamp),date=e.sessionDate,ref=e.decisionPrice,end=date<'2024-11-05'?900:930,sm=minutes(e.decisionTimestamp);
  if(!Number.isFinite(start)||!(ref>0)||new Date(start+32400000).toISOString().slice(0,10)!==date)throw Error('ENTRY_REFERENCE_INVALID');
  const map=new Map();
  for(const b of bars){const t=Date.parse(b.barStartJst);if(map.has(t)||b.sessionDate!==date)throw Error('BAR_IDENTITY_FAILED');map.set(t,b);}
  const expected=[];for(let m=sm;m<end;m+=5)if(regular(m,end))expected.push(start+(m-sm)*60000);
  const future=expected.map((t,i)=>{
    const b=map.get(t);if(!b)return {slot:i+1,start:new Date(t).toISOString(),end:new Date(t+300000).toISOString(),minutes:(t+300000-start)/60000,missing:true};
    if(Date.parse(b.availableAtJst)!==t+300000||![b.open,b.high,b.low,b.close].every(v=>Number.isFinite(v)&&v>0)||b.high<Math.max(b.open,b.close)||b.low>Math.min(b.open,b.close))throw Error('INVALID_COMPLETED_BAR');
    return {slot:i+1,start:b.barStartJst,end:b.availableAtJst,minutes:(t+300000-start)/60000,missing:false,o:100*(b.open/ref-1),h:100*(b.high/ref-1),l:100*(b.low/ref-1),c:100*(b.close/ref-1),observedMinutes:b.observedMinutes};
  });
  return {...e,direction:'LONG',sessionEndMinute:end,entryMinute:sm,expectedBars:expected.length,future};
}
export function summarizePath(rows){
  if(!rows.length)return {available:false,reason:'NO_REMAINING_REGULAR_BAR'};
  if(rows.some(b=>b.missing))return {available:false,reason:'PROVIDER_GAP'};
  const hi=Math.max(...rows.map(b=>b.h)),lo=Math.min(...rows.map(b=>b.l)),mfe=Math.max(0,hi),mae=Math.min(0,lo),ih=rows.findIndex(b=>b.h===hi),il=rows.findIndex(b=>b.l===lo);
  return {available:true,barCount:rows.length,mfePct:mfe,maePct:mae,returnPct:rows.at(-1).c,timeToMfeMinutes:mfe>0?rows[ih].minutes:null,timeToMaeMinutes:mae<0?rows[il].minutes:null,ordering:mfe<=0||mae>=0?'NO_TWO_SIDED_EXCURSION':ih===il?'UNKNOWN_INTRABAR_ORDER':ih<il?'MFE_FIRST':'MAE_FIRST',sparseMinuteBars:rows.filter(b=>b.observedMinutes<5).length};
}
export function horizons(e){
  const out={};
  for(const h of [5,10,15,30]){
    if(e.entryMinute+h>e.sessionEndMinute)out[h]={available:false,reason:'SESSION_END'};
    else if(e.entryMinute>=690&&e.entryMinute<750||e.entryMinute<690&&e.entryMinute+h>690)out[h]={available:false,reason:'LUNCH_BREAK'};
    else out[h]=summarizePath(e.future.filter(b=>b.minutes<=h));
  }
  out.SESSION_END=summarizePath(e.future);out.FIXED_12=summarizePath(e.future.slice(0,12));return out;
}
export function main(cacheRoot,output){
  if(!cacheRoot||!output||fs.existsSync(output))throw Error('EXPLICIT_NEW_OUTPUT_REQUIRED');
  const base='docs/evidence/phase57-long-exit-v345-paired',c=read(`${base}/contract.json`),ledger='docs/evidence/phase57-msh-entry-long-v1-upstream-freeze/historical-enter-identities.json',entries=read(ledger);
  if(sha(fs.readFileSync(ledger))!==c.enterIdentitySHA||entries.length!==277||new Set(entries.map(e=>e.symbolSessionId)).size!==277)throw Error('ENTRY_EVENT_IDENTITY_MISMATCH');
  for(const [p,h] of Object.entries(c.sourcePins))if(sha(fs.readFileSync(p))!==h)throw Error(`SOURCE_SHA_MISMATCH:${p}`);
  const alloc=read('predict/long-only/phase57-long-only-session-allocation-v3.json'),l1=read('predict/long-only/phase57-long-only-l1-discovery-sessions.json'),l2=read('predict/long-only/phase57-long-only-l2-development-sessions.json'),v2=read('predict/long-only/phase57-long-only-v2-development-sessions.json');
  const groups=[{sessions:l1.sessions,manifest:'l1-minute-manifest.json',hash:l1.sessionListSha256},{sessions:v2.sessions,manifest:'v2-minute-manifest.json',hash:v2.sessionListSha256},{sessions:[...alloc.partitions.DEVELOPMENT_C,...alloc.partitions.DEVELOPMENT_D],manifest:'l2-minute-manifest.json',hash:l2.sessionListSha256}];
  const events=[],sources=[];
  for(const date of c.sessionList){
    const gs=groups.filter(g=>g.sessions.includes(date)),parts=Object.entries(alloc.partitions).filter(([,ds])=>ds.includes(date));
    if(gs.length!==1||parts.length!==1||!parts[0][0].startsWith('DEVELOPMENT_'))throw Error('SEALED_OR_AMBIGUOUS_SCOPE');
    const dir=path.join(cacheRoot,'phase57-long-only/raw/jquants-v2',date),m=read(path.join(dir,gs[0].manifest)),file=path.join(dir,'minute-pages.json'),pages=read(file);
    if(m.sessionDate!==date||m.partition!==parts[0][0]||m.sessionListSha256!==gs[0].hash||m.pageCount!==pages.length)throw Error('SOURCE_MANIFEST_MISMATCH');
    for(const p of pages)if(sha(p.responseText)!==p.responseSha256)throw Error('RAW_PAGE_SHA_MISMATCH');
    const raw=pages.flatMap(p=>JSON.parse(p.responseText).data??[]);if(raw.length!==m.rowCount||raw.some(r=>(r.Date??r.date)!==date))throw Error('UNAUTHORIZED_SESSION');
    const n=normalizeAndAggregateMinuteRows(raw),map=new Map();for(const b of n.bars){if(!map.has(b.symbol))map.set(b.symbol,[]);map.get(b.symbol).push(b);}
    for(const e of entries.filter(x=>x.sessionDate===date)){const p=projectPath(map.get(e.symbol)??[],e);events.push({...p,horizons:horizons(p),v3:null,v4:null,v5:null,pairedFiveArmEligible:false,blockedReason:'PINNED_ANALOG_WINDOW_AFTER_ENTRY'});}
    sources.push({sessionDate:date,partition:m.partition,rawPagesSHA:sha(fs.readFileSync(file)),normalizedSHA:sha(JSON.stringify(n.bars)),audit:n.audit});
    console.log(JSON.stringify({sessionDate:date,status:'FIXED_ENTRY_PATH_RECOVERED',providerRequests:0}));
  }
  if(events.length!==277)throw Error('ENTRY_COUNT_MISMATCH');
  const result={contractSHA:sha(fs.readFileSync(`${base}/contract.json`)),enterIdentitySHA:c.enterIdentitySHA,role:c.role,sources,events,counts:{entryPredictions:0,modelFit:0,scalerFit:0,exitFit:0,exitSweep:0,v3Replay:0,v4Replay:0,v5Replay:0,completeFiveArmPairs:0,providerRequests:0,freshAccess:0,oosAccess:0,shortEvaluation:0,forwardFill:0,interpolation:0,futureSubstitution:0,priorExitResultAccess:0},safety:c.safety};
  fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(result)+'\n',{flag:'wx'});fs.writeFileSync(`${output}.sha256`,sha(fs.readFileSync(output))+'\n',{flag:'wx'});
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href)main(process.argv[2],process.argv[3]);
