import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {isDeepStrictEqual} from 'node:util';
import {buildDirectionFeatures} from './phase57-minimal-stateful-entry.mjs';
import {score,replayFirstEnter} from '../phase57-capital-allocation-v3-phase-a.mjs';
import {PHASE_B_SAFETY} from './phase57-capital-allocation-v3-phase-b.mjs';

export const digest=x=>createHash('sha256').update(x).digest('hex');
export const hash=x=>digest(JSON.stringify(x));
export const FREEZE='f0ea365e5cf73b3394779ae1be3ea99e268f9d6cede8160a703ed24cab5c0a14';
export const MODEL='f05def20081e51dfe7391c7e80e8b8474e5c140c42a47dc29dcd94bca367ab8a';
export const SAFETY=PHASE_B_SAFETY;
export const CAUSES=['DATA_SOURCE_DIFFERENCE','TIMESTAMP_NORMALIZATION_DIFFERENCE','BAR_FINALIZATION_DIFFERENCE','MISSING_RSS_DATA','RSS_STALE_DATA','EXCEL_CAPTURE_FAILURE','SYMBOL_MAPPING_DIFFERENCE','LOGIC_IMPLEMENTATION_DIFFERENCE','ROUNDING_OR_LOT_DIFFERENCE','LEDGER_IMPLEMENTATION_DIFFERENCE','REFERENCE_RECONSTRUCTION_LIMITATION','UNKNOWN_REQUIRES_REVIEW'];
export function instant(s){assert.ok(typeof s==='string'&&/(Z|[+-]\d\d:\d\d)$/.test(s)&&Number.isFinite(Date.parse(s)),'EXPLICIT_TIMESTAMP_REQUIRED');return Date.parse(s);}
export const iso=t=>new Date(t).toISOString();
export const jstDate=t=>iso(instant(t)+32400000).slice(0,10);
export function exposedDate(date){assert.ok(/^2026-\d\d-\d\d$/.test(date)&&date>='2026-06-18'&&date<='2026-09-09','RESERVED_OR_UNAPPROVED_SESSION_LOCKED');return date;}
export function verifyFreeze(root){assert.equal(digest(fs.readFileSync(path.join(root,'predict/research/phase57-capital-allocation-integrated-candidate-freeze.json'))),FREEZE,'FREEZE_MISMATCH');}
export function symbolId(s){assert.ok(typeof s==='string'&&/^[0-9A-Z]{4}(\.T)?$/.test(s),'SYMBOL_MAPPING_DIFFERENCE');return s.endsWith('.T')?s:s+'.T';}

// Pure mapping, preserving the stable-slot behavior of phase58_excel_dynamic_slot_capture.
// An epoch changes on every reassignment; old generation reads cannot become new-symbol bars.
export class SymbolSlots{
  constructor(count){assert.ok(Number.isInteger(count)&&count>0);this.slots=Array.from({length:count},()=>({symbol:null,generation:0}));}
  assign(symbols){const wanted=symbols.map(symbolId);assert.equal(new Set(wanted).size,wanted.length,'DUPLICATE_SYMBOL');assert.ok(wanted.length<=this.slots.length,'CAPACITY_EXCEEDED_SELECTOR_UNIVERSE_UNCHANGED');const next=structuredClone(this.slots);for(const s of next)if(s.symbol&&!wanted.includes(s.symbol)){s.symbol=null;s.generation++;}for(const symbol of wanted)if(!next.some(s=>s.symbol===symbol)){const s=next.find(s=>s.symbol===null);s.symbol=symbol;s.generation++;}this.slots=next;return structuredClone(next);}
  verify(slot,symbol,generation){const s=this.slots[slot];assert.ok(s&&s.symbol===symbolId(symbol)&&s.generation===generation,'SYMBOL_MAPPING_DIFFERENCE');}
}

