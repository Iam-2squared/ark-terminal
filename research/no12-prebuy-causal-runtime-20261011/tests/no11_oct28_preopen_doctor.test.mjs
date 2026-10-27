import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {inspect} from '../tools/no11_oct28_preopen_doctor.mjs';

const code=fs.readFileSync(new URL('../tools/no11_oct28_preopen_doctor.mjs',import.meta.url),'utf8');

test('2026-10-28 is NOT allowed to reuse October 26 seed as fresh daily G1',()=>{
 for(const marker of [
  "PREV='2026-10-27',TARGET='2026-10-28',SEED='2026-10-26'",
  "verifyWeeklyPool(path.join(local,SEED_DIR))",
  "p.asOfSession===PREV",
  "p.weeklySource?.asOfSession===SEED",
  "p.weeklySource?.originalPlanId===seed.plan.planId",
  "JSON.stringify(p.expectedSessions)===JSON.stringify(requiredDailySessions(PREV))",
  "observed.length!==p.symbols.length",
  "fresh.observedPassCount",
  "validateNo11Chart50Plan({chartPlan:c.chartPlan,mask:m,sessionDate:TARGET})",
  "stage.previousSession===PREV",
  "NO11_OCT28_FULL_SHADOW=NOT_YET_AUTHORIZED"
 ])assert.ok(code.includes(marker),marker);
});
test('reported 47 reference diagnostics distinguish RSS fields from independent corporate action review',()=>{
 for(const marker of [
  "marketCodeT:","marketDateOct27:","previousDateOct26:",
  "previousClosePositive:","dayBasePricePositive:","segmentRecognized:",
  "lotShares100:","externalCorporateReview:false",
  "OCT28_EXTERNAL_SECURITY_AND_PRICE_BASIS_REVIEW",
  "OCT28_ACCOUNT_PINS_AND_SIM_ACCOUNT_RECONCILIATION",
  "OCT28_SAME_DAY_MASTER_AND_PREVIOUS_CONTEXT",
  "OCT28_ORIGINAL_INTEGRATED_PREFLIGHT",
  "orderTransmission:false"
 ])assert.ok(code.includes(marker),marker);
});
test('audit does not mutate Excel or source nor authorize orders',async()=>{
 assert.throws(()=>inspect([]),/NO11_OCT28_DOCTOR_USAGE/);
 for(const pattern of [
  /\bGetActiveObject\b|\bExcel.Application\b|\bWorkbooks\b/,
  /(?:RssStockOrder|RssMarginOpenOrder|RssCancelOrder)\s*\(/,
  /(?:writeFileSync|mkdirSync|renameSync|unlinkSync|spawnSync|execSync)\s*\(/,
  /EXTERNALLY_REVIEWED/
 ])assert.doesNotMatch(code,pattern);
});
