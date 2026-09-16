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

const freshPacket=()=>{const p=packet();p.connected=null;p.rows[0]={...p.rows[0],currentPrice:100,bestBid:99,bestAsk:101};return p;};
test('fresh feed plus old chart rows observes connection once without stale chart-age alarms',()=>{
  const p=freshPacket();p.rows=Array.from({length:20},(_,i)=>({...p.rows[0],sourceTime:`09:${String(i%12*5).padStart(2,'0')}:00`}));
  p.captureTimestamp='2026-09-14T05:16:07Z';p.rows.forEach(r=>r.marketTimestamp='2026-09-14T05:16:06Z');
  const o=new SourceObserver(),result=o.step(p);
  assert.equal(result.connectionState,'REAL_SOURCE_CONNECTED_OBSERVED');assert.equal(result.currentFeeds.length,1);
  assert.equal(result.problems.filter(x=>x.cause==='STALE_SOURCE_DATA').length,0);assert.equal(result.strategyAllowed,false);
  const stale=structuredClone(p);stale.captureId='2';stale.captureTimestamp='2026-09-14T05:17:00Z';
  const r=o.step(stale);assert.equal(r.problems.filter(x=>x.cause==='STALE_SOURCE_DATA').length,1);
  assert.equal(r.connectionState,'SOURCE_CONNECTION_UNVERIFIED');
});
test('connection observation requires quotes, matching date, chart, coherent feed and healthy reads',()=>{
  for(const mutate of [p=>p.rows[0].bestAsk=0,p=>p.rows[0].marketTimestamp='2026-09-13T00:05:00Z',p=>p.rows=[],
    p=>p.partialRead=true,p=>p.workbookHealthy=false,p=>p.rows.push({...p.rows[0],currentPrice:101}),p=>p.rows[0].sourceTime='18:00:00']){
    const p=freshPacket();mutate(p);assert.notEqual(new SourceObserver().step(p).connectionState,'REAL_SOURCE_CONNECTED_OBSERVED');
  }
});
test('adjacent successor gives candidate latency, subsequent revision invalidates it; latest follows label',()=>{
  const o=new SourceObserver(),p=freshPacket();p.captureTimestamp='2026-09-14T00:04:59Z';p.rows[0].marketTimestamp='2026-09-14T00:04:58Z';o.step(p);
  const q=structuredClone(p);q.captureId='2';q.captureTimestamp='2026-09-14T00:05:02Z';q.rows.push({...q.rows[0],sourceTime:'09:05:00'});o.step(q);
  let r=o.report();assert.equal(r.bars[0].candidateFinalizationLatencyMs,2000);assert.equal(r.latestSourceTime,'09:05:00');assert.equal(r.latestBarAgeMs,2000);
  assert.equal(r.bars[0].safeCompletedBarTime,null);assert.equal(r.finalization,'UNVERIFIED');
  q.captureId='3';q.captureTimestamp='2026-09-14T00:05:03Z';q.rows[0].close=100.5;o.step(q);r=o.report();
  assert.equal(r.bars[0].candidateFinalizationLatencyMs,null);assert.equal(r.bars[0].revisionsAfterNextAppearance,1);assert.equal(r.latestSourceTime,'09:05:00');
});
test('backfills, lunch gap, unchanged values and partial packets never establish finalization',()=>{
  const o=new SourceObserver(),p=freshPacket();p.rows.push({...p.rows[0],sourceTime:'09:05:00'});o.step(p);
  assert.ok(o.report().bars.every(b=>b.candidateFinalizationLatencyMs===null));
  const q=freshPacket();q.captureId='2';q.captureTimestamp='2026-09-14T03:00:00Z';q.rows[0].sourceTime='11:25:00';o.step(q);
  assert.equal(o.report().events.filter(x=>x.captureId==='2'&&x.cause==='STALE_SOURCE_DATA').length,0);
  q.captureId='3';q.captureTimestamp='2026-09-14T03:30:02Z';q.rows[0].sourceTime='12:30:00';o.step(q);
  assert.ok(o.report().bars.every(b=>b.candidateFinalizationLatencyMs===null));
  q.captureId='4';q.partialRead=true;q.rows[0].close=100.5;const before=o.report().bars.at(-1).revisions;o.step(q);
  assert.equal(o.report().bars.at(-1).revisions,before);assert.equal(o.report().readyForStrategy,false);
});

test('raw latest metadata is retained and mismatched normalized latest fails closed',()=>{
  const p=freshPacket();p.rawWindowMetadata=[{slot:0,generation:0,symbol:'1000.T',sourceCode:'1000',sessionDate:p.sessionDate,
    rawLastSourceTime:'09:00:00',rawValidRowCount:136,rawLastExcelRow:138,rawLatestSessionSourceTime:'09:00:00',normalizedLatestSourceTime:'09:00:00',normalizationParity:'PASS'}];
  const o=new SourceObserver();o.step(p);assert.equal(o.report().latestRawWindowMetadata[0].rawLastExcelRow,138);
  p.rawWindowMetadata[0].rawLatestSessionSourceTime='09:05:00';
  assert.throws(()=>new SourceObserver().step(p),/RAW_NORMALIZATION_LAG/);
  p.error='RAW_NORMALIZATION_LAG';p.workbookHealthy=false;p.rows=[];p.rawWindowMetadata[0].normalizationParity='RAW_NORMALIZATION_LAG';
  const failed=new SourceObserver();failed.step(p);assert.ok(failed.report().events.some(e=>e.cause==='RAW_NORMALIZATION_LAG'));
  assert.equal(failed.report().readyForStrategy,false);
});