export function normalizeBar(raw,{label,decisionTimestamp,fixture=true}){
  assert.equal(fixture,true,'REAL_CAPTURE_LOCKED');
  assert.ok(['START','END'].includes(label),'TIMESTAMP_SEMANTICS_UNVERIFIED');
  assert.ok(/^\d{4}-\d\d-\d\d$/.test(raw.sourceDate)&&/^\d\d:\d\d(:00)?$/.test(raw.sourceTime),'SOURCE_TIMESTAMP_INVALID');
  exposedDate(raw.sourceDate);
  const source=instant(`${raw.sourceDate}T${raw.sourceTime.length===5?raw.sourceTime+':00':raw.sourceTime}+09:00`);
  const start=source-(label==='END'?300000:0),end=start+300000,captured=instant(raw.captureAt),available=instant(raw.availableAt),decision=instant(decisionTimestamp);
  const local=iso(start+32400000),minute=Number(local.slice(11,13))*60+Number(local.slice(14,16));
  assert.ok(local.slice(0,10)===raw.sourceDate&&start%300000===0&&((minute>=540&&minute<690)||(minute>=750&&minute<930)),'INVALID_SESSION_GRID');
  assert.ok(raw.finalized===true&&available>=end&&captured>=available&&captured<=decision,'BAR_FINALIZATION_DIFFERENCE');
  const x={};for(const k of ['open','high','low','close','volume']){assert.ok(typeof raw[k]==='number'&&Number.isFinite(raw[k]),'MALFORMED_NUMERIC_CELL');x[k]=raw[k];}
  assert.ok(Math.min(x.open,x.low,x.close)>0&&x.high>=Math.max(x.open,x.low,x.close)&&x.low<=Math.min(x.open,x.close)&&x.volume>=0,'INVALID_OHLCV');
  return {symbol:symbolId(raw.symbol),sourceDate:raw.sourceDate,sourceTime:raw.sourceTime,sourceLabel:label,sourceAvailableAt:iso(available),captureAt:iso(captured),observedAt:iso(captured),availableAt:iso(Math.max(captured,available)),barStart:iso(start),barEnd:iso(end),timestamp:iso(start),finalized:true,...x};
}

export class CausalBars{
  constructor(){this.rows=new Map();}
  add(row){const key=row.symbol+'|'+row.barStart,prior=this.rows.get(key);if(prior){assert.equal(hash(['open','high','low','close','volume'].map(k=>prior[k])),hash(['open','high','low','close','volume'].map(k=>row[k])),'CONFLICTING_DUPLICATE_BAR');return false;}this.rows.set(key,structuredClone(row));return true;}
  prefix(symbol,t){return [...this.rows.values()].filter(x=>x.symbol===symbol&&jstDate(x.timestamp)===jstDate(t)&&instant(x.availableAt)<=instant(t)).sort((a,b)=>instant(a.timestamp)-instant(b.timestamp)).map(({timestamp,availableAt,open,high,low,close,volume})=>({timestamp,availableAt,open,high,low,close,volume}));}
}

// Selection lineage remains an explicit reference input; no claim of independent Selector parity.
export function reconstructEntryEvent(event,bars){
  exposedDate(event.sessionDate);const t=instant(event.decisionTimestamp);
  const prefix=bars.filter(x=>instant(x.availableAt)<=t&&instant(x.timestamp)+300000<=t);
  const pair=[1,-1].map(direction=>buildDirectionFeatures({symbol:event.symbol,decisionTimestamp:event.decisionTimestamp,bars:prefix,rank:event.hybridRank,score:event.hybridScore,priceReference:prefix.at(-1)?.close,firstSelectionTimestamp:event.firstSelectionTimestamp,priorSelectionCount:event.priorSelectionCount,direction}));
  return {...event,priceReference:prefix.at(-1).close,directionFeatures:pair,featureStatus:'READY'};
}
export class OfflineEntry{
  constructor(modelBytes){assert.equal(digest(modelBytes),MODEL,'MODEL_HASH_MISMATCH');this.model=JSON.parse(modelBytes);this.entered=new Set();this.last=-Infinity;}
  decide(event,bars){const t=instant(event.decisionTimestamp);assert.ok(t>=this.last,'ENTRY_OUT_OF_ORDER');this.last=t;const e=reconstructEntryEvent(event,bars);const pair=e.directionFeatures.map(x=>({direction:x.direction,probability:score(x,this.model)}));const selected=[...pair].sort((a,b)=>b.probability-a.probability);let opportunity=null;
    if(!this.entered.has(e.symbolSessionId)){const stream=new Map([[e.sessionDate,new Map([[e.symbol,bars.filter(x=>instant(x.availableAt)<=t)]])]]);opportunity=replayFirstEnter([e],this.model,stream)[0]??null;if(opportunity)this.entered.add(e.symbolSessionId);}
    return {event:e,pair,chosenDirection:selected[0].probability===selected[1].probability?null:selected[0].direction,action:opportunity?'ENTER':'WATCH',opportunity};
  }
}

