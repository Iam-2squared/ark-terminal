import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {normalizeAndAggregateMinuteRows} from '../predict/long-only/phase57-long-only-integrated-dataset.js';
import {simulateFrozenRatchetExit,P23_8D_FROZEN_RATCHET_CONFIG} from '../predict/daytrade/phase57-frozen-ratchet-exit.js';
const sha=b=>createHash('sha256').update(b).digest('hex');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const minute=ts=>{const d=new Date(Date.parse(ts)+9*3600000).toISOString();return Number(d.slice(11,13))*60+Number(d.slice(14,16));};
const active=(m,end)=>m>=540&&m<end&&!(m>=690&&m<750);
const pct=(p,ref)=>100*(p/ref-1);
export function pathFor(bars,event,horizon){
 const start=Date.parse(event.decisionTimestamp),ref=event.decisionPrice,date=event.sessionDate,sm=minute(event.decisionTimestamp),end=date<'2024-11-05'?900:930;
 if(!Number.isFinite(start)||!(ref>0)||new Date(start+9*3600000).toISOString().slice(0,10)!==date)throw Error('INVALID_ENTRY_REFERENCE');
 const finish=horizon==='SESSION_END'?end:sm+horizon;
 const fail=reason=>({available:false,reason});
 if(!active(sm,end)||finish>end)return fail('SESSION_BOUNDARY');
 if(horizon!=='SESSION_END'&&sm<690&&finish>690)return fail('LUNCH_RECESS');
 const map=new Map();for(const b of bars){const t=Date.parse(b.barStartJst);if(map.has(t)||b.sessionDate!==date)throw Error('DUPLICATE_OR_CROSS_SESSION');map.set(t,b);}
 const selected=[];
 for(let m=sm;m<finish;m+=5){if(!active(m,end))continue;const t=start+(m-sm)*60000,b=map.get(t);if(!b)return fail('PROVIDER_GAP');
  if(Date.parse(b.availableAtJst)!==t+300000||![b.open,b.high,b.low,b.close].every(v=>Number.isFinite(v)&&v>0)||b.low>Math.min(b.open,b.close)||b.high<Math.max(b.open,b.close))throw Error('INVALID_BAR');selected.push(b);}
 if(!selected.length)return fail('NO_FUTURE_BARS');
 const hi=Math.max(...selected.map(b=>b.high)),lo=Math.min(...selected.map(b=>b.low));
 const mfe=Math.max(0,pct(hi,ref)),mae=Math.min(0,pct(lo,ref));
 const ih=selected.findIndex(b=>b.high===hi),il=selected.findIndex(b=>b.low===lo);
 const when=i=>(Date.parse(selected[i].availableAtJst)-start)/60000;
 const firstHit=level=>{const i=selected.findIndex(b=>level>0?pct(b.high,ref)>=level:pct(b.low,ref)<=level);return i<0?null:when(i);};
 const result={available:true,barCount:selected.length,sparseMinuteBars:selected.filter(b=>b.observedMinutes<5).length,mfePct:mfe,maePct:mae,returnPct:pct(selected.at(-1).close,ref),timeToMfeMinutes:mfe>0?when(ih):null,timeToMaeMinutes:mae<0?when(il):null,ordering:mfe<=0||mae>=0?'NO_TWO_SIDED_EXCURSION':ih===il?'UNKNOWN_INTRABAR_ORDER':ih<il?'MFE_FIRST':'MAE_FIRST',firstPlus1Minutes:firstHit(1),firstMinus1Minutes:firstHit(-1),adverse:{}};
 for(const level of [-1,-2,-3,-5,-10]){const index=selected.findIndex(b=>pct(b.low,ref)<=level);if(index<0)continue;const later=selected.slice(index+1);result.adverse[level]={firstHitMinutes:when(index),laterMfePct:later.length?Math.max(0,pct(Math.max(...later.map(b=>b.high)),ref)):null,laterHighReturnPct:later.length?pct(Math.max(...later.map(b=>b.high)),ref):null,horizonCloseReturnPct:result.returnPct};}
 const downIndex=selected.findIndex(b=>pct(b.low,ref)<=-1);
 result.plus1AfterFirstMinus1=downIndex>=0&&selected.slice(downIndex+1).some(b=>pct(b.high,ref)>=1);
 return result;
}
export function pathType(p){
 if(!p.available)return 'G_UNKNOWN';
 const up=p.firstPlus1Minutes,down=p.firstMinus1Minutes;
 if(up!==null&&up===down)return 'G_UNKNOWN';
 if(down!==null&&down<=15&&p.plus1AfterFirstMinus1)return 'A_EARLY_ADVERSE_THEN_RECOVERY';
 if(down!==null&&down<=15&&!p.plus1AfterFirstMinus1&&p.returnPct<=-1)return 'B_EARLY_FAILURE';
 if(p.mfePct>=1&&p.returnPct<=0)return 'D_WINNER_THEN_GIVEBACK';
 if(up!==null&&up<=30&&p.returnPct>0)return 'C_FAST_WINNER';
 if(up!==null&&up>30&&p.returnPct>0)return 'E_SLOW_WINNER';
 return 'F_CHOP_NO_EDGE';
}
export function replay(bars,event,full){
 if(event.direction!=='LONG')throw Error('LONG_ONLY');
 if(!full.available)return {eligible:false,reason:'INCOMPLETE_SESSION_PATH'};
 const start=Date.parse(event.decisionTimestamp),sm=minute(event.decisionTimestamp),end=event.sessionDate<'2024-11-05'?900:930;
 const byStart=new Map(bars.map(b=>[Date.parse(b.barStartJst),b])),context=[],future=[];
 for(let m=540;m<end;m+=5){if(!active(m,end))continue;const b=byStart.get(start+(m-sm)*60000);if(m<sm){if(!b)return {eligible:false,reason:'INCOMPLETE_PIT_CONTEXT'};context.push(b);}else future.push(b);}
 if(!context.length)return {eligible:false,reason:'NO_PIT_CONTEXT'};
 const adapt=b=>({timestamp:b.availableAtJst,open:b.open,high:b.high,low:b.low,close:b.close,volume:b.volume});
 if(context.some(b=>Date.parse(b.availableAtJst)>start)||future.some(b=>!b||Date.parse(b.barStartJst)<start))throw Error('PIT_VIOLATION');
 const result=simulateFrozenRatchetExit({entryPrice:event.decisionPrice,signalDirection:'LONG',sessionDate:event.sessionDate,frozenEntry:true,contextBars:context.map(adapt),futureBars:future.map(adapt)});
 if(!result||result.direction!=='LONG'||!result.ratchetNeverLoosened||result.futureBarsUsedBeforeDecision||result.futureExtremaUsedForDecision)throw Error('EXIT_INTEGRITY');
 const held=future.slice(0,result.barsHeld),last=held.at(-1),closeMinutes=(Date.parse(result.outcomeAt)-start)/60000;
 return {eligible:true,exitReason:result.exitReason,exitPrice:result.exitPrice,outcomeAt:result.outcomeAt,barsHeld:result.barsHeld,holdingMinutesUpper:closeMinutes,holdingMinutesLower:result.intrabarExit?closeMinutes-5:closeMinutes,intrabarExit:result.intrabarExit,grossReturnPct:result.grossReturnPct,netReturnPct:result.netReturnPct,positive:result.netReturnPct>0,availableSessionMfePct:full.mfePct,availableMfeCaptureRatio:full.mfePct>0?result.grossReturnPct/full.mfePct:null,netAvailableMfeCaptureRatio:full.mfePct>0?result.netReturnPct/full.mfePct:null,maeBeforeExitUpperPct:result.maePct,maeBeforeExitLowerPct:result.intrabarExit?Math.min(result.maePct,pct(last.low,event.decisionPrice)):result.maePct,maeBeforeExitExact:!result.intrabarExit,sessionEndExposure:result.barsHeld===future.length,sessionEndNetReferencePct:full.returnPct-P23_8D_FROZEN_RATCHET_CONFIG.roundTripCostPct,ratchetActivated:result.ratchetActivated,contextBars:context.length,sparseContextBars:context.filter(b=>b.observedMinutes<5).length,ratchetNeverLoosened:result.ratchetNeverLoosened};
}
export function main(cacheRoot,output){
 if(!cacheRoot||!output||fs.existsSync(output))throw Error('EXPLICIT_NEW_OUTPUT_REQUIRED');
 const base='docs/evidence/phase57-long-exit-architecture-diagnostic',contract=read(`${base}/diagnostic-contract.json`),identityFile=`${base}/frozen-enter-identities.json`,entries=read(identityFile);
 if(sha(fs.readFileSync(identityFile))!==contract.entryIdentitySHA||entries.length!==277||new Set(entries.map(e=>e.symbolSessionId)).size!==277)throw Error('ENTRY_EVENT_IDENTITY_MISMATCH');
 if(sha(fs.readFileSync(`${base}/entry-upstream-freeze.json`))!==contract.upstreamFreezeSHA)throw Error('UPSTREAM_SHA_MISMATCH');
 for(const [p,h] of Object.entries(contract.sourcePins))if(sha(fs.readFileSync(p))!==h)throw Error(`SOURCE_SHA_MISMATCH:${p}`);
 const alloc=read('predict/long-only/phase57-long-only-session-allocation-v3.json'),l1=read('predict/long-only/phase57-long-only-l1-discovery-sessions.json'),l2=read('predict/long-only/phase57-long-only-l2-development-sessions.json'),v2=read('predict/long-only/phase57-long-only-v2-development-sessions.json');
 const groups=[{sessions:l1.sessions,manifest:'l1-minute-manifest.json',hash:l1.sessionListSha256},{sessions:v2.sessions,manifest:'v2-minute-manifest.json',hash:v2.sessionListSha256},{sessions:[...alloc.partitions.DEVELOPMENT_C,...alloc.partitions.DEVELOPMENT_D],manifest:'l2-minute-manifest.json',hash:l2.sessionListSha256}];
 const sources=[],events=[];
 for(const date of contract.sessionList){
  const group=groups.filter(g=>g.sessions.includes(date)),parts=Object.entries(alloc.partitions).filter(([,ds])=>ds.includes(date));
  if(group.length!==1||parts.length!==1||!parts[0][0].startsWith('DEVELOPMENT_'))throw Error('SEALED_OR_AMBIGUOUS_SCOPE');
  const dir=path.join(cacheRoot,'phase57-long-only/raw/jquants-v2',date),m=read(path.join(dir,group[0].manifest)),file=path.join(dir,'minute-pages.json'),pages=read(file);
  if(m.sessionDate!==date||m.partition!==parts[0][0]||m.sessionListSha256!==group[0].hash||m.pageCount!==pages.length)throw Error('MANIFEST_MISMATCH');
  for(const p of pages)if(sha(p.responseText)!==p.responseSha256)throw Error('PAGE_SHA_MISMATCH');
  const raw=pages.flatMap(p=>JSON.parse(p.responseText).data??[]);if(raw.length!==m.rowCount||raw.some(r=>(r.Date??r.date)!==date))throw Error('UNAUTHORIZED_OR_CORRUPT_DATA');
  const normalized=normalizeAndAggregateMinuteRows(raw),bySymbol=new Map();for(const b of normalized.bars){if(!bySymbol.has(b.symbol))bySymbol.set(b.symbol,[]);bySymbol.get(b.symbol).push(b);}
  for(const e of entries.filter(e=>e.sessionDate===date)){
   const bars=bySymbol.get(e.symbol)??[],horizons=Object.fromEntries([...contract.horizonsMinutes,'SESSION_END'].map(h=>[h,pathFor(bars,e,h)]));
   events.push({...e,direction:'LONG',horizons,pathType:pathType(horizons.SESSION_END),replay:replay(bars,{...e,direction:'LONG'},horizons.SESSION_END)});
  }
  sources.push({sessionDate:date,partition:m.partition,rawPagesSHA:sha(fs.readFileSync(file)),normalizedSHA:sha(JSON.stringify(normalized.bars)),audit:normalized.audit});
  console.log(JSON.stringify({sessionDate:date,status:'SAVED_DEVELOPMENT_DIAGNOSTIC_COMPLETE',providerRequests:0}));
 }
 if(events.length!==277||events.some(e=>!entries.some(x=>x.selectorEventId===e.selectorEventId)))throw Error('ENTRY_EVENT_IDENTITY_MISMATCH');
 const result={contractSHA:sha(fs.readFileSync(`${base}/diagnostic-contract.json`)),entryIdentitySHA:contract.entryIdentitySHA,exposure:'DIRECT_ENTRY_DEVELOPMENT_IN_SAMPLE',sources,events,unchangedRatchetConfig:P23_8D_FROZEN_RATCHET_CONFIG,counts:{providerRequests:0,entryPredictions:0,entryChanges:0,selectorChanges:0,exitTuning:0,freshAccess:0,oosAccess:0,shortEvaluation:0,forwardFill:0,interpolation:0,futureSubstitution:0,pitViolations:0},safety:contract.safety};
 fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(result)+'\n',{flag:'wx'});fs.writeFileSync(`${output}.sha256`,sha(fs.readFileSync(output))+'\n',{flag:'wx'});
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href)main(process.argv[2],process.argv[3]);
