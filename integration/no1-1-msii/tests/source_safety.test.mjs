import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const read=p=>fs.readFileSync(path.join(root,p),'utf8');

test('the snapshot capture has no AutoRegisterXLL path or order function',()=>{
  const src=read('windows/Get-No11ReadOnlySnapshot.ps1');
  assert.doesNotMatch(src,/\.\s*RegisterXLL\s*\(/i);
  assert.doesNotMatch(src,/function\s+Ensure-ArkRssAddinLoaded/i);
  assert.doesNotMatch(src,/\bRssStockOrder\s*\(/i);
  assert.doesNotMatch(src,/\.Formula\s*=/);
  assert.doesNotMatch(src,/\.Value2\s*=/);
});
test('the read-only path requires all four broker feeds',()=>{
  const src=read('windows/Get-No11ReadOnlySnapshot.ps1');
  for(const k of ['RssCapacityList','RssOrderList','RssExecutionList','RssPositionList'])
    assert(src.includes(k));
  assert(src.includes('DoNotAutoOpenWorkbook'));
  assert(src.includes('actualFeedTimestampCertified = $false'));
});
test('No.1.1 UI projection cannot invoke any order or Excel write',()=>{
  const ui=read('ui/phase57_ui_read_model.mjs');
  assert(ui.includes("orderSubmit: false"));
  assert(ui.includes("orderCancel: false"));
  assert(ui.includes("brokerWrite: false"));
  assert(ui.includes("excelOrderWrite: false"));
  assert(ui.includes("rssOrderFunction: false"));
  const preview=read('windows/Write-No11ReadOnlyPreview.ps1');
  assert.doesNotMatch(preview,/\.\s*RegisterXLL\s*\(/i);
  assert.doesNotMatch(preview,/\bRssStockOrder\s*\(/i);
});
test('UI server is loopback only, forbids mutations, and uses recovered interface',()=>{
  const server=read('ui/ark_ui2_readonly_server.py');
  assert(server.includes('("127.0.0.1", args.port)'));
  assert(server.includes('do_POST'));
  assert(server.includes('do_PUT = do_POST'));
  assert(server.includes('do_PATCH = do_POST'));
  assert(server.includes('do_DELETE = do_POST'));
  assert(server.includes('repo_root / "ui" / "public"'));
  assert(server.includes('repo_root / "windows" / "Write-No11ReadOnlyPreview.ps1"'));
});
test('safe Windows launch cannot remotely enable execution',()=>{
  const launch=read('windows/Start-No11UiReadOnly.ps1');
  assert.doesNotMatch(launch,/\bRssStockOrder\s*\(/i);
  assert.doesNotMatch(launch,/\.\s*RegisterXLL\s*\(/i);
  assert(launch.includes('127.0.0.1'));
});
