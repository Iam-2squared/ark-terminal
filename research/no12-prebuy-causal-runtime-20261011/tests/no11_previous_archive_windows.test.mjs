import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';

const base=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const script=path.join(base,'windows/Prepare-No11PreviousArchiveReadOnly.ps1');
const source=fs.readFileSync(script,'utf8');

test('previous source wrapper reuses existing selected-scope exporter and collector',()=>{
 assert.match(source,/no11_export_chart50_prescreen\.mjs/);
 assert.match(source,/Capture-No11RssTrainingBatchReadOnly\.ps1/);
 assert.match(source,/no11_previous_archive_context\.py/);
 assert.match(source,/'-Bars','3000','-Period','1M'/);
 assert.match(source,/if\(\[string\]::IsNullOrWhiteSpace\(\$CaptureDir\)\)/);
 assert.doesNotMatch(source,/RssStockOrder\s*\(|RssCancelOrder\s*\(|\.Workbooks\.Add\(|\.SaveAs\(|\.Quit\(|Stop-Process|taskkill|RegisterXLL/i);
 assert.ok([...source].every(c=>c.charCodeAt(0)<128));
});

test('adapter retains uncertified evidence and uses the existing previous-context gate',()=>{
 const py=fs.readFileSync(path.join(base,'tools/no11_previous_archive_context.py'),'utf8');
 assert.match(py,/ARCHIVE_BYTES_CHANGED/);
 assert.match(py,/FINAL_CONTEXT_REQUIRES_ACTUAL_SESSION_DAY/);
 assert.match(py,/bootstrap\.previous_coverage/);
 assert.match(py,/bootstrap\.validate_scope/);
 assert.match(py,/'previousVaGenerated': False/);
 assert.doesNotMatch(py,/requests\.|urllib\.|\.fit\(|productionReady['"]?\s*:\s*True/);
});

test('Windows previous-source entrypoint offline self-test does not open Excel',
 {skip:process.platform!=='win32'},()=>{
 const r=spawnSync('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass','-File',script,'-OfflineSelfTest'],
   {encoding:'utf8',timeout:20000});
 assert.equal(r.status,0,r.stderr+'\n'+r.stdout);
 assert.match(r.stdout,/NO11_PREVIOUS_PREPARE_OFFLINE_SELFTEST=PASS/);
 assert.match(r.stdout,/EXCEL_STARTED=False/);
 assert.match(r.stdout,/ORDER_TRANSMISSION=False/);
});
