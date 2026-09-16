import test from 'node:test';
import assert from 'node:assert/strict';
import {projectPath,horizons,summarizePath} from './phase57_long_exit_paired_paths.mjs';
import {scoreP25ExitV2StateConditioned} from '../predict/daytrade/phase57-p25-exit-v2-state-conditioned.js';
const e={sessionDate:'2024-10-01',decisionTimestamp:'2024-10-01T09:30:00+09:00',decisionPrice:100};
function bar(m){const t=Date.parse(e.decisionTimestamp)+m*60000;return {sessionDate:e.sessionDate,barStartJst:new Date(t).toISOString(),availableAtJst:new Date(t+300000).toISOString(),open:100,high:102,low:98,close:101,observedMinutes:5};}
test('all identity retained; missing never fills',()=>{const p=projectPath([bar(0)],e);assert.equal(p.future[1].missing,true);assert.equal(horizons(p)[10].available,false);assert.equal(horizons(p)[5].available,true);assert.equal(p.decisionTimestamp,e.decisionTimestamp);});
test('samebar order stays unknown; horizon endpoint return',()=>{const p=horizons(projectPath([bar(0)],e))[5];assert.equal(p.ordering,'UNKNOWN_INTRABAR_ORDER');assert.ok(Math.abs(p.mfePct-2)<1e-10);assert.ok(Math.abs(p.maePct+2)<1e-10);assert.ok(Math.abs(p.returnPct-1)<1e-10);});
test('lunch/end boundaries and fixed remaining cap',()=>{const p=projectPath([],{...e,decisionTimestamp:'2024-10-01T11:30:00+09:00'});assert.equal(horizons(p)[5].reason,'LUNCH_BREAK');const q=projectPath([],{...e,decisionTimestamp:'2024-10-01T15:00:00+09:00'});assert.equal(q.future.length,0);assert.equal(horizons(q)[30].reason,'SESSION_END');});
test('duplicates, crosssession and invalid bars fail closed',()=>{assert.throws(()=>projectPath([bar(0),bar(0)],e),/BAR_IDENTITY/);assert.throws(()=>projectPath([{...bar(0),sessionDate:'2024-10-02'}],e),/BAR_IDENTITY/);assert.throws(()=>projectPath([{...bar(0),low:110}],e),/INVALID/);});
test('sparse minutes disclosed, empty unavailable, ordered extrema',()=>{const p=projectPath([{...bar(0),observedMinutes:1},{...bar(5),high:104,low:99}],e);const x=horizons(p)[10];assert.equal(x.sparseMinuteBars,1);assert.equal(x.ordering,'MAE_FIRST');assert.equal(summarizePath([]).available,false);});
test('unchanged causal scorer rejects 2026 analogs for a 2024 LONG query',()=>{
 const pool=Array.from({length:35},(_,i)=>({sessionDate:'2026-07-01',symbol:`SYNTHETIC${i}`,direction:'LONG',fullyRealizedAt:'2026-07-01T01:00:00.000Z',state:{currentReturnPct:1},labels:{1:-1,3:-1,6:-1}}));
 const observed=[0,5,10].map(m=>({timestamp:bar(m).availableAtJst,open:100,high:102,low:99,close:101,volume:100}));
 const score=scoreP25ExitV2StateConditioned({entryPrice:100,direction:'LONG',observedBars:observed,timestamp:observed.at(-1).timestamp,sessionDate:e.sessionDate,analogPool:pool});
 assert.equal(score.ready,false);assert.equal(score.neighborCount,0);assert.equal(score.reason,'INSUFFICIENT_STATE_CONDITIONED_CAUSAL_ANALOGS');
});
