import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const base=new URL('../windows/',import.meta.url);
const ps=name=>fs.readFileSync(new URL(name,base),'utf8');
test('one desktop launcher routes full MAX3 normal cash mode and actual Friday weekly weekend source',()=>{
 const source=ps('Start-No11UnifiedLauncher.ps1');
 for(const marker of [
  "Run-No11ReceivedSessionOperatorLive.ps1",
  "Prepare-No11WeeklyAfterCloseReadOnly.ps1",
  "IApproveOrdersForToday",
  "normalMaxPositions=3",
  "sameDayApprovalRequired",
  "automaticOrderAuthorization=$false",
  "orderTransmission=$false",
  "CheckExcel $cfg $true",
  "CheckExcel $cfg $false",
  "if($weekend){$arguments+=@('-WeekendFriday')}",
  "StartChild 'TRADE'",
  "StartChild 'WEEKLY'",
  "WEEKLY_REAL_ASOF_FRIDAY",
  "STOP_NEW_ENTRIES_REQUESTED",
  "NO11_UNIFIED_BROKER_ORDER_CANCELLED=False",
  "No.1.1"
 ]) {
  assert.ok(source.includes(marker),marker);
 }
 assert.doesNotMatch(source,/RssStockOrder\s*\(/i);
 assert.doesNotMatch(source,/RssCancelOrder\s*\(/i);
 assert.doesNotMatch(source,/Stop-Process|taskkill|git\s+(?:reset|clean|checkout)/i);
});
test('desktop setup creates separate icon and never modifies legacy read-only icons',()=>{
 const install=ps('Install-No11UnifiedDesktopShortcut.ps1');
 const bootstrap=ps('Install-No11UnifiedFromGitReadOnly.ps1');
 assert.ok(install.includes('Ark Terminal No11 Normal + Weekly.lnk'));
 assert.ok(install.includes("WScript.Shell"));
 assert.ok(install.includes('FOREIGN_DESKTOP_SHORTCUT_WONT_OVERWRITE'));
 assert.ok(bootstrap.includes('worktree add --detach'));
 assert.ok(bootstrap.includes('NO_SOURCE_RESET=True'));
 assert.ok(bootstrap.includes('NO11_UNIFIED_GIT_INSTALL_FAILURE_STAGE='));
 assert.doesNotMatch(bootstrap,/git\s+(?:pull|reset|clean)/i);
 assert.doesNotMatch(bootstrap,/RssStockOrder\s*\(/i);
});
test('weekend source uses observed Friday history only and requires RSS connection',()=>{
 const scheduler=fs.readFileSync(new URL('../tools/no11_weekly_g1_refresh.mjs',import.meta.url),'utf8');
 const orchestrator=ps('Prepare-No11WeeklyAfterCloseReadOnly.ps1');
 const friday=ps('Prepare-No11NextSessionNightlyReadOnly.ps1');
 assert.ok(scheduler.includes('WEEKEND_FRIDAY_MODE_SAT_SUN_ONLY'));
 assert.ok(scheduler.includes('vendorRssConnectionStillRequired:true'));
 assert.ok(orchestrator.includes("if($WeekendFriday){$arguments+=@('-WeekendFriday')}"));
 assert.ok(friday.includes("ACTUAL_PRIOR_FRIDAY_REQUIRED"));
 assert.ok(friday.includes("WEEKEND_RSS_NOT_GUARANTEED=True"));
 assert.doesNotMatch(orchestrator,/RssStockOrder\s*\(/i);
});