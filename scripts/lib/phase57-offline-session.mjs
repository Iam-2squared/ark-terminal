import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {EvidenceLog,FREEZE,SAFETY,hash,digest,exposedDate,instant} from './phase57-offline-parity.mjs';

export const CHANNELS=['raw','normalized','decisions','ledger','health','mismatch','reference','report'];
const same=(a,b)=>assert.deepEqual(a,b,'SESSION_IDENTITY_CHANGED');

// Event sourcing: durable input and its derived output commit as ONE fsynced record.
// On restart the reducer is rebuilt from committed inputs. Already-committed IDs
// cannot cause a second decision. A crash before append can safely be replayed.
export class OfflineSession {
  constructor(directory,identity,makeReducer){
    exposedDate(identity.sessionDate);
    assert.ok(['USED_HISTORICAL_FIXTURE','SYNTHETIC_TRANSPORT_TEST'].includes(identity.sourceClass),'REAL_CAPTURE_LOCKED');
    assert.equal(identity.freezeSha256,FREEZE);
    for(const key of ['repoHead','workbookSha256','sourceIdentity'])assert.match(identity[key],/^[a-f0-9]{40,64}$/);
    this.dir=directory;this.identity={...identity,safety:SAFETY};this.seen=new Map();this.reducer=makeReducer();this.halted=false;this.sealed=false;this.last=-Infinity;
    this.log=new EvidenceLog(path.join(directory,'session.jsonl'));
    try{
      const rows=fs.existsSync(this.log.file)?fs.readFileSync(this.log.file,'utf8').trim().split('\n').filter(Boolean).map(JSON.parse):[];
      if(!rows.length)this.log.append('IDENTITY',this.identity);
      else{
        assert.equal(rows[0].kind,'IDENTITY');same(rows[0].payload,this.identity);
        for(const r of rows.slice(1)){
          assert.ok(!this.sealed&&!this.halted,'EVENT_AFTER_TERMINAL_RECORD');
          if(r.kind==='COMMIT'){
            assert.ok(!this.seen.has(r.payload.id),'DUPLICATE_COMMITTED_ID');
            same(this.reducer(structuredClone(r.payload.input)),r.payload.output);
            this.seen.set(r.payload.id,hash(r.payload.input));
            this.last=instant(r.payload.input.timestamp);
          }else if(r.kind==='HALT')this.halted=true;
          else if(r.kind==='SEAL')this.sealed=true;
          else throw Error('UNKNOWN_SESSION_RECORD');
        }
      }
    }catch(e){this.log.close();throw e;}
  }
  commit(id,input){
    assert.ok(!this.halted&&!this.sealed,'SESSION_HALTED_OR_SEALED');
    assert.ok(typeof id==='string'&&id.length>0,'EVENT_ID_REQUIRED');
    if(this.seen.has(id)){
      if(this.seen.get(id)===hash(input))return {duplicate:true};
      this.halt('CONFLICTING_CAPTURE_ID');throw Error('CONFLICTING_CAPTURE_ID');
    }
    try{
      assert.equal(input.sessionDate,this.identity.sessionDate,'CROSS_SESSION_INPUT');
      assert.ok(instant(input.timestamp)>=this.last,'NONMONOTONIC_SESSION_INPUT');
      const output=this.reducer(structuredClone(input));
      assert.ok(output&&typeof output==='object'&&!Array.isArray(output),'OUTPUT_CHANNELS_REQUIRED');
      for(const [k,v]of Object.entries(output))assert.ok(CHANNELS.includes(k)&&Array.isArray(v),'UNKNOWN_OUTPUT_CHANNEL');
      this.log.append('COMMIT',{id,input,output});this.seen.set(id,hash(input));this.last=instant(input.timestamp);return {duplicate:false,output};
    }catch(e){this.halt(e.message);throw e;}
  }
  halt(reason){this.halted=true;this.log.append('HALT',{reason});}
  close(){this.log.close();}
  seal(report){
    assert.ok(!this.halted&&!this.sealed,'SESSION_HALTED_OR_SEALED');
    // A sealed stream can be exported again into a NEW directory after interruption.
    this.log.append('SEAL',{report});this.sealed=true;
  }
}

export function exportSession(sourceFile,destination){
  const verify=new EvidenceLog(sourceFile);verify.close();
  const rows=fs.readFileSync(sourceFile,'utf8').trim().split('\n').map(JSON.parse);
  assert.equal(rows[0].kind,'IDENTITY');assert.equal(rows.at(-1).kind,'SEAL','SESSION_NOT_SEALED');
  fs.mkdirSync(destination,{recursive:false});
  const files={};
  for(const channel of CHANNELS){
    const content=rows.filter(x=>x.kind==='COMMIT').flatMap(x=>x.payload.output[channel]??[]);
    if(channel==='report')content.push(rows.at(-1).payload.report);
    const bytes=content.map(x=>JSON.stringify(x)+'\n').join('');
    fs.writeFileSync(path.join(destination,channel+'.jsonl'),bytes,{flag:'wx'});
    files[channel]={sha256:digest(bytes),rows:content.length};
  }
  const timestamps=rows.filter(x=>x.kind==='COMMIT').map(x=>x.payload.input.timestamp);
  const manifest={schemaId:'ARK_OFFLINE_SESSION_MANIFEST_V2',...rows[0].payload,captureStart:timestamps[0]??null,captureEnd:timestamps.at(-1)??null,files,journalSha256:digest(fs.readFileSync(sourceFile)),journalTerminalHash:rows.at(-1).sha256,realSessionCaptured:false,reservedDataOpened:false};
  fs.writeFileSync(path.join(destination,'manifest.json'),JSON.stringify(manifest,null,2)+'\n',{flag:'wx'});
  return manifest;
}
