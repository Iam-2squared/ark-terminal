import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const src=fs.readFileSync(new URL('../windows/Run-No12TuesdayReadOnly.ps1',import.meta.url),'utf8');
test('one-click Tuesday runner is UTF-8 BOM PowerShell 5.1 safe and defaults to no mode',()=>{
 assert.equal(src.charCodeAt(0),0xFEFF);
 assert.match(src,/NO12_RUNNER_SELECT_EXACTLY_ONE_MODE/);
 assert.match(src,/param\(\[switch\]\$OfflineSelfTest,\[switch\]\$PhysicalReadOnly\)/);
 assert.match(src,/NO12_TUESDAY_OFFLINE_SELFTEST_PASS=True/);
});
test('sequential only: 5M then 1M then RssMarket seconds, all READ ONLY',()=>{
 const five=src.indexOf("Invoke-No12Child -script $five -arguments @('-WaitSeconds'");
 const one=src.indexOf("Invoke-No12Child -script $one -arguments @('-WaitSeconds'");
 const seconds=src.indexOf("Invoke-No12Child -script $seconds -arguments @('-Samples'");
 assert(five>0&&one>five&&seconds>one);
 assert.match(src,/NO12_TUESDAY_MARKET_OBSERVATIONS_COMPLETE_READ_ONLY=True/);
 assert.match(src,/NO11_RSS_SECONDS_ASOF_STATUS=LOCAL_RSS_SECONDS_ASOF_MARKET_SOURCE_ONLY/);
});
test('physical runner is exclusive and refuses wrong branch or dirty tracked worktree',()=>{
 for(const x of ['NO12_RUNNER_WRONG_BRANCH_OR_DETACHED','NO12_RUNNER_DIRTY_TRACKED_WORKTREE',
  'NO12_RUNNER_DIRTY_STAGED_WORKTREE','FileShare]::None','tuesday-readonly-runner.lock',
  'NO12_RUNNER_CHILD_BLOCKED','NO12_RUNNER_CHILD_RECEIPT_NOT_VERIFIED'])
  assert(src.includes(x),x);
});
test('no broker orders, Excel writes, force-push, Safety reset or branch modification',()=>{
 for(const forbidden of [/RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,
  /Workbooks\.Open\(/,/Workbooks\.Add\(/,/Invoke-Expression/,
  /git\s+push/,/--force/,/killSwitchLatched\s*=\s*false/,
  /executionAllowed\s*=\s*true/,/productionReady\s*=\s*true/])
  assert.doesNotMatch(src,forbidden);
 assert.match(src,/ORDER_TRANSMISSION=False/);
 assert.match(src,/NO11_PRODUCTION_READY=False/);
});
