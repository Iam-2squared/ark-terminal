import test from 'node:test';
import assert from 'node:assert/strict';
import {carryWindow,holidayCompletedSessionWindow}
  from './no11_weekly_g1_refresh.mjs';

// All tests are pure calendar/policy checks. NO Excel, RSS, account or order I/O.
test('Nov2 Nov4 Nov5 Nov6 use exactly one carried Friday 429 week',()=>{
  for(const day of ['2026-11-02','2026-11-04','2026-11-05','2026-11-06'])
    assert.equal(carryWindow('2026-10-26','2026-10-30',day),true);
});
test('next Monday expires, a future weekly input is necessary',()=>{
  assert.throws(()=>carryWindow('2026-10-26','2026-10-30','2026-11-09'),
                /CARRY_ONLY_ONE_WEEK/);
});
test('Nov 3 is a cash market holiday, never a price session',()=>{
  assert.throws(()=>carryWindow('2026-10-26','2026-10-30','2026-11-03'),
                /CARRY_ONLY_ONE_WEEK/);
});
test('continuation cannot substitute an unverified source week',()=>{
  assert.throws(()=>carryWindow('2026-10-27','2026-10-30','2026-11-04'),
                /CARRY_ORIGINAL_WEEK/);
  assert.throws(()=>carryWindow('2026-10-26','2026-10-29','2026-11-04'),
                /CARRY_ORIGINAL_WEEK/);
});
test('Nov 3 holiday receipt targets actual Nov2 completed close',()=>{
  assert.deepEqual(holidayCompletedSessionWindow(
    '2026-11-03T20:01:00.000+09:00','2026-11-02'),{
     date:'2026-11-02',now:'2026-11-03T20:01:00.000+09:00',
     holidayHistoricalRecovery:true});
});
test('cannot retroactively relabel a Friday or a later day',()=>{
  for(const [now,day] of [
    ['2026-11-03T20:01:00.000+09:00','2026-10-30'],
    ['2026-11-04T08:00:00.000+09:00','2026-11-02'],
    ['2026-11-03T20:01:00.000+09:00','2026-11-04']
  ]) assert.throws(()=>holidayCompletedSessionWindow(now,day),
       /HOLIDAY_ONLY_REAL_NOV2_CLOSE/);
});
console.log('WEEK429_CARRY_CALENDAR_TEST=PASS_OFFLINE_ONLY');
console.log('ORDER_TRANSMISSION=False');