// Receives only the CURRENT frozen-v4 decision. It never accepts a full future v4 trade.
// The caller supplies already-authorized reference decisions for offline fixtures.
export class Bar5Manager{
  constructor({eventId,symbol,direction,entryPrice,entryTimestamp,usedPathIdentity=null}){assert.ok([-1,1].includes(direction)&&entryPrice>0);exposedDate(jstDate(entryTimestamp));if(usedPathIdentity!==null)assert.ok(['4dd18c66586706aebc19775c718d0fca2fb1ac569d40e8746f85aae502a44a70','b28bf1931a2fc3332b0c83306523b0d0838d9776b3fc66cb8587b305170ac521'].includes(usedPathIdentity),'UNAPPROVED_SAVED_PATH');this.usedPathIdentity=usedPathIdentity;this.id=eventId;this.symbol=symbol;this.direction=direction;this.entryPrice=entryPrice;this.last=instant(entryTimestamp);this.n=0;this.state=null;this.closed=false;}
  step({timestamp,close,v4}){assert.ok(!this.closed&&instant(timestamp)>this.last,'EXIT_ORDER_OR_ALREADY_CLOSED');exposedDate(jstDate(timestamp));let expected=this.last+300000;if(iso(this.last+32400000).slice(11,16)==='11:30')expected=this.last+3900000;const gridGap=instant(timestamp)!==expected;if(!this.usedPathIdentity)assert.equal(gridGap,false,'MISSING_MANAGEMENT_BAR');assert.ok(Number.isFinite(close)&&close>0&&v4&&['HOLD','EXIT'].includes(v4.action),'CURRENT_V4_DECISION_REQUIRED');assert.equal(instant(v4.timestamp),instant(timestamp),'FUTURE_V4_FORBIDDEN');
    this.last=instant(timestamp);this.n++;const ret=this.direction*(close/this.entryPrice-1)*100;
    if(this.n===1)this.state=ret>=0?'FIRST_BAR_NON_ADVERSE_V4':'DEFENSIVE_PENDING';
    else if(this.state==='DEFENSIVE_PENDING'&&this.n<=5&&ret>=0)this.state='RECOVERED_TO_V4';
    let decision=null;
    if(this.state==='DEFENSIVE_PENDING'&&this.n===5){this.state='DEFENSIVE_EXIT_BAR_5';decision={exitPrice:close,exitReason:'DEFENSIVE_EXIT_BAR_5'};}
    else if(v4.action==='EXIT'){assert.ok(Number.isFinite(v4.exitPrice)&&v4.exitPrice>0&&typeof v4.exitReason==='string');if(this.state==='DEFENSIVE_PENDING')this.state='HORIZON_FALLBACK_V4';decision={exitPrice:v4.exitPrice,exitReason:v4.exitReason};}
    if(decision){this.closed=true;decision={eventId:this.id,...decision,exitTimestamp:iso(this.last),barsHeld:this.n,classification:this.state};}
    return {timestamp:iso(this.last),eventId:this.id,barsHeld:this.n,directionalReturnPct:ret,reclaim:ret>=0,state:this.state,v4:structuredClone(v4),decision,gridGap,savedPathOrdinalReplay:this.usedPathIdentity!==null};
  }
}

