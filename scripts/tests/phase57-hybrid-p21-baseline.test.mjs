import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { SAFETY, buildStatefulLedger, freezeFeatureRecord, buildFutureLabels, summarizeDirectional, auditAdmission, timeBucket, verifyFreeze } from '../lib/phase57-hybrid-p21-baseline.mjs';
const iso = (time, date='2026-09-01') => `${date}T${time}:00+09:00`;
const bar = (time, close=100, date='2026-09-01') => ({ timestamp:iso(time,date), availableAt:new Date(Date.parse(iso(time,date))+300000).toISOString(), open:100,high:Math.max(101,close),low:Math.min(99,close),close,volume:1000 });
const event = (time,status,direction=null,symbol='7203.T') => ({decisionAt:iso(time),sessionDate:'2026-09-01',symbol,p21Status:status,direction});
const freeze = () => freezeFeatureRecord({decisionAt:iso('10:00'),symbol:'7203.T',bars:[bar('09:55')],features:{vwapDistance:0}});
test('all safety flags remain false',()=>assert.ok(Object.values(SAFETY).every(x=>x===false)));
test('one first-enter opportunity, not two trades',()=>{
  const r=buildStatefulLedger([event('10:10','ENTER','LONG'),event('10:00','ABSTAIN'),event('10:05','ENTER','LONG')]);
  assert.equal(r.counts.selectionEvents,3);assert.equal(r.counts.p21Eligible,2);assert.equal(r.counts.firstEnterOpportunities,1);
  assert.equal(r.counts.repeatedSameDirectionSignals,1);assert.equal(r.ledger[1].entryDelayMinutes,5);assert.equal(r.ledger[2].alreadyEntered,true);
  assert.equal(r.ledger[0].selectedAtNextFiveMinutes,true);assert.equal(r.ledger[2].selectedAtNextFiveMinutes,null);
});
test('direction flip is not a second stateful trade',()=>{
  const r=buildStatefulLedger([event('10:00','ENTER','LONG'),event('10:05','ENTER','SHORT')]);
  assert.equal(r.counts.firstEnterOpportunities,1);assert.equal(r.counts.repeatedSameDirectionSignals,0);assert.equal(r.counts.short,1);
});
test('blocked is distinct from abstain',()=>{
  const r=buildStatefulLedger([event('10:00','BLOCKED'),event('10:05','ABSTAIN')]);
  assert.equal(r.counts.p21Blocked,1);assert.equal(r.counts.p21Abstain,1);assert.equal(r.counts.coverage,0);
});
test('duplicate timestamp aliases are rejected',()=>{
  const x=event('10:00','ABSTAIN');assert.throws(()=>buildStatefulLedger([x,{...x,decisionAt:new Date(x.decisionAt).toISOString()}]),/DUPLICATE/);
});
test('session reset is distinct from within-session reentry',()=>{
  const r=buildStatefulLedger([event('10:00','ENTER','LONG'),{...event('10:00','ENTER','LONG'),decisionAt:iso('10:00','2026-09-02'),sessionDate:'2026-09-02'}]);
  assert.equal(r.counts.firstEnterOpportunities,2);assert.equal(r.counts.uniqueSymbols,1);assert.equal(r.counts.uniqueSymbolSessions,2);
});
test('empty population is unknown coverage, not zero',()=>assert.equal(buildStatefulLedger([]).counts.coverage,null));
test('invalid direction and session fail closed',()=>{
  assert.throws(()=>buildStatefulLedger([event('10:00','ENTER')]),/DIRECTION/);
  assert.throws(()=>buildStatefulLedger([{...event('10:00','ABSTAIN'),sessionDate:'2026-09-02'}]),/EVENT_ID/);
});
test('prefix completion and delayed availability enforced',()=>{
  assert.throws(()=>freezeFeatureRecord({decisionAt:iso('10:00'),symbol:'7203.T',bars:[bar('10:00')]}),/PREFIX/);
  assert.throws(()=>freezeFeatureRecord({decisionAt:iso('10:00'),symbol:'7203.T',bars:[{...bar('09:55'),availableAt:iso('10:01')}]}),/PREFIX/);
});
test('nested future feature rejected',()=>assert.throws(()=>freezeFeatureRecord({decisionAt:iso('10:00'),symbol:'7203.T',bars:[bar('09:55')],features:{nested:{futureReturn:1}}}),/FUTURE_FIELD/));
test('feature mutation invalidates labels',()=>assert.throws(()=>buildFutureLabels({...freeze(),anchorPrice:200},[],5),/FREEZE_CHANGED/));
test('gross zero is not a hit; costs remain explicit',()=>{
  const r=buildFutureLabels(freeze(),[bar('10:00')],5).horizons[1];
  assert.equal(r.LONG.hit,false);assert.equal(r.SHORT.hit,false);assert.equal(r.LONG.netReturnBps,-5);
  assert.throws(()=>buildFutureLabels(freeze(),[],undefined),/COST/);
});
test('long and short labels are symmetric, not selector opportunity utility',()=>{
  const r=buildFutureLabels(freeze(),[bar('10:00',102)],5).horizons[1];
  assert.ok(r.LONG.grossReturnBps>0);assert.equal(r.SHORT.grossReturnBps,-r.LONG.grossReturnBps);
  assert.equal(r.LONG.mfeBps,r.SHORT.maeBps);assert.equal(r.LONG.timeToMfeMinutes,5);
});
test('missing slot censors horizon rather than selecting next observed bar',()=>{
  const r=buildFutureLabels(freeze(),[bar('10:00'),bar('10:10'),bar('10:15')],5);
  assert.equal(r.horizons[1].complete,true);assert.equal(r.horizons[3].complete,false);
});
test('overnight label completion forbidden',()=>assert.throws(()=>buildFutureLabels(freeze(),[bar('10:00',100,'2026-09-02')],5),/FUTURE_SESSION/));
test('lunch is scheduled non-trading time; same-session labels may cross it',()=>{
  const f=freezeFeatureRecord({decisionAt:iso('11:25'),symbol:'7203.T',bars:[bar('11:20')]});
  const r=buildFutureLabels(f,[bar('11:25'),bar('12:30'),bar('12:35',102)],5);
  assert.equal(r.horizons[3].complete,true);assert.equal(r.horizons[3].LONG.timeToMfeMinutes,75);
});
test('summary excludes censored denominator',()=>{
  const rows=[{...event('10:00','ENTER','LONG'),labels:buildFutureLabels(freeze(),[bar('10:00',102)],5)},event('10:05','ENTER','SHORT')];
  const r=summarizeDirectional(rows,1);assert.equal(r.labeled,1);assert.equal(r.censored,1);assert.equal(r.hitRate,1);
});
test('time buckets fixed before outcomes',()=>{
  assert.equal(timeBucket(iso('10:25')),'MORNING_EARLY');assert.equal(timeBucket(iso('10:30')),'MORNING_LATE');
  assert.equal(timeBucket(iso('13:55')),'AFTERNOON_EARLY');assert.equal(timeBucket(iso('14:00')),'AFTERNOON_LATE');
});
test('default admission is blocked',()=>assert.equal(auditAdmission({}).ready,false));
test('current P21 cannot be projected into 2025, even when date is opened',()=>{
  const r=auditAdmission({sessions:['2025-03-11'],precommittedSessions:['2025-03-11'],baselineClass:'CURRENT_FROZEN_P21_BASELINE'});
  assert.ok(r.blockers.includes('CURRENT_P21_HISTORY_OUTSIDE_CAUSAL_WINDOW'));
});
test('protected dates cannot be authorized by development flag',()=>{
  const r=auditAdmission({sessions:['2026-09-01'],precommittedSessions:['2026-09-01'],protectedSessions:['2026-09-01']});
  assert.ok(r.blockers.includes('SESSION_NOT_RELEASED'));
});
test('reconstructed P21 is explicitly a different contract',()=>assert.ok(auditAdmission({baselineClass:'HISTORICALLY_RECONSTRUCTED_P21_METHODOLOGY'}).blockers.includes('DIFFERENT_BASELINE_CLASS_REQUIRES_SEPARATE_CONTRACT')));
test('fake model or freeze is rejected',()=>assert.throws(()=>verifyFreeze({modelDigest:'fake'},{freezeSha256:'fake'}),/MISMATCH/));
test('precommit never represents helper tests as baseline performance',()=>{
  const c=JSON.parse(fs.readFileSync(new URL('../../predict/research/phase57-hybrid-p21-entry-baseline-precommit.json',import.meta.url),'utf8'));
  assert.equal(c.results.measurementPerformed,false);assert.equal(c.results.selectionEvents,null);assert.equal(c.results.pitViolations,null);
  assert.equal(c.allocation.sessions.length,17);assert.ok(c.allocation.sessions.includes('2026-08-14'));
  assert.equal(c.allocation.sealedReleaseAllowed,false);assert.equal(c.allocation.modelFittingAllowed,false);
  assert.equal(c.allocation.protectedNonPurgeSessions,190);assert.equal(c.cost.entryOutcomeRoundTripCostBps,null);
  assert.equal(auditAdmission({...c.allocation,baselineClass:c.baseline.baselineClass,precommittedSessions:c.allocation.sessions}).ready,false);
  assert.ok(Object.values(c.safety).every(x=>x===false));
});
