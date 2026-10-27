import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {verifyWeeklyShadowScope} from '../tools/no11_verified_weekly_shadow_scope.mjs';
const code=fs.readFileSync(new URL('../tools/no11_verified_weekly_shadow_scope.mjs',import.meta.url),'utf8');
test('original weekly seeded daily refresh must have genuine complete source and real next-session chart receipts',()=>{
 for(const must of [
  'verifyWeeklyPool(seed)','tradingGap(weekly.plan.asOfSession,asOf)',
  'loadCaptures(run,plan)','summarizeDailyCaptures(plan,observed)',
  'makeObservedPassWatchMask(plan,observed)',
  'validateNo11Chart50Plan({chartPlan:chart.chartPlan,mask,sessionDate})',
  'plan.codeSha256===codeIdentity()','sourceManifestSha256===sha(JSON.stringify(sourceNames))',
  'mask.weeklyOriginalAsOfSession===weekly.plan.asOfSession',
  'plan.weeklySource?.originalPlanId===weekly.plan.planId',
  'currentRefreshAsOfSession===asOf',
  'NO11_WEEKLY_SHADOW_SCOPE=PASS_OBSERVED_NOT_EXTERNALLY_REVIEWED'
 ])assert.ok(code.includes(must),must);
});
test('works without nighttime-only calendar, while never promoting external evidence',()=>{
 assert.doesNotMatch(code,/nightlyWindow|currentAsOf\(\)|RssStockOrder\s*\(/);
 for(const marker of ['externalReviewCertified:false','fullShadowPreflightPassed:false',
   'orderTransmission:false','NO11_WEEKLY_SHADOW_FULL_PREFLIGHT=NOT_PASSED'])
  assert.ok(code.includes(marker));
 assert.throws(()=>verifyWeeklyShadowScope({}),/NO11_WEEKLY_SHADOW_ABSOLUTE_SOURCE_REQUIRED/);
});
