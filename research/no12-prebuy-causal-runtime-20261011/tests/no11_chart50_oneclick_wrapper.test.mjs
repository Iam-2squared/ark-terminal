import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
const tool=path.resolve(path.dirname(fileURLToPath(import.meta.url)),
 '../windows/Run-No11Chart50ReadOnlyE2E.ps1');
const text=fs.readFileSync(tool,'utf8');
test('read-only E2E orchestrates private immutable captures to Va proxy, never orders',()=>{
 assert.match(text,/Probe-No11Chart50ContinuousReadOnly\.ps1/);
 assert.match(text,/no11_import_chart50_continuous_snapshot\.mjs/);
 assert.match(text,/NO11_C50_PRIVATE_FOLDER/);
 assert.match(text,/NO11_C50_PRIVATE_CHART_PLAN/);
 assert.match(text,/ORDER_TRANSMISSION=False/);
 assert.doesNotMatch(text,/RssStockOrder\s*\(|RssCancelOrder\s*\(|\.Save\s*\(|\.SaveAs\s*\(/);
 assert.ok([...text].every(x=>x.charCodeAt(0)<=127));
});
test('one-command wrapper Windows offline check can run without Excel',()=>{
 if(process.platform!=='win32')return;
 const child=spawnSync('powershell.exe',
  ['-NoProfile','-ExecutionPolicy','Bypass','-File',tool,'-OfflineSelfTest'],
  {encoding:'utf8',windowsHide:true,timeout:30000});
 assert.equal(child.status,0,child.stderr+'\n'+child.stdout);
 assert.match(child.stdout,/NO11_C50_E2E_OFFLINE_SELFTEST=PASS/);
});
