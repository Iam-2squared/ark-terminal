import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {digest} from '../../../integration/no1-1-msii/runtime/locked_intent.mjs';
import {No12SyntheticJournal as Journal} from '../runtime/synthetic_durable_journal.mjs';
const scenario=digest({strategy:'No12 synthetic',seed:42});
function make(){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'no12-durable-'));
 const session='2026-10-13';
 return {root,session,create:()=>new Journal({privateRoot:root,session,scenarioSha256:scenario}),
  cleanup:()=>fs.rmSync(root,{force:true,recursive:true})};
}
const event=(id,kind='ENTRY_SIGNAL')=>({
 eventId:id,kind,session:'2026-10-13',
 knownAt:'2026-10-13T09:36:01+09:00',entryId:'e-1',orderId:'synthetic-1',
 productionReady:false,transmitted:false
});
test('journal initializes blocked, writes and reloads without duplicate order intents',()=>{
 const f=make();try{
  const a=f.create();assert.equal(a.snapshot().eventCount,0);
  assert.equal(a.append(event('one')).status,'SYNTHETIC_EVENT_RECORDED');
  const b=f.create();assert.equal(b.snapshot().eventCount,1);
  assert.equal(b.append(event('one')).status,'IDEMPOTENT_REPLAY');
  assert.equal(a.snapshot().eventCount,1);
  assert.equal(b.snapshot().productionReady,false);
 }finally{f.cleanup();}
});
test('reusing event ID with changed content is always rejected',()=>{
 const f=make();try{
  const journal=f.create();journal.append(event('same'));
  assert.throws(()=>journal.append({...event('same'),quantity:200}),/NO12_EVENT_ID_REUSE_CONFLICT/);
  assert.equal(journal.snapshot().eventCount,1);
 }finally{f.cleanup();}
});
test('on-disk tamper/rollback is detectable through chain and root checksum',()=>{
 const f=make();try{
  const j=f.create();j.append(event('a'));j.append(event('b','BUY_FILL'));
  const filename=path.join(f.root,'no12-shadow-2026-10-13.json');
  const data=JSON.parse(fs.readFileSync(filename,'utf8'));
  data.rows[0].event.kind='SELL_FILL';
  fs.writeFileSync(filename,JSON.stringify(data));
  assert.throws(()=>j.snapshot(),/NO12_JOURNAL_CHECKSUM_MISMATCH/);
 }finally{f.cleanup();}
});
test('bad row chain cannot be masked merely by recalculating the root checksum',()=>{
 const f=make();try{
  const j=f.create();j.append(event('a'));j.append(event('b'));
  const filename=path.join(f.root,'no12-shadow-2026-10-13.json');
  const data=JSON.parse(fs.readFileSync(filename,'utf8'));
  data.rows[1].previousSha256='f'.repeat(64);
  const {journalSha256,...core}=data;
  data.journalSha256=digest(core);
  fs.writeFileSync(filename,JSON.stringify(data));
  assert.throws(()=>j.snapshot(),/NO12_JOURNAL_SEQUENCE_OR_CHAIN_INVALID/);
 }finally{f.cleanup();}
});
test('concurrent writer lock blocks without modifying prior events',()=>{
 const f=make();try{
  const j=f.create();
  fs.mkdirSync(path.join(f.root,'no12-shadow-2026-10-13.json.lock'));
  assert.throws(()=>j.append(event('x')),/NO12_JOURNAL_CONCURRENT_WRITER_BLOCKED/);
  assert.equal(j.snapshot().eventCount,0);
 }finally{f.cleanup();}
});
test('a replayed day cannot be silently interpreted as another scenario',()=>{
 const f=make();try{
  f.create().append(event('x'));
  assert.throws(()=>new Journal({privateRoot:f.root,session:f.session,
   scenarioSha256:'f'.repeat(64)}),/NO12_JOURNAL_CONTRACT_INVALID/);
  assert.equal(f.create().snapshot().eventCount,1);
 }finally{f.cleanup();}
});
test('real mode, wrong day and attempted live-order flags all fail closed',()=>{
 const f=make();try{
  assert.throws(()=>new Journal({privateRoot:f.root,session:f.session,
    scenarioSha256:scenario,mode:'LIVE_ATTESTED'}),/NO12_LIVE_ORDER_JOURNAL_NOT_IMPLEMENTED/);
  const j=f.create();
  assert.throws(()=>j.append({...event('wrong'),session:'2026-10-14'}),/NO12_EVENT_SESSION_MISMATCH/);
  assert.throws(()=>j.append({...event('unsafe'),productionReady:true}),/NO12_EVENT_LIVE_FLAG_FORBIDDEN/);
  assert.throws(()=>j.append({...event('date'),knownAt:'2026-10-14T09:36:01+09:00'}),/NO12_EVENT_LOCAL_DAY_MISMATCH/);
 }finally{f.cleanup();}
});
test('existing account files and unrelated personal archives are never modified',()=>{
 const f=make();try{
  const owner=path.join(f.root,'ownership-baseline.json');
  fs.writeFileSync(owner,'PRIVATE_SENTINEL');
  f.create().append(event('x'));
  assert.equal(fs.readFileSync(owner,'utf8'),'PRIVATE_SENTINEL');
 }finally{f.cleanup();}
});
