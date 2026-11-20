/** No11 2026-10-28 nightly handoff static safety regression. */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const read=n=>fs.readFileSync(new URL('../windows/'+n,import.meta.url),'utf8');
const weekly=read('Prepare-No11WeeklyAfterCloseReadOnly.ps1');
const previous=read('Prepare-No11PreviousArchiveReadOnly.ps1');
const source=read('Run-No11WeeklyCandidateRefreshReadOnly.ps1');
test('Wednesday Oct28 uses Tuesday Oct27 close; no erroneous Friday full symbols prerequisite',()=>{
 const fullBranch=weekly.indexOf("if($mode -ceq 'FULL_MARKET_FRIDAY')");
 const fullCheck=weekly.indexOf("'FULL_SYMBOL_LIST_MISSING'");
 assert.ok(fullBranch>0&&fullCheck>fullBranch,'Friday-only full symbol file');
 assert.ok(weekly.includes("'WEEKLY_POOL_CANDIDATES_ONLY'"));
 assert.ok(source.includes('Get-Plan'));
 assert.ok(source.includes('NO11_DAILY_RESUME_VERIFIED='));
 assert.ok(weekly.includes('NO11_WEEKLY_NIGHTLY_CURRENT_MASK='));
 assert.ok(weekly.includes('NO11_WEEKLY_NIGHTLY_CURRENT_CHART50='));
});
test('weekday current chart plan and mask are forwarded to original previous-archive importer',()=>{
 const precomputedIndex=weekly.indexOf("'-PrecomputedChartPlanFile',$weeklyChart");
 const finishIndex=weekly.indexOf("Need ($LASTEXITCODE -eq 0) 'SELECTED_PREVIOUS_1M_FAILED'");
 assert.ok(precomputedIndex>0&&finishIndex>precomputedIndex);
 for(const marker of [
  "NO11_WEEKLY_REFRESH_MASK=","NO11_WEEKLY_REFRESH_CHART50=",
  "('report','--run',[string]$result.run,'--weekly-run',$WeeklyRun)",
  "'-PrecomputedMaskFile',$weeklyMask",
  "'-PrecomputedChartPlanFile',$weeklyChart",
 ])assert.ok(weekly.includes(marker),marker);
 for(const marker of [
  "[string]$PrecomputedChartPlanFile", "[string]$PrecomputedMaskFile",
  "NO11_PREVIOUS_PRECOMPUTED_BOTH_RECEIPTS_REQUIRED",
  "NO11_PREVIOUS_PRECOMPUTED_PRIVATE_FILE_INVALID",
  "NO11_PREVIOUS_PRECOMPUTED_WRONG_SOURCE_RUN",
  "NO11_PREVIOUS_INPUT_SCOPE=WEEKLY_PINNED_RECEIPTS_VALIDATION_REQUIRED",
  "--symbols-only"
 ])assert.ok(previous.includes(marker),marker);
 const scopeIndex=previous.indexOf('--symbols-only');
 const collectIndex=previous.indexOf("CaptureArguments $symbols $PrivateRoot");
 assert.ok(scopeIndex<collectIndex,'original scope validated before Excel collector');
});
test('no fake review, no order transmission, no model fit or broker side effects',()=>{
 for(const src of [weekly,previous,source]){
  assert.doesNotMatch(src,/(?:RssStockOrder|RssMarginOpenOrder|RssCancelOrder)\s*\(/);
  assert.doesNotMatch(src,/productionReady=\$true|orderTransmission=\$true/);
  assert.doesNotMatch(src,/EXTERNALLY_REVIEWED/);
  assert.ok(src.includes("ORDER_TRANSMISSION=False"));
 }
});