// One exclusive writer per session/version; a torn tail is preserved and fails closed.
export class EvidenceLog{
  constructor(file){this.file=file;this.lock=file+'.lock';fs.mkdirSync(path.dirname(file),{recursive:true});this.fd=fs.openSync(this.lock,'wx');this.last='0'.repeat(64);this.sequence=0;
    try{if(fs.existsSync(file)){const data=fs.readFileSync(file,'utf8');assert.ok(!data||data.endsWith('\n'),'TORN_EVIDENCE_TAIL');for(const line of data.trim().split('\n').filter(Boolean)){const row=JSON.parse(line),{sha256,...body}=row;assert.equal(body.sequence,this.sequence);assert.equal(body.previousSha256,this.last);assert.equal(hash(body),sha256,'EVIDENCE_HASH_MISMATCH');this.last=sha256;this.sequence++;}}}catch(e){this.close();throw e;}}
  append(kind,payload){assert.ok(this.fd!==null,'WRITER_CLOSED');const body={sequence:this.sequence,previousSha256:this.last,kind,payload};const row={...body,sha256:hash(body)};const fd=fs.openSync(this.file,'a');try{fs.writeFileSync(fd,JSON.stringify(row)+'\n');fs.fsyncSync(fd);}finally{fs.closeSync(fd);}this.last=row.sha256;this.sequence++;return row;}
  close(){if(this.fd!==null){fs.closeSync(this.fd);this.fd=null;fs.unlinkSync(this.lock);}}
}

export function compareRecords(realtime,reference,{stage,key='id',cause}={}){
  const map=rows=>{const m=new Map();for(const r of rows){assert.ok(r[key]!==undefined&&!m.has(r[key]),'DUPLICATE_OR_MISSING_COMPARISON_KEY');m.set(r[key],r);}return m;};const a=map(realtime),b=map(reference),ids=[...new Set([...a.keys(),...b.keys()])].sort(),mismatches=[];let exact=0;
  for(const id of ids){if(a.has(id)&&b.has(id)&&isDeepStrictEqual(a.get(id),b.get(id)))exact++;else{const primaryCause=cause??(!a.has(id)?'MISSING_RSS_DATA':!b.has(id)?'REFERENCE_RECONSTRUCTION_LIMITATION':stage==='LEDGER'?'LEDGER_IMPLEMENTATION_DIFFERENCE':'UNKNOWN_REQUIRES_REVIEW');assert.ok(CAUSES.includes(primaryCause));mismatches.push({stage,id,primaryCause,realtime:a.get(id)??null,reference:b.get(id)??null});}}
  return {stage,denominator:ids.length,exact,exactMatchRate:ids.length?exact/ids.length:null,mismatches};
}
export function cumulative(reports){const by={};for(const r of reports)for(const s of r.stages??[]){const x=by[s.stage]??={exact:0,denominator:0};x.exact+=s.exact;x.denominator+=s.denominator;}return Object.fromEntries(Object.entries(by).map(([k,v])=>[k,{...v,exactMatchRate:v.denominator?v.exact/v.denominator:null}]));}

export function captureHealth({now,msiiConnected,workbookHealthy,rssError,latestAvailableAt,lastPollAt,maxAgeMs=30000}){
  const t=instant(now),local=iso(t+32400000),minute=Number(local.slice(11,13))*60+Number(local.slice(14,16));
  const active=(minute>=540&&minute<=690)||(minute>=750&&minute<=930);
  const failures=[];
  if(!msiiConnected)failures.push('MSII_DISCONNECTED');if(!workbookHealthy)failures.push('EXCEL_CAPTURE_FAILURE');if(rssError)failures.push('RSS_CELL_ERROR');
  if(active&&(!lastPollAt||t-instant(lastPollAt)>maxAgeMs||instant(lastPollAt)>t))failures.push('POLL_GAP_OR_SLEEP');
  if(active&&(!latestAvailableAt||t-instant(latestAvailableAt)>330000||instant(latestAvailableAt)>t))failures.push('RSS_STALE_DATA');
  return {healthStatus:failures.length?'FAIL_CLOSED':active?'HEALTHY_FIXTURE':'SCHEDULED_IDLE',failures,requiredDataHealthy:failures.length===0,strategyDecisionAllowed:false,reason:'OFFLINE_ONLY_REAL_CAPTURE_LOCKED'};
}
