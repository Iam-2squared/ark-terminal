import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {inspect} from '../tools/no11_oct29_preopen_doctor.mjs';
const src=fs.readFileSync(new URL('../tools/no11_oct29_preopen_doctor.mjs',import.meta.url),'utf8');
test('29th uses actual 28th G1, not the 26th seed as a fresh day',()=>{
 for(const needle of [
  "PREV='2026-10-28',TARGET='2026-10-29',SEED='2026-10-26'",
  "verifyWeeklyPool(path.join(local,SEED_DIR))",
  "weekly-refresh-2026-10-28-",
  "p.asOfSession===PREV",
  "p.weeklySource?.originalPlanId===seed.plan.planId",
  "JSON.stringify(p.expectedSessions)===JSON.stringify(requiredDailySessions(PREV))",
  "observed.length!==p.symbols.length",
  "validateNo11Chart50Plan({chartPlan:c.chartPlan,mask:m,sessionDate:TARGET})",
  "OCT28_FRESH_G1_POOL","OCT29_CHART50_MASK"
 ])assert.ok(src.includes(needle),needle);
});
test('29th requires 28th previous minute staging and independent same day review',()=>{
 for(const needle of [
  "previous-source',TARGET","stage.sessionDate===TARGET","stage.previousSession===PREV",
  "stage.chartPlanSha256===","OCT28_PREVIOUS_1M_FOR_OCT29",
  "OCT29_SAME_DAY_RSS_REFERENCE","OCT29_EXTERNAL_SECURITY_AND_PRICE_BASIS_REVIEW",
  "OCT29_ACCOUNT_PINS_AND_SIM_ACCOUNT_RECONCILIATION",
  "OCT29_SAME_DAY_MASTER_AND_PREVIOUS_CONTEXT","OCT29_ORIGINAL_INTEGRATED_PREFLIGHT",
  "NO11_OCT29_FULL_SHADOW=NOT_YET_AUTHORIZED",
  "auditReference(saved.data,PREV)","PREVIOUS_REFERENCE_HASH_MISMATCH"
 ])assert.ok(src.includes(needle),needle);
});
test('Oct29 audit only - never starts Excel, orders or review promotion',()=>{
 assert.throws(()=>inspect([]),/NO11_OCT29_DOCTOR_USAGE/);
 for(const x of [
  /(?:writeFileSync|mkdirSync|renameSync|unlinkSync|execSync|spawnSync)\s*\(/,
  /\bGetActiveObject\b|\bExcel.Application\b|\bWorkbooks\b/,
  /(?:RssStockOrder|RssCancelOrder|RssMarginOpenOrder)\s*\(/,
  /reviewStatus\s*:\s*['"]EXTERNALLY_REVIEWED/,
  /orderTransmission\s*:\s*true/
 ])assert.doesNotMatch(src,x);
});
