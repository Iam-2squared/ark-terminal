/**
 * No.1.2 one-session crash-recoverable synthetic event journal.
 * A durable read-only research witness, NOT an order queue or Excel writer.
 * No actual brokerage orders can originate here.
 */
import fs from 'node:fs';
import path from 'node:path';
import {randomUUID} from 'node:crypto';
import {digest} from '../../../integration/no1-1-msii/runtime/locked_intent.mjs';

export const SHADOW_JOURNAL_SCHEMA='ARK_NO12_PRIVATE_SYNTHETIC_EVENT_JOURNAL_V1';
const zero='0'.repeat(64);
const allowed=new Set(['ENTRY_SIGNAL','BUY_FILL','SELL_INTENT','SELL_FILL']);
const fail=label=>{throw Error(label)};
function date(x,label){
  if(typeof x!=='string'||!/(Z|[+-]\d{2}:\d{2})$/.test(x)||!Number.isFinite(Date.parse(x)))fail(label);
  return new Date(x);
}
function jst(ms){
  return new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tokyo',
    year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(ms)).replace(/\//g,'-');
}
function validatedEvent(event,session){
  if(!event||typeof event!=='object'||Array.isArray(event))fail('NO12_EVENT_OBJECT_REQUIRED');
  if(!allowed.has(event.kind)||typeof event.eventId!=='string'||
     !/^[a-zA-Z0-9_.:-]{1,128}$/.test(event.eventId))fail('NO12_EVENT_KIND_OR_ID_INVALID');
  if(event.session!==session)fail('NO12_EVENT_SESSION_MISMATCH');
  const at=date(event.knownAt,'NO12_EVENT_KNOWN_AT_INVALID').getTime();
  if(jst(at)!==session)fail('NO12_EVENT_LOCAL_DAY_MISMATCH');
  if(event.transmitted===true||event.liveTradingAllowed===true||
     event.productionReady===true||event.executionAllowed===true)
    fail('NO12_EVENT_LIVE_FLAG_FORBIDDEN');
  const encoded=JSON.stringify(event);
  if(typeof encoded!=='string'||encoded.length>12000)fail('NO12_EVENT_TOO_LARGE_OR_INVALID');
  const copy=JSON.parse(encoded);
  if(digest(copy)!==digest(event))fail('NO12_EVENT_NOT_SERIALIZABLE');
  return copy;
}
function validRoot(root){
  if(typeof root!=='string'||!path.isAbsolute(root))fail('NO12_PRIVATE_DIRECTORY_ABSOLUTE_REQUIRED');
  const target=path.resolve(root);
  const st=fs.lstatSync(target);
  if(!st.isDirectory()||st.isSymbolicLink())fail('NO12_PRIVATE_DIRECTORY_UNSAFE');
  return target;
}
function validateState(obj,session,scenarioSha256){
  if(!obj||obj.schemaId!==SHADOW_JOURNAL_SCHEMA||obj.mode!=='SYNTHETIC_OFFLINE_ONLY'||
     obj.session!==session||obj.scenarioSha256!==scenarioSha256||
     obj.productionReady!==false||obj.orderTransmission!==false||
     !Array.isArray(obj.rows)||obj.rows.length>20000)fail('NO12_JOURNAL_CONTRACT_INVALID');
  const {journalSha256,...core}=obj;
  if(typeof journalSha256!=='string'||journalSha256!==digest(core))
    fail('NO12_JOURNAL_CHECKSUM_MISMATCH');
  let previous=zero;
  const eventIds=new Map();
  for(let n=0;n<obj.rows.length;n++){
    const r=obj.rows[n];
    if(r.sequence!==n+1||r.previousSha256!==previous)
      fail('NO12_JOURNAL_SEQUENCE_OR_CHAIN_INVALID');
    validatedEvent(r.event,session);
    const payload={sequence:r.sequence,previousSha256:r.previousSha256,event:r.event};
    if(r.rowSha256!==digest(payload))fail('NO12_JOURNAL_ROW_HASH_MISMATCH');
    const fingerprint=digest(r.event);
    if(eventIds.has(r.event.eventId))fail('NO12_JOURNAL_DUPLICATE_ID_CORRUPT');
    eventIds.set(r.event.eventId,fingerprint);
    previous=r.rowSha256;
  }
  if(obj.headSha256!==previous||obj.eventCount!==obj.rows.length)
    fail('NO12_JOURNAL_HEAD_OR_COUNT_MISMATCH');
  return obj;
}
function atomicWrite(dest,value){
  const temp=dest+'.tmp-'+process.pid+'-'+randomUUID();
  let fd;
  try{
    fd=fs.openSync(temp,'wx',0o600);
    fs.writeFileSync(fd,JSON.stringify(value,null,2)+'\n','utf8');
    fs.fsyncSync(fd);
    fs.closeSync(fd);fd=undefined;
    fs.renameSync(temp,dest);
  }finally{
    if(fd!==undefined)fs.closeSync(fd);
    if(fs.existsSync(temp))fs.unlinkSync(temp);
  }
}
export class No12SyntheticJournal{
  constructor({privateRoot,session,scenarioSha256,mode='SYNTHETIC_OFFLINE_ONLY'}={}){
    if(mode!=='SYNTHETIC_OFFLINE_ONLY')fail('NO12_LIVE_ORDER_JOURNAL_NOT_IMPLEMENTED');
    if(typeof session!=='string'||! /^\d{4}-\d{2}-\d{2}$/.test(session))
      fail('NO12_JOURNAL_SESSION_INVALID');
    if(!/^[a-f0-9]{64}$/.test(scenarioSha256??''))fail('NO12_SCENARIO_ID_REQUIRED');
    const root=validRoot(privateRoot);
    this.session=session;this.scenarioSha256=scenarioSha256;
    this.filename=path.join(root,'no12-shadow-'+session+'.json');
    this.lockName=this.filename+'.lock';
    this._locked(()=>{
      if(!fs.existsSync(this.filename)){
        const core={schemaId:SHADOW_JOURNAL_SCHEMA,session,scenarioSha256,
          mode:'SYNTHETIC_OFFLINE_ONLY',eventCount:0,headSha256:zero,
          rows:[],productionReady:false,orderTransmission:false};
        atomicWrite(this.filename,{...core,journalSha256:digest(core)});
      }else this._read();
    });
  }
  _locked(action){
    try{fs.mkdirSync(this.lockName);}catch{fail('NO12_JOURNAL_CONCURRENT_WRITER_BLOCKED');}
    try{return action();}
    finally{fs.rmdirSync(this.lockName);}
  }
  _read(){
    const file=fs.lstatSync(this.filename);
    if(!file.isFile()||file.isSymbolicLink())fail('NO12_JOURNAL_FILE_UNSAFE');
    const x=JSON.parse(fs.readFileSync(this.filename,'utf8'));
    return validateState(x,this.session,this.scenarioSha256);
  }
  snapshot(){
    const x=this._read();
    return Object.freeze({schemaId:x.schemaId,session:x.session,
      eventCount:x.eventCount,headSha256:x.headSha256,
      events:Object.freeze(x.rows.map(r=>Object.freeze(structuredClone(r.event)))),
      productionReady:false,orderTransmission:false});
  }
  append(event){
    const row=validatedEvent(event,this.session);
    return this._locked(()=>{
      const cur=this._read();
      const prior=cur.rows.find(r=>r.event.eventId===row.eventId);
      if(prior){
        if(digest(prior.event)!==digest(row))fail('NO12_EVENT_ID_REUSE_CONFLICT');
        return Object.freeze({status:'IDEMPOTENT_REPLAY',eventCount:cur.eventCount,
          headSha256:cur.headSha256,orderTransmission:false});
      }
      if(cur.rows.length>=20000)fail('NO12_JOURNAL_MAX_EVENTS_EXCEEDED');
      const payload={sequence:cur.rows.length+1,previousSha256:cur.headSha256,
        event:row};
      const newRow={...payload,rowSha256:digest(payload)};
      const core={...cur,rows:[...cur.rows,newRow],eventCount:cur.eventCount+1,
        headSha256:newRow.rowSha256};
      delete core.journalSha256;
      atomicWrite(this.filename,{...core,journalSha256:digest(core)});
      return Object.freeze({status:'SYNTHETIC_EVENT_RECORDED',
        eventCount:core.eventCount,headSha256:core.headSha256,
        productionReady:false,orderTransmission:false});
    });
  }
}
