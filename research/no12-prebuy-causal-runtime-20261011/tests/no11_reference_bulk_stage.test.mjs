import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const file=fileURLToPath(new URL('../windows/Stage-No11ReferenceBulkReadReadOnly.ps1',import.meta.url));
const source=readFileSync(file,'utf8');

test('safe one-time current-session RSS reference speed repair has exact old and new SHA pins',()=>{
 for(const marker of [
  'Capture-No11SessionReferenceReadOnly.ps1',
  'Run-No11Oct28AfternoonShadowReadOnly.ps1',
  '94b13a2589b0e2c23d97c8e5c425f3e13581a23f',
  '26d2a79c912d4bfd2422bcb82562004794b50487',
  'b73141c81c31b5493aaee5df0dbca019429c930f',
  'c1d8514fa17b8169576427403dd687acbf62b5f5',
  'PatchKnownLegacyParent',
  'LEGACY_PARENT_EXACT_ANCHOR_REQUIRED',
  'LEGACY_PARENT_SAFETY_ANCHORS_MISSING',
  'LEGACY_PARENT_PATCH_SCOPE_CHANGED',
  'NO11_REFERENCE_BULK_LEGACY_PARENT=EXACT_ONE_ANCHOR_PATCHED_OTHER_TEXT_PRESERVED',
  'NO11_REFERENCE_BULK_LOCAL_PARENT_CHANGES=PINNED_LEGACY_PRESERVED',
  '$finalHashes[$original]=$expected',
  'b253086835cf76ab6bfe0fbe9f7f4c0c3cc36b74',
  'PARENT_OR_CHILD_RUNNING_STOP_ORIGINAL_FIRST',
  'LOCAL_FILE_DIFFERENT_NO_OVERWRITE',
  'DOWNLOADED_SHA_MISMATCH',
  'POWERSHELL_PARSE_ERRORS',
  'COLLECTOR_OFFLINE_SELFTEST_FAILED',
  'NO11_REFERENCE_BULK_FORMULA_MODE=PER_SHEET_BULK_READ',
  'NO11_REFERENCE_BULK_DIAGNOSTICS=LIVE_CHILD_STAGES',
  'NO11_REFERENCE_BULK_PREVIOUS_ARCHIVE_TOUCHED=False',
  'NO11_REFERENCE_BULK_EXCEL_TOUCHED=False',
  'ORDER_TRANSMISSION=False'
 ])assert.ok(source.includes(marker),marker);
 for(const bad of [/RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,
  /Stop-Process|\.Kill\s*\(/,/\.Save\s*\(|\.SaveAs\s*\(|pip\s+install/])
  assert.doesNotMatch(source,bad);
 assert.ok(source.includes('[IO.File]::Copy($applied[$i].backup,$applied[$i].from,$true)'));
});
test('Windows one-time repair selftest is completely offline',{skip:process.platform!=='win32'},()=>{
 const r=spawnSync('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass',
  '-File',file,'-OfflineSelfTest'],{encoding:'utf8',timeout:18000});
 assert.equal(r.status,0,(r.stdout||'')+'\n'+(r.stderr||''));
 assert.match(r.stdout,/NO11_REFERENCE_BULK_INSTALL_OFFLINE_SELFTEST=PASS/);
 assert.match(r.stdout,/ORDER_TRANSMISSION=False/);
});
