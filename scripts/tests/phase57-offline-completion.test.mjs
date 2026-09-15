import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {OfflineSession,exportSession,CHANNELS} from '../lib/phase57-offline-session.mjs';
import {diagnoseSnapshots,classifyGap,tickSnapshotDiagnostic} from '../lib/phase57-offline-semantics.mjs';
import {FREEZE,hash} from '../lib/phase57-offline-parity.mjs';
import {cumulativeDays} from '../lib/phase57-parity-report.mjs';
const at=time=>'2026-08-13T'+time+':00+09:00';
test('cumulative report preserves bad sessions and forbids duplicate-session cherry picking',()=>{
  const r={sessionDate:'2026-08-13',classification:'USED_HISTORICAL_FIXTURE',freezeSha256:FREEZE,stages:[{stage:'DATA',exact:1,denominator:2}],metrics:{mismatchCountsByCause:{MISSING_RSS_DATA:1}}};const c=cumulativeDays([r,{...r,sessionDate:'2026-08-14'}]);assert.equal(c.stages.DATA.exactMatchRate,.5);assert.equal(c.mismatchCountsByCause.MISSING_RSS_DATA,2);assert.throws(()=>cumulativeDays([r,r]),/DUPLICATE/);
});
test('identical ticks are diagnostic repeats, never silently discarded or fed into MSH',()=>{
  const t={timestamp:at('09:01'),price:100,volume:100};const r=tickSnapshotDiagnostic([t,t]);assert.equal(r.identicalRowRepeats,1);assert.equal(r.rowsDropped,0);assert.equal(r.modelInput,false);assert.throws(()=>tickSnapshotDiagnostic(Array(301).fill(t)),/ROW_LIMIT/);
});
const row=()=>({captureId:'a',symbol:'0000.T',sourceDate:'2026-08-13',sourceTime:'09:00:00',captureAt:at('09:01'),open:100,high:101,low:99,close:100,volume:1,marketTimestamp:at('09:01'),connected:true,workbookHealthy:true,rssError:null});
test('semantics reports both labels and changes, never infers finality from stability',()=>{
  const a=row(),b={...a,captureId:'b',captureAt:at('09:03'),marketTimestamp:at('09:03'),close:101},c={...b,captureId:'c',captureAt:at('09:06')};
  const r=diagnoseSnapshots([a,b,c,c]);assert.equal(r.bars[0].versions,2);assert.equal(r.bars[0].lastChangedAt,b.captureAt);assert.equal(r.bars[0].finalization,'UNVERIFIED');assert.equal(r.uniqueCaptures,3);assert.equal(r.strategyCalculated,false);assert.equal(r.readyForStrategy,false);assert.ok(r.events.some(x=>x.cause==='DUPLICATE_CAPTURE'));assert.ok(r.events.some(x=>x.cause==='RSS_STALE_DATA'));
});
test('source diagnostics classify disconnect, closed workbook, cell errors and malformed numbers',()=>{
  for(const [change,cause]of [[{connected:false},'MSII_DISCONNECTED'],[{workbookHealthy:false},'EXCEL_CAPTURE_FAILURE'],[{rssError:'#N/A'},'RSS_CELL_ERROR'],[{close:'abc'},'MALFORMED_NUMERIC_CELL'],[{marketTimestamp:null},'MISSING_MARKET_TIMESTAMP'],[{marketTimestamp:at('09:02')},'FUTURE_MARKET_TIMESTAMP']])assert.ok(diagnoseSnapshots([{...row(),...change}]).events.some(x=>x.cause===cause));
});
test('diagnostics reject strategy fields, reserved dates, timezones and conflicting duplicate captures',()=>{
  assert.throws(()=>diagnoseSnapshots([{...row(),entry:1}]),/STRATEGY/);
  assert.throws(()=>diagnoseSnapshots([{...row(),sourceDate:'2026-09-10'}]),/RESERVED/);
  assert.throws(()=>diagnoseSnapshots([{...row(),captureAt:'2026-08-13T09:00:00'}]),/TIMESTAMP/);
  assert.throws(()=>diagnoseSnapshots([{...row(),captureAt:'2026-08-14T00:00:00Z'}]),/TIMEZONE/);
  assert.throws(()=>diagnoseSnapshots([row(),{...row(),close:101}]),/CONFLICTING/);
});
test('gap classes distinguish exact lunch, real missing input and unknown provenance',()=>{
  assert.equal(classifyGap(at('11:30'),at('12:35')),'LUNCH_BREAK');
  assert.equal(classifyGap(at('09:05'),at('09:10')),null);
  assert.equal(classifyGap(at('09:05'),at('09:15')),'UNKNOWN');
  assert.equal(classifyGap(at('09:05'),at('09:15'),{savedFixture:true}),'FIXTURE_LIMITATION');
  assert.equal(classifyGap(at('09:05'),at('09:15'),{sourceMissingConfirmed:true}),'SOURCE_MISSING');
  assert.equal(classifyGap(at('09:05'),at('09:16')),'INVALID_5M_GRID');
  assert.equal(classifyGap(at('15:30'),'2026-08-14T09:05:00+09:00'),'UNKNOWN');
  assert.equal(classifyGap(at('15:30'),'2026-08-14T09:05:00+09:00',{sessionTransitionConfirmed:true}),'EXPECTED_SESSION_GAP');
});
const identity={sessionDate:'2026-08-13',sourceClass:'SYNTHETIC_TRANSPORT_TEST',freezeSha256:FREEZE,repoHead:'a'.repeat(40),workbookSha256:'b'.repeat(64),sourceIdentity:'c'.repeat(64)};
const input=n=>({sessionDate:'2026-08-13',timestamp:at('09:0'+n),n});
const reducer=()=>{let total=0;return x=>({raw:[x],decisions:[{total:total+=x.n}]});};
function scope(fn){const dir=fs.mkdtempSync(path.join(os.tmpdir(),'ark-completion-'));try{fn(dir);}finally{fs.rmSync(dir,{recursive:true,force:true});}}
test('restart replays state exactly and suppresses duplicate decisions with durable identity',()=>scope(dir=>{
  let s=new OfflineSession(dir,identity,reducer);s.commit('a',input(1));s.close();
  s=new OfflineSession(dir,identity,reducer);assert.equal(s.commit('a',input(1)).duplicate,true);assert.equal(s.commit('b',input(2)).output.decisions[0].total,3);s.seal({pass:true});s.close();
  const m=exportSession(path.join(dir,'session.jsonl'),path.join(dir,'export'));assert.equal(m.files.decisions.rows,2);assert.deepEqual(Object.keys(m.files),CHANNELS);assert.throws(()=>exportSession(path.join(dir,'session.jsonl'),path.join(dir,'export')));
  s=new OfflineSession(dir,identity,reducer);assert.throws(()=>s.commit('c',input(3)),/SEALED/);s.close();
}));
test('restart rejects changed identity and reducer version without overwriting evidence',()=>scope(dir=>{
  const s=new OfflineSession(dir,identity,reducer);s.commit('a',input(1));s.close();const before=fs.readFileSync(path.join(dir,'session.jsonl'),'utf8');
  assert.throws(()=>new OfflineSession(dir,{...identity,repoHead:'d'.repeat(40)},reducer),/IDENTITY/);
  assert.throws(()=>new OfflineSession(dir,identity,()=>()=>({decisions:[]})),/IDENTITY/);
  assert.equal(fs.readFileSync(path.join(dir,'session.jsonl'),'utf8'),before);
}));
test('conflicting capture halts session persistently',()=>scope(dir=>{
  let s=new OfflineSession(dir,identity,reducer);s.commit('a',input(1));assert.throws(()=>s.commit('a',input(2)),/CONFLICTING/);s.close();s=new OfflineSession(dir,identity,reducer);assert.throws(()=>s.commit('b',input(2)),/HALTED/);s.close();
}));
test('partial evidence and stale crash lock preserve files and fail closed',()=>scope(dir=>{
  const file=path.join(dir,'session.jsonl');let s=new OfflineSession(dir,identity,reducer);s.commit('a',input(1));s.close();fs.appendFileSync(file,'{');const before=fs.readFileSync(file);assert.throws(()=>new OfflineSession(dir,identity,reducer),/TORN/);assert.deepEqual(fs.readFileSync(file),before);fs.writeFileSync(file+'.lock','crashed');assert.throws(()=>new OfflineSession(dir,identity,reducer));assert.equal(fs.readFileSync(file+'.lock','utf8'),'crashed');
}));
test('reserved or real data sessions never start reducers',()=>scope(dir=>{
  let calls=0;const factory=()=>{calls++;return ()=>({});};
  assert.throws(()=>new OfflineSession(dir,{...identity,sessionDate:'2026-10-22'},factory));assert.throws(()=>new OfflineSession(dir,{...identity,sourceClass:'REALTIME'},factory));assert.equal(calls,0);
}));
test('exported hashes cover all channels and immutable seal',()=>scope(dir=>{
  const s=new OfflineSession(dir,identity,reducer);s.commit('a',input(1));s.seal({badSession:true});s.close();const m=exportSession(path.join(dir,'session.jsonl'),path.join(dir,'export'));assert.equal(m.files.report.rows,1);assert.equal(m.safety.transmitted,false);assert.equal(m.reservedDataOpened,false);assert.equal(hash(JSON.parse(fs.readFileSync(path.join(dir,'export/manifest.json')))),hash(m));
}));
