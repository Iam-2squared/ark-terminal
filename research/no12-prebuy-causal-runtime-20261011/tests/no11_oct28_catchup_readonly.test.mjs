import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {daytimeCatchUpWindow,nightlyWindow} from '../tools/no11_weekly_g1_catchup_20261028.mjs';

const code=fs.readFileSync(new URL('../tools/no11_weekly_g1_catchup_20261028.mjs',import.meta.url),'utf8');
const collector=fileURLToPath(new URL('../windows/Run-No11WeeklyCandidateCatchUpReadOnly.ps1',import.meta.url));
const runner=fileURLToPath(new URL('../windows/Run-No11Oct28CatchUpReadOnly.ps1',import.meta.url));
const source=fs.readFileSync(collector,'utf8');
const launch=fs.readFileSync(runner,'utf8');

test('Oct28 explicit catch-up accepts ONLY Oct27 last completed JPX cash day',()=>{
 const actual=daytimeCatchUpWindow('2026-10-28T09:00:01.000+09:00','2026-10-27');
 assert.equal(actual.date,'2026-10-27');
 assert.equal(actual.now,'2026-10-28T09:00:01.000+09:00');
 assert.equal(actual.daytimeHistoricalRecovery,true);
 for(const [now,asOf] of [
  ['2026-10-28T08:29:59.000+09:00','2026-10-27'],
  ['2026-10-28T18:00:00.000+09:00','2026-10-27'],
  ['2026-10-28T11:00:00.000+09:00','2026-10-26'],
  ['2026-10-27T19:00:00.000+09:00','2026-10-27'],
  ['2026-10-29T09:00:00.000+09:00','2026-10-27'],
  ['2026-11-02T09:00:00.000+09:00','2026-10-30']
 ])assert.throws(()=>daytimeCatchUpWindow(now,asOf),/CATCHUP_REQUIRES_ACTUAL_PREVIOUS_CASH_DAY/);
});
test('unchanged nightly window still fails at Oct28 08:30 (cannot silently switch modes)',()=>{
 assert.equal(nightlyWindow('2026-10-28T08:29:59.000+09:00').date,'2026-10-27');
 assert.throws(()=>nightlyWindow('2026-10-28T09:00:00.000+09:00'),/CURRENT_COMPLETED_CASH_SESSION_REQUIRED/);
});
test('catch-up plan preserves actual receipt date and excludes later partial bar',()=>{
 for(const m of [
  'createdAtJst:now','daytimeHistoricalRecovery=true;',
  'body.recoveryObservedCalendarDay=now.slice(0,10)',
  'body.historicalAsOfSession=date',
  'body.futurePartialBarsExcludedFromG1=true',
  'plan.createdAtJst.slice(0,10)===plan.recoveryObservedCalendarDay',
  'mask.futurePartialBarsExcludedFromG1=true',
  'NO11_WEEKLY_REFRESH_DAYTIME_CATCHUP=',
  'loadCaptures(run,plan)',
  'summarizeDailyCaptures(plan,captures)',
  'rankVerifiedG1PassForChartBudget(plan,captures,mask)'
 ])assert.ok(code.includes(m),m);
 const sourceInspector=fs.readFileSync(new URL('../runtime/no11_rss_daily_trend_census.mjs',import.meta.url),'utf8');
 assert.match(sourceInspector,/if \(row\.session > plan\.asOfSession\) \{ ignoredLaterRows\+\+; continue; \}/);
 assert.doesNotMatch(code,/(?:RssStockOrder|RssCancelOrder|RssMarginOpenOrder)\s*\(/);
});
test('new collector is separate from original and invokes only explicit opt-in recovery',()=>{
 assert.ok(source.includes("'tools\\no11_weekly_g1_catchup_20261028.mjs'"));
 assert.ok(source.includes('[string]$CatchUpAsOf'));
 assert.ok(source.includes("'--catch-up-asof',$CatchUpAsOf"));
 assert.ok(source.includes('ONLY_TWO_ORIGINAL_WORKBOOKS_REQUIRED'));
 assert.ok(source.includes('RssChart($A$2:$J$2'));
 assert.ok(source.includes('NO11_WEEKLY_DAILY_CAPTURE=HISTORICAL_ASOF_WITH_REAL_CURRENT_RECEIPT'));
 for(const forbidden of [/RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,/Stop-Process|taskkill/])assert.doesNotMatch(source,forbidden);
});
test('an all-empty real RSS wave gets only bounded same-formula retries, never a fake capture',()=>{
 assert.ok(source.includes('$emptyRetry=0'));
 assert.ok(source.includes('$emptyRetry -ge 2'));
 assert.ok(source.includes('NO11_DAILY_EMPTY_WAVE_RETRY='));
 assert.ok(source.includes('NO11_DAILY_EMPTY_WAVE_EXHAUSTED=NO_CAPTURE_WRITTEN'));
 const bad=source.indexOf('if($usable -eq 0){');
 const save=source.indexOf('foreach($payload in $payloads){Save-Capture');
 assert.ok(bad>0 && save>bad,'must refuse empty wave before saving any payload');
 assert.ok(source.includes('NO11_DAILY_ALL_EMPTY_WAVE_RETRY_AFTER_RECONNECT'));
 assert.doesNotMatch(source,/if\(\$usable -eq 0\)\{\s*\$usable\+\+/);
});
test('one-shot uses exactly original 429, real 27-asof and previous 1M with strict verification',()=>{
 for(const marker of [
  'daily-2026-10-26-e84a2ec53b0fdf41',
  'NO11_OCT28_CATCHUP_RECEIPT_DAY=2026-10-28',
  'NO11_OCT28_CATCHUP_FUTURE_2026_10_28_BARS=EXCLUDED_FROM_G1',
  '--catch-up-asof','2026-10-27',
  '@($job.plan.symbols).Count -eq 429',
  'Run-No11WeeklyCandidateCatchUpReadOnly.ps1',
  'no11_verified_weekly_shadow_scope.mjs',
  'NO11_WEEKLY_SHADOW_SCOPE=PASS_OBSERVED_NOT_EXTERNALLY_REVIEWED',
  'Prepare-No11PreviousArchiveReadOnly.ps1',
  'NO11_OCT28_CATCHUP_INDEPENDENT_REVIEW=STILL_REQUIRED',
  'NO11_OCT28_CATCHUP=REAL_RSS_SOURCE_STAGED_NOT_SHADOW_AUTHORIZED'
 ])assert.ok(launch.includes(marker),marker);
 assert.doesNotMatch(launch,/(?:RssStockOrder|RssCancelOrder)\s*\(|Start-Process|Stop-Process/);
});
test('Windows offline selftest of all new scripts', {skip:process.platform!=='win32'},()=>{
 for(const file of [collector,runner]){
  const p=spawnSync('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass','-File',file,
   '-OfflineSelfTest'],{encoding:'utf8',timeout:25000});
  assert.equal(p.status,0,(p.stdout||'')+'\n'+(p.stderr||''));
  assert.match(p.stdout,/ORDER_TRANSMISSION=False/);
 }
});
