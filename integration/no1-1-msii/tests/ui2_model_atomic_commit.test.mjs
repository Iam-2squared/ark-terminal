import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const dir=new URL('../windows/',import.meta.url);
const caller=fs.readFileSync(new URL('Write-No11DesktopReadOnlyPreview.ps1',dir),'utf8');
const helper=fs.readFileSync(new URL('Set-No11UiReadModelAtomic.ps1',dir),'utf8');
const win=fs.readFileSync(new URL('Test-No11UiModelAtomicReplace.ps1',dir),'utf8');
test('UI2 MODEL_COMMIT delegates to a restricted atomic Windows writer',()=>{
 assert.match(caller,/Commit-No11UiReadModelAtomic -TemporaryPath \$tmp -DestinationPath \$target -PrivateRoot \$local/);
 assert.match(caller,/\. \$atomicHelper/);
 assert.doesNotMatch(caller,/\[IO\.File\]::Replace\(\$tmp,\$target,\$null\)/);
 assert.match(caller,/\$RefreshAuditStage='MODEL_COMMIT'/);
});
test('explicit backup, only local ui-read-model.json, no symlinks, no fallback',()=>{
 assert.match(helper,/\[IO\.File\]::Replace\(\$src,\$dest,\$backup\)/);
 assert.doesNotMatch(helper,/\[IO\.File\]::Replace\([^)]*\$null/);
 for(const marker of ['NO11_UI_MODEL_DESTINATION_NOT_APPROVED','ReparsePoint','NO11_UI_MODEL_SOURCE_MISSING_OR_COLLISION','ui-read-model.json'])assert.ok(helper.includes(marker),marker);
 assert.match(helper,/if \(\$replaced -and \[IO\.File\]::Exists\(\$backup\)\)/);
});
test('Windows 5.1 test covers first, repeated, bad path, missing source',()=>{
 for(const marker of ['NO11_UI_MODEL_FIRST_COMMIT_PASS=True','NO11_UI_MODEL_EXISTING_REPLACE_PASS=True','NO11_UI_MODEL_REPEATED_REFRESH_PASS=True','NO11_UI_MODEL_FOREIGN_FILE_PROTECTED=True','NO11_UI_MODEL_FAILURE_PRESERVES_PREVIOUS=True'])assert.ok(win.includes(marker),marker);
});
test('no broker/Excel/order or Safety mutation introduced',()=>{
 for(const body of [helper,win])for(const x of [/RssStockOrder\s*\(/i,/RssCancelOrder\s*\(/i,/explicitSafetyReset\s*\(/i,/[.]Formula\s*=/i,/Excel.Application/i])assert.doesNotMatch(body,x);
});
