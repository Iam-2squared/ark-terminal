import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
const file=new URL('../windows/Run-No11Oct29ReferenceOneShotReadOnly.ps1',import.meta.url);
const script=fs.readFileSync(file,'utf8');
test('2026-10-29 one-shot reads only the true 28th G1 mask and chart',()=>{
 for(const marker of [
  "if($date -cne '2026-10-29')",
  "currentRefreshAsOfSession -cne '2026-10-28'",
  "weeklyOriginalAsOfSession -cne '2026-10-26'",
  "chartPlan.asOfSession -cne '2026-10-28'",
  "chartPlan.sessionDate -cne $date",
  "NO11_ONESHOT_OCT29_REFRESH_RUN_IDENTITY_MISMATCH",
  "no11_previous_archive_context.py","--symbols-only",
  "Capture-No11SessionReferenceReadOnly.ps1",
  "no11_reference_fields_diagnostic.mjs",
  "NO11_ONESHOT_INTEGRATED_SHADOW=BLOCKED_UNTIL_REAL_EXTERNAL_REVIEW"
 ])assert.ok(script.includes(marker),marker);
});
test('one-shot refuses original stale Oct27 hard-coded plan, preserves originals, no order or model runs',()=>{
 assert.doesNotMatch(script,/session-reference\\2026-10-27|daily-2026-10-26|no11_review_queue_from_actual_rss/);
 for(const r of [
  /(?:RssStockOrder|RssCancelOrder|RssMarginOpenOrder)\s*\(/,
  /(?:\.SaveAs|\.Save|\.Quit)\s*\(/,
  /(?:Stop-Process|\.Kill)\s*\(/,
  /reviewStatus\s*=\s*['"]EXTERNALLY_REVIEWED/
 ])assert.doesNotMatch(script,r);
 assert.ok(script.includes("ORDER_TRANSMISSION=False"));
});
test('Windows Oct29 wrapper parses and runs collector offline only', {skip:process.platform!=='win32'},()=>{
 const r=spawnSync('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass',
  '-File',decodeURIComponent(file.pathname.replace(/^\//,'')),'-OfflineSelfTest'],
  {encoding:'utf8',timeout:30000});
 assert.equal(r.status,0,(r.stdout||'')+'\n'+(r.stderr||''));
 assert.match(r.stdout,/NO11_ONESHOT_OFFLINE_SELFTEST=PASS/);
 assert.match(r.stdout,/ORDER_TRANSMISSION=False/);
});
