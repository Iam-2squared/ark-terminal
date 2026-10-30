import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
const file=new URL('../windows/Stage-No11Oct29ReadOnlyFiles.ps1',import.meta.url);
const s=fs.readFileSync(file,'utf8');
test('Oct29 portable installer pins four exact Git source blob hashes and guards active collectors',()=>{
 for(const x of [
  "07de76726065f505c215e97bdd5e3f3bac1f8204",
  "72b4c4b440dd70d7e7c8fa7bd57a470f4ae2d3cd",
  "66c6de5063654b51434dabc408bf453e709bf5ea",
  "182aa998af2b0997a58255ae533f4c7f8f8bcd47",
  "94b13a2589b0e2c23d97c8e5c425f3e13581a23f",
  "COLLECTOR_RUNNING_MUST_STOP_NORMALLY",
  "NO11_OCT29_SOURCE_STAGE=PASS",
  "ORDER_TRANSMISSION=False",
  "NO11_OCT29_SHADOW_PREFLIGHT=NOT_PASSED"
 ])assert.ok(s.includes(x),x);
});
test('installer is source-only with rollback; never touches broker, original Excel or models',()=>{
 assert.match(s,/DOWNLOAD_BLOB_HASH/);
 assert.match(s,/INSTALL_BLOB_HASH/);
 assert.match(s,/for\(\$i=\$touched\.Count-1/);
 for(const x of [/RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,
  /Stop-Process|\.Kill\s*\(/,/Excel\.Application|GetActiveObject\s*\(/,
  /orderTransmission\s*=\s*\$true/])assert.doesNotMatch(s,x);
});
test('Windows installer offline selftest needs no broker or Excel',{skip:process.platform!=='win32'},()=>{
 const filePath=decodeURIComponent(file.pathname.replace(/^\//,''));
 const r=spawnSync('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass','-File',filePath,'-OfflineSelfTest'],
  {encoding:'utf8',timeout:20000});
 assert.equal(r.status,0,(r.stdout||'')+'\n'+(r.stderr||''));
 assert.match(r.stdout,/NO11_OCT29_STAGE_OFFLINE_SELFTEST=PASS/);
 assert.match(r.stdout,/ORDER_TRANSMISSION=False/);
});
