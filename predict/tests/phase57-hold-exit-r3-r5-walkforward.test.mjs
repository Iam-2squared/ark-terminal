import assert from 'node:assert/strict';
import {R3_R5_CANDIDATES,R3_R5_SAFETY,simulateHoldFirst,runHoldExitHistoricalWalkForward} from '../daytrade/phase57-hold-exit-r3-r5-walkforward.js';

function row(sessionDate,i,pattern='good'){
 const entry=100,ctx=Array.from({length:12},(_,k)=>({close:100+k*0.01,high:100.15+k*0.01,low:99.85+k*0.01}));
 const seq=pattern==='breakdown'?[100.5,100.7,100.4,99.9,99.4,99.2]:[100.2,100.4,100.6,100.8,101,101.2];
 return {entryAccepted:true,pointInTimeValid:true,symbol:`T${i%3}`,sessionDate,entryTimestamp:`${sessionDate}T00:${String(i%60).padStart(2,'0')}:00.000Z`,entryPrice:entry,signalDirection:1,baseHorizonBars:6,contextBars:ctx,futureBars:seq.map((close,j)=>({timestamp:`${sessionDate}T01:${String(j).padStart(2,'0')}:00.000Z`,open:close,high:close+0.1,low:close-0.1,close}))};
}
const c=R3_R5_CANDIDATES.find(x=>x.id==='HPX_P2_A075_G075');
const e=simulateHoldFirst(row('2026-01-01',1,'breakdown'),c);
assert.ok(e.barsHeld<6,'persistent deterioration should be able to exit before frozen horizon');
assert.match(e.exitReason,/PERSISTENT_/);
const f=simulateHoldFirst(row('2026-01-01',1,'good'),R3_R5_CANDIDATES[0]);
assert.equal(f.barsHeld,6);
assert.equal(f.exitReason,'FROZEN_HORIZON');

const sessions=Array.from({length:18},(_,i)=>`2026-01-${String(i+1).padStart(2,'0')}`);
const rows=[];for(let s=0;s<sessions.length;s++)for(let i=0;i<6;i++)rows.push(row(sessions[s],i,(s%4===0&&i<3)?'breakdown':'good'));
const out=runHoldExitHistoricalWalkForward(rows,{minTrainSessions:8,validationSessions:3,testSessions:2});
assert.ok(out.folds.length>=2);
assert.equal(out.method,'EXPANDING_DEV_SEPARATE_VALIDATION_OUTER_OOS');
assert.equal(out.noSameOosThresholdSweep,true);
assert.equal(out.currentP25EvidenceUsedForTuning,false);
assert.equal(out.freshHoldoutConsumed,false);
for(const fold of out.folds){
 const dev=new Set(fold.devSessions),val=new Set(fold.validationSessions),test=new Set(fold.testSessions);
 for(const x of dev)assert.ok(!val.has(x)&&!test.has(x));
 for(const x of val)assert.ok(!test.has(x));
 assert.ok(fold.selectedCandidate==='FIXED'||R3_R5_CANDIDATES.some(c=>c.id===fold.selectedCandidate));
}
for(const [k,v] of Object.entries(R3_R5_SAFETY))if(k.endsWith('Allowed')||['transmitted','freshHoldoutConsumed'].includes(k))assert.equal(v,false,`${k} must remain false`);
console.log('Phase57 R3-R5 HOLD-first walk-forward guards passed');
