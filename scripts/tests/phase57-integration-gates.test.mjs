import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {admitMode,SyntheticCashBook,capacityBoundary,inspectOosPrecommit} from '../lib/phase57-integration-gates.mjs';
import {reconcileState} from '../lib/phase57-operational-robustness.mjs';
import {SourceObserver} from '../lib/phase57-source-observer.mjs';
const packet=()=>({mode:'SOURCE_SEMANTICS_ONLY',sourceClass:'SYNTHETIC_TRANSPORT_TEST',sourceIdentity:'synthetic',workbookIdentity:'dedicated',workbookVersion:'v1',fieldMapSha256:'a'.repeat(64),captureId:'1',captureTimestamp:'2026-09-14T00:05:01Z',sessionDate:'2026-09-14',connected:true,workbookHealthy:true,partialRead:false,
  rows:[{slot:0,generation:0,symbol:'1000.T',sourceCode:'1000',sourceDate:'2026-09-14',sourceTime:'09:00:00',open:100,high:101,low:99,close:100,volume:1,marketTimestamp:'2026-09-14T00:05:00Z'}]});
test('reserved source-only diagnostics never admit strategy modes or OOS',()=>{
  assert.equal(admitMode(packet()).strategyAllowed,false);
  for(const mode of ['OFFLINE_FIXTURE','POST_CLOSE_PARITY','REALTIME_SHADOW'])assert.throws(()=>admitMode({...packet(),mode}));
  assert.throws(()=>admitMode({...packet(),sessionDate:'2026-10-22'}),/OOS_LOCKED/);
});
test('unchanged values and repeated captures do not prove finality',()=>{
  const o=new SourceObserver(),p=packet();o.step(p);assert.equal(o.step(p).duplicate,true);
  o.step({...p,captureId:'2',captureTimestamp:'2026-09-14T00:05:02Z'});
  assert.equal(o.report().bars[0].safeCompletedBarTime,null);assert.equal(o.report().readyForStrategy,false);
  assert.equal(o.report().bars[0].observations,2);
});
test('source-only boundary rejects strategy fields and identity changes',()=>{
  assert.throws(()=>new SourceObserver().step({...packet(),entry:[]}));
  const o=new SourceObserver();o.step(packet());assert.throws(()=>o.step({...packet(),captureId:'2',workbookVersion:'v2'}),/IDENTITY_CHANGED/);
  const p=packet();p.rows[0].pnl=0;assert.throws(()=>new SourceObserver().step(p),/UNKNOWN_ROW/);
});
test('slot reassignment cannot associate an old row with a new symbol',()=>{
  const o=new SourceObserver();o.step(packet());const p=packet();p.captureId='2';p.rows[0].symbol='2000.T';o.step(p);
  assert.ok(o.report().events.some(x=>x.cause==='SYMBOL_MAPPING_DIFFERENCE'));
});
test('stale, partial, disconnected, malformed and future timestamps stay observable',()=>{
  for(const [mutate,cause] of [
    [p=>{p.connected=false;},'SOURCE_DISCONNECTED'],[p=>{p.partialRead=true;},'PARTIAL_READ'],
    [p=>{p.rows[0].close='#N/A';},'MALFORMED_SOURCE_CELL'],[p=>{p.rows[0].marketTimestamp='2026-09-14T00:04:00Z';},'STALE_SOURCE_DATA'],
    [p=>{p.rows[0].marketTimestamp='2026-09-14T00:06:00Z';},'CLOCK_DRIFT_OR_FUTURE_SOURCE']]){
    const o=new SourceObserver(),p=packet();mutate(p);o.step(p);assert.ok(o.report().events.some(x=>x.cause===cause));assert.equal(o.report().strategyCalculated,false);
  }
});
test('revisions, duplicate rows, clock reversal and lunch are not silently repaired',()=>{
  const o=new SourceObserver();o.step(packet());const p=packet();p.captureId='2';p.rows[0].close=100.5;p.rows.push(structuredClone(p.rows[0]));o.step(p);
  assert.ok(o.report().events.some(x=>x.cause==='OBSERVED_VALUE_REVISION'));
  assert.ok(o.report().events.some(x=>x.cause==='DUPLICATE_ROW'));
  assert.throws(()=>o.step({...packet(),captureId:'3',captureTimestamp:'2026-09-14T00:04:00Z'}),/CLOCK/);
  const lunch=packet();lunch.captureTimestamp='2026-09-14T03:00:00Z';lunch.captureId='4';o.step(lunch);assert.equal(o.report().coverage.lunch,true);
});
test('unknown or duplicate external positions never reconcile',()=>{
  assert.equal(reconcileState({},{}).decisionAllowed,false);
  const x={cashJpy:10,equityJpy:10,grossExposureJpy:0,absoluteNetExposureJpy:0,positions:[]};
  assert.equal(reconcileState(x,x).decisionAllowed,true);
  const dup={...x,positions:[{symbol:'1000.T',direction:'LONG',quantity:100},{symbol:'1000.T',direction:'LONG',quantity:100}]};
  assert.equal(reconcileState(dup,dup).decisionAllowed,false);
});
test('withdrawal changes next budget not PnL, duplicates are idempotent',()=>{
  const b=new SyntheticCashBook({cashJpy:1300000,equityJpy:1300000,tradingPnlJpy:300000});
  const e={sourceClass:'SYNTHETIC_TRANSPORT_TEST',id:'w',type:'WITHDRAWAL',amountJpy:300000,timestamp:'2026-08-13T01:00:00Z'};
  const r=b.apply(e);assert.equal(r.equityJpy,1000000);assert.equal(r.tradingPnlJpy,300000);assert.equal(r.nextSlotBudgetJpy,1000000/3);assert.deepEqual(b.apply(e),r);
  assert.throws(()=>b.apply({...e,amountJpy:1}),/CONFLICTING/);
  assert.throws(()=>b.apply({...e,id:'large',amountJpy:1000001}),/EXCEEDS/);
  assert.equal(b.snapshot().equityJpy,1000000);
});
test('manual adjustments require reason and remain outside trading return',()=>{
  const b=new SyntheticCashBook({cashJpy:1000,equityJpy:1000,tradingPnlJpy:0});
  const e={sourceClass:'SYNTHETIC_TRANSPORT_TEST',id:'a',type:'MANUAL_ADJUSTMENT',amountJpy:-100,timestamp:'2026-08-13T01:00:00Z'};
  assert.throws(()=>b.apply(e),/REASON/);assert.equal(b.apply({...e,reason:'synthetic correction'}).tradingPnlJpy,0);
});
test('unknown constraints do not change frozen shadow or authorize orders',()=>{
  const r=capacityBoundary({strategyDesiredQuantity:500,frozenShadowQuantity:300});
  assert.equal(r.finalExecutableQuantity,300);assert.equal(r.constraintAllowedQuantity,null);assert.equal(r.executionAllowed,false);
});
test('OOS inspection preserves four arms and never unlocks',()=>{
  const r=inspectOosPrecommit(process.cwd());assert.equal(r.window.targetEligibleMarketSessions,20);assert.equal(r.unlockAllowed,false);assert.equal(r.outcomesRead,false);
});
test('source diagnostic CLI seals evidence and never overwrites an existing run',()=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'ark-source-observer-'));
  const input=path.join(root,'raw.jsonl'),output=path.join(root,'report');
  fs.writeFileSync(input,JSON.stringify(packet())+'\n');
  const args=['scripts/phase57-source-diagnostic.mjs',input,output];
  execFileSync(process.execPath,args,{stdio:'pipe'});
  const summary=JSON.parse(fs.readFileSync(path.join(output,'summary.json')));
  assert.equal(summary.strategyCalculated,false);assert.equal(summary.finalization,'UNVERIFIED');
  const evidence=fs.readFileSync(path.join(output,'source-diagnostic.jsonl'),'utf8');
  assert.equal(JSON.parse(evidence.trim().split('\n').at(-1)).kind,'SEAL');
  assert.throws(()=>execFileSync(process.execPath,args,{stdio:'pipe'}));
  assert.equal(fs.readFileSync(path.join(output,'source-diagnostic.jsonl'),'utf8'),evidence);
});
