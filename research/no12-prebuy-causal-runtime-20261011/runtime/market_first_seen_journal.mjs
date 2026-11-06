/**
 * Local-only, append-only first-observed MARKET bar evidence; never order authority.
 * Five-day backfill remains historical reconstruction, not live observation.
 */
import fs from 'node:fs';
import path from 'node:path';
import {createHash,randomUUID} from 'node:crypto';
import {verifyNo12ObservedChart} from '../tools/no12_private_chart_publish.mjs';
export const FIRST_SEEN_SCHEMA='ARK_NO12_LOCAL_FIRST_SEEN_5M_V1';
const fail=s=>{throw Error(s)};
const sha=v=>createHash('sha256').update(v).digest('hex');
const jst=t=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tokyo',
 year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(t)).replace(/\//g,'-');
function millis(x,label){
 if(typeof x!=='string'||!/(Z|[+-]\d{2}:\d{2})$/.test(x)||!Number.isFinite(Date.parse(x)))fail(label);
 return Date.parse(x);
}
function rootOf(p){
 if(typeof p!=='string'||!path.isAbsolute(p))fail('FIRST_SEEN_ABSOLUTE_ROOT_REQUIRED');
 const s=fs.lstatSync(p);
 if(!s.isDirectory()||s.isSymbolicLink())fail('FIRST_SEEN_UNSAFE_ROOT');
 return path.resolve(p);
}
function readFile(file){
 const st=fs.lstatSync(file);
 if(!st.isFile()||st.isSymbolicLink())fail('FIRST_SEEN_UNSAFE_FILE');
 return fs.readFileSync(file);
}
function atomic(file,obj){
 const temp=file+'.tmp-'+process.pid+'-'+randomUUID();let fd;
 try{
  fd=fs.openSync(temp,'wx',0o600);
  fs.writeFileSync(fd,JSON.stringify(obj)+'\n');fs.fsyncSync(fd);
  fs.closeSync(fd);fd=undefined;fs.renameSync(temp,file);
 }finally{
  if(fd!==undefined)fs.closeSync(fd);
  if(fs.existsSync(temp))fs.unlinkSync(temp);
 }
}
function validate(state,symbol){
 if(state?.schemaId!==FIRST_SEEN_SCHEMA||state.symbol!==symbol||state.period!=='5M'||
   !Array.isArray(state.rows)||state.rows.length>20000||
   state.productionReady!==false||state.orderTransmission!==false||
   state.brokerArrivalCertified!==false)fail('FIRST_SEEN_JOURNAL_CONTRACT_INVALID');
 const {journalSha256,...core}=state;
 if(journalSha256!==sha(JSON.stringify(core)))fail('FIRST_SEEN_JOURNAL_HASH_INVALID');
 let head='0'.repeat(64),lastTime=-Infinity,lastCaptured=-Infinity;
 for(let i=0;i<state.rows.length;i++){
  const r=state.rows[i],e=r?.entry;
  if(!e||r.sequence!==i+1||r.previousSha256!==head||
    r.rowSha256!==sha(JSON.stringify({sequence:r.sequence,previousSha256:head,entry:e}))||
    e.productionReady!==false||e.brokerArrivalCertified!==false||
    e.orderTransmission!==false||e.symbol!==symbol)fail('FIRST_SEEN_CHAIN_INVALID');
  const t=millis(e.bar.at,'FIRST_SEEN_BAR_TIME_INVALID');
  const c=millis(e.firstSeenAt,'FIRST_SEEN_CAPTURE_TIME_INVALID');
  if(t<=lastTime||c<=lastCaptured||c<millis(e.bar.conservativeBarClosedAt,'FIRST_SEEN_CLOSE_INVALID'))
    fail('FIRST_SEEN_CHRONOLOGY_INVALID');
  lastTime=t;lastCaptured=c;head=r.rowSha256;
 }
 if(state.eventCount!==state.rows.length||state.headSha256!==head)fail('FIRST_SEEN_HEAD_INVALID');
 return state;
}
function continuity(prev,next){
 if(!prev)return 'FIRST_OBSERVATION';
 const a=millis(prev.bar.at,'FIRST_SEEN_PREV_TIME_INVALID');
 const b=millis(next.bar.at,'FIRST_SEEN_NEXT_TIME_INVALID');
 if(jst(a)!==jst(b))return 'NEW_SESSION_NOT_CONTINUOUS';
 if(b-a===300000)return 'CONTIGUOUS';
 const am=prev.bar.at.slice(11,16),bm=next.bar.at.slice(11,16);
 if((am==='11:25'&&bm==='12:30')||(am==='11:30'&&bm==='12:35'))return 'CONTIGUOUS';
 return 'GAP_OR_CLOCK_MISMATCH';
}
function currentSource(root,now){
 verifyNo12ObservedChart({privateRoot:root,now});
 const raw=readFile(path.join(root,'market-readonly-observed.json'));
 const receipt=JSON.parse(readFile(path.join(root,'market-readonly-receipt.json')).toString('utf8'));
 if(receipt.marketSha256!==sha(raw)||receipt.productionReady!==false||
   receipt.orderTransmission!==false)fail('FIRST_SEEN_MARKET_RECEIPT_RACE');
 const market=JSON.parse(raw.toString('utf8'));
 const symbol=market.symbol,bar=market.bars?.at(-1);
 if(typeof symbol!=='string'||!/^[0-9A-Z]{4}\.T$/.test(symbol)||
   !bar||market.brokerArrivalCertified!==false||market.nativeDecisionCertified!==false||
   market.productionReady!==false||market.orderTransmission!==false||
   market.sourceRecord?.sourceAsOf!==bar.at||market.sourceRecord?.knownAt!==market.capturedAt)
   fail('FIRST_SEEN_MARKET_IDENTITY_UNVERIFIED');
 const captured=millis(market.capturedAt,'FIRST_SEEN_CAPTURE_INVALID');
 const t=millis(bar.at,'FIRST_SEEN_BAR_AT_INVALID');
 const closed=millis(bar.conservativeBarClosedAt,'FIRST_SEEN_BAR_CLOSED_INVALID');
 if(closed!==t+300000||closed>captured||jst(t)!==jst(captured)||
  !['open','high','low','close'].every(k=>typeof bar[k]==='number'&&Number.isFinite(bar[k])&&bar[k]>0)||
  !Number.isSafeInteger(bar.volume)||bar.volume<0||bar.low>Math.min(bar.open,bar.close)||
  bar.high<Math.max(bar.open,bar.close))
   fail('FIRST_SEEN_BAR_INVALID');
 return {symbol,bar:{at:bar.at,conservativeBarClosedAt:bar.conservativeBarClosedAt,
  open:bar.open,high:bar.high,low:bar.low,close:bar.close,volume:bar.volume},
  firstSeenAt:market.capturedAt,sourceReceiptSha256:receipt.marketSha256,
  sourceRecordId:market.sourceRecord.recordId};
}
export function recordNo12MarketFirstSeen({privateRoot,now=new Date()}={}){
 const root=rootOf(privateRoot),source=currentSource(root,now);
 const file=path.join(root,'first-seen-'+source.symbol.replace('.','-')+'.json');
 const lock=file+'.lock';try{fs.mkdirSync(lock)}catch{fail('FIRST_SEEN_LOCKED_OR_UNRECOVERED')}
 try{
  let state;
  if(fs.existsSync(file))state=validate(JSON.parse(readFile(file).toString('utf8')),source.symbol);
  else{
   const core={schemaId:FIRST_SEEN_SCHEMA,symbol:source.symbol,period:'5M',
    rows:[],eventCount:0,headSha256:'0'.repeat(64),brokerArrivalCertified:false,
    productionReady:false,orderTransmission:false};
   state={...core,journalSha256:sha(JSON.stringify(core))};
  }
  const prior=state.rows.at(-1)?.entry??null;
  const previous=prior?millis(prior.bar.at,'FIRST_SEEN_PRIOR_TIME_INVALID'):-Infinity;
  const nowBar=millis(source.bar.at,'FIRST_SEEN_NEW_TIME_INVALID');
  if(nowBar<previous)fail('FIRST_SEEN_SOURCE_ROLLBACK');
  if(nowBar===previous){
   if(sha(JSON.stringify(prior.bar))!==sha(JSON.stringify(source.bar)))
    fail('FIRST_SEEN_REVISED_BAR_BLOCKED');
   return Object.freeze({status:'IDEMPOTENT_OBSERVATION',
    eventCount:state.eventCount,continuity:prior.continuity,
    brokerArrivalCertified:false,productionReady:false,orderTransmission:false});
  }
  if(prior&&millis(source.firstSeenAt,'FIRST_SEEN_NEW_CAPTURE_INVALID')<=
    millis(prior.firstSeenAt,'FIRST_SEEN_PRIOR_CAPTURE_INVALID'))
    fail('FIRST_SEEN_CAPTURE_REGRESSION');
  if(state.rows.length>=20000)fail('FIRST_SEEN_JOURNAL_LIMIT');
  const entry={...source,continuity:continuity(prior,source),
   brokerArrivalCertified:false,productionReady:false,orderTransmission:false};
  const row={sequence:state.rows.length+1,previousSha256:state.headSha256,entry};
  const nextRow={...row,rowSha256:sha(JSON.stringify(row))};
  const core={schemaId:FIRST_SEEN_SCHEMA,symbol:source.symbol,period:'5M',
   rows:[...state.rows,nextRow],eventCount:state.eventCount+1,headSha256:nextRow.rowSha256,
   brokerArrivalCertified:false,productionReady:false,orderTransmission:false};
  const next={...core,journalSha256:sha(JSON.stringify(core))};
  validate(next,source.symbol);atomic(file,next);
  return Object.freeze({status:'LOCAL_FIRST_SEEN_RECORDED',
   eventCount:next.eventCount,continuity:entry.continuity,
   brokerArrivalCertified:false,productionReady:false,orderTransmission:false});
 }finally{fs.rmdirSync(lock)}
}
export function inspectNo12MarketFirstSeen({privateRoot,symbol}={}){
 const root=rootOf(privateRoot);
 if(typeof symbol!=='string'||!/^[0-9A-Z]{4}\.T$/.test(symbol))fail('FIRST_SEEN_SYMBOL_INVALID');
 const file=path.join(root,'first-seen-'+symbol.replace('.','-')+'.json');
 const state=validate(JSON.parse(readFile(file).toString('utf8')),symbol);
 return Object.freeze({eventCount:state.eventCount,headSha256:state.headSha256,
  lastContinuity:state.rows.at(-1)?.entry?.continuity??null,
  brokerArrivalCertified:false,productionReady:false,orderTransmission:false});
}
