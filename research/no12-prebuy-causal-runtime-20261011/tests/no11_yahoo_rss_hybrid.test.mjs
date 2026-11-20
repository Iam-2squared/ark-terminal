import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {nightlyWindow,yahooFridayConfirmationWindow}
 from '../tools/no11_weekly_g1_refresh.mjs';

const weekly=fs.readFileSync(new URL('../tools/no11_weekly_g1_refresh.mjs',import.meta.url),'utf8');
const verification=fs.readFileSync(new URL('../tools/no11_verified_weekly_shadow_scope.mjs',import.meta.url),'utf8');
const after=fs.readFileSync(new URL('../windows/Prepare-No11WeeklyAfterCloseReadOnly.ps1',import.meta.url),'utf8');
const collector=fs.readFileSync(new URL('../windows/Run-No11WeeklyCandidateRefreshReadOnly.ps1',import.meta.url),'utf8');
const yahoo=fs.readFileSync(new URL('../windows/Run-No11YahooWeeklySeedReadOnly.ps1',import.meta.url),'utf8');

test('on Fridays, opt-in Yahoo 4328 seed is confirmed with real 429 RSS D100, not original 4328 scan',()=>{
 assert.equal(yahooFridayConfirmationWindow('2026-10-30T19:01:00.000+09:00').yahooFridayRssConfirmation,true);
 for(const clock of ['2026-10-30T18:59:59.000+09:00','2026-10-29T20:00:00.000+09:00',
  '2026-10-31T20:00:00.000+09:00']){
  assert.throws(()=>yahooFridayConfirmationWindow(clock),/NO11_WEEKLY_YAHOO_FRIDAY_RSS_CONFIRM_AFTER_1900_ONLY/);
 }
 assert.throws(()=>nightlyWindow('2026-10-28T09:00:00.000+09:00'),
  /NO11_WEEKLY_CURRENT_COMPLETED_CASH_SESSION_REQUIRED/);
 for(const value of ['--yahoo-friday-rss-confirm','FRIDAY_CONFIRM_REQUIRES_MATCHING_YAHOO_SEED',
  'YAHOO_FRIDAY_REAL_RSS_PLAN_CONTRACT','sourceWasYahooButDailyCandlesAreRss',
  'source.plan.sourceProvider===YAHOO_SOURCE','verifyYahooWeeklySeed(run)'])
  assert.ok(weekly.includes(value),value);
 assert.ok(collector.includes('[switch]$ConfirmYahooFridayRss'));
 assert.ok(after.includes('-ConfirmYahooFridayRss'));
 for(const m of ['NO11_WEEKLY_NIGHTLY_FRIDAY_FULL_RSS_SCAN=SKIPPED_YAHOO_SOURCE_ONLY',
  'NO11_WEEKLY_NIGHTLY_FRIDAY_RSS_CONFIRMATION=429_CANDIDATES_ONLY',
  'NO11_WEEKLY_NIGHTLY_STAGE=YAHOO_WEEKLY_AND_RSS_429_G1_PREVIOUS_COMPLETE'])
  assert.ok(after.includes(m),m);
});
test('Yahoo does not silently become default: default remains RSS and no missing-source RSS fallback',()=>{
 assert.ok(after.includes("[string]$WeeklySourcePolicy='RSS_FULL_FRIDAY'"));
 assert.ok(after.includes("'YAHOO_WEEKLY_SOURCE_NOT_READY_NO_RSS_FALLBACK'"));
 assert.ok(after.includes("if($mode -ceq 'FULL_MARKET_FRIDAY')"));
 assert.ok(after.includes("NO11_WEEKLY_NIGHTLY_STAGE=CANDIDATE_ONLY_FRESH_G1_AND_PREVIOUS_COMPLETE"));
 assert.ok(after.includes("NO11_WEEKLY_NIGHTLY_MODE="));
});
test('Shadow requires same Friday source, actual D100 captured RSS, Yahoo remains provisional',()=>{
 for(const marker of ['verifyWeeklySource(seed)','weekly.plan.sourceProvider===YAHOO_SOURCE',
  'sourceWasYahooButDailyCandlesAreRss===true',
  'loadCaptures(run,plan)','summarizeDailyCaptures(plan,observed)',
  'CURRENT_MASK_NOT_DERIVED_FROM_OBSERVED_CAPTURE',
  'YAHOO_WEEKLY_UNOFFICIAL_PLUS_REAL_DAILY_RSS_NOT_PRICE_CERTIFIED',
  'fullShadowPreflightPassed:false','orderTransmission:false'])
  assert.ok(verification.includes(marker),marker);
});
test('unofficial Yahoo fetch will not run without explicit Yahoo prior permission',()=>{
 for(const marker of [
  'EXPRESS_YAHOO_AUTOMATED_PERMISSION_REQUIRED',
  'YahooAutomatedAccessPermissionConfirmed',
  'PersonalResearchTermsAcknowledged',
  'yahoo-isolated-venv',
  'YAHOO_MUST_NOT_USE_FROZEN_MODEL_VENV',
  'NO11_YAHOO_WEEKLY_TRADE_AUTHORIZED=False','ORDER_TRANSMISSION=False'])
  assert.ok(yahoo.includes(marker),marker);
 for(const code of [weekly,after,yahoo,verification]){
  for(const forbidden of [/RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,
    /orderTransmission\s*[=:]\s*(?:\$true|true)/,/Stop-Process/])
   assert.doesNotMatch(code,forbidden);
 }
});
