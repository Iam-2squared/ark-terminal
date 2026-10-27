import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {isoFriday, tradingGap, nextCashDate, nightlyWindow} from '../tools/no11_weekly_g1_refresh.mjs';

test('full universe is Friday and initial 2026-10-26 is only a manual seed',()=>{
  assert.equal(isoFriday('2026-10-30'),true);
  assert.equal(isoFriday('2026-10-26'),false);
  assert.equal(isoFriday('2026-10-27'),false);
});
test('JPX cash calendar honors holidays between Friday weekly sweep and daily pool refresh',()=>{
  assert.equal(nextCashDate('2026-10-30'),'2026-11-02');
  assert.equal(nextCashDate('2026-11-02'),'2026-11-04');
  assert.equal(tradingGap('2026-10-30','2026-11-02'),1);
  assert.equal(tradingGap('2026-10-30','2026-11-05'),3);
  assert.equal(tradingGap('2026-10-26','2026-10-29'),3);
  assert.throws(()=>tradingGap('2026-10-30','2026-10-30'),/NO11_WEEKLY_TRADING_DATES_INVALID/);
  assert.throws(()=>tradingGap('2026-10-30','2026-10-29'),/NO11_WEEKLY_TRADING_DATES_INVALID/);
});
test('weekday refresh demands genuinely observed D100 sources and records limited-universe lineage',()=>{
  const src=fs.readFileSync(new URL('../tools/no11_weekly_g1_refresh.mjs',import.meta.url),'utf8');
  for(const marker of [
    'FULL_WEEKLY_SWEEP_NOT_COMPLETE','codeSha256===codeIdentity()',
    'FULL_MARKET_FRIDAY','CURRENT_COMPLETED_CASH_SESSION_REQUIRED',
    'FRIDAY_FULL_MARKET_SWEEP_REQUIRED','WEEKLY_POOL_EXPIRED_FULL_SWEEP_REQUIRED',
    'loadCaptures(run,plan)','summarizeDailyCaptures(plan,captures)',
    'makeObservedPassWatchMask(plan,captures)',
    'rankVerifiedG1PassForChartBudget(plan,captures,mask)',
    'mask.newBreakoutsOutsideWeeklyPoolNotScanned=true;',
    'unknownNotAdmitted:true',
    'productionReady:false','orderTransmission:false'
  ])assert.ok(src.includes(marker),marker);
  assert.doesNotMatch(src,/RssStockOrder\s*\(|RssCancelOrder\s*\(/);
});
test('after-close runner selects full Friday or limited weekly candidates and never enables orders',()=>{
  const src=fs.readFileSync(new URL('../windows/Prepare-No11WeeklyAfterCloseReadOnly.ps1',import.meta.url),'utf8');
  const refresh=fs.readFileSync(new URL('../windows/Run-No11WeeklyCandidateRefreshReadOnly.ps1',import.meta.url),'utf8');
  for(const mark of ['FULL_MARKET_FRIDAY','WEEKLY_POOL_CANDIDATES_ONLY',
    'Prepare-No11NextSessionNightlyReadOnly.ps1','Run-No11WeeklyCandidateRefreshReadOnly.ps1',
    'Prepare-No11PreviousArchiveReadOnly.ps1','NO11_WEEKLY_NIGHTLY_OFFLINE_SELFTEST=PASS',
    'NO11_WEEKLY_NIGHTLY_NEW_BREAKOUTS_OUTSIDE_POOL=NOT_SCANNED',
    'ORDER_TRANSMISSION=False'])
    assert.ok(src.includes(mark),mark);
  assert.ok(refresh.includes('RssChart($A$2:$J$2'));
  assert.ok(refresh.includes('ONLY_TWO_ORIGINAL_WORKBOOKS_REQUIRED'));
  assert.ok(refresh.includes('NO11_WEEKLY_DAILY_REFRESH=COMPLETE_NOT_FULL_UNIVERSE'));
  assert.ok(refresh.includes('Ark_No11_MARKET_RSS.xlsx'));
  assert.ok(refresh.includes('Ark_No11_MSII_RSS.xlsx'));
  for(const forbidden of [/RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,/Stop-Process/,/taskkill/,/git\s+pull/])
    assert.doesNotMatch(src,forbidden);
});

test('Oct27 evening and Oct28 early morning use the SAME ACTUAL OCT27 close without future data',()=>{
 const night=nightlyWindow('2026-10-27T23:15:00.000+09:00');
 assert.equal(night.date,'2026-10-27');
 assert.equal(night.followingPreopen,false);
 const early=nightlyWindow('2026-10-28T01:03:00.000+09:00');
 assert.equal(early.date,'2026-10-27');
 assert.equal(early.followingPreopen,true);
 const late=nightlyWindow('2026-10-28T08:29:59.000+09:00');
 assert.equal(late.date,'2026-10-27');
 assert.throws(()=>nightlyWindow('2026-10-28T08:30:00.000+09:00'),
  /NO11_WEEKLY_CURRENT_COMPLETED_CASH_SESSION_REQUIRED/);
 assert.throws(()=>nightlyWindow('2026-10-27T17:59:00.000+09:00'),
  /NO11_WEEKLY_CURRENT_COMPLETED_CASH_SESSION_REQUIRED/);
 assert.throws(()=>nightlyWindow('2026-10-28T09:00:00.000+09:00'),
  /NO11_WEEKLY_CURRENT_COMPLETED_CASH_SESSION_REQUIRED/);
 assert.throws(()=>nightlyWindow('2026-11-02T07:55:00.000+09:00'),
  /NO11_WEEKLY_CURRENT_COMPLETED_CASH_SESSION_REQUIRED/); // Friday full sweep only
});
