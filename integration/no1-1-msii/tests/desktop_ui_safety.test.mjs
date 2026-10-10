import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const read=x=>fs.readFileSync(path.join(root,x),'utf8');
test('desktop UI2 auto refresh selects only approved read-only capture entrypoint',()=>{
  const server=read('ui/ark_ui2_readonly_server.py');
  assert(server.includes('allowed_preview_scripts'));
  assert(server.includes('PREVIEW_SCRIPT_NOT_APPROVED'));
  assert(server.includes('Write-No11DesktopReadOnlyPreview.ps1'));
  assert(server.includes('preview_script=preview_script'));
});
test('desktop UI2 commands cannot write Excel, place orders or auto approve',()=>{
  for(const script of ['windows/Write-No11DesktopReadOnlyPreview.ps1',
    'windows/Start-No11DesktopUi.ps1']){
    const src=read(script);
    assert.doesNotMatch(src,/Workbooks\s*\.\s*Add\s*\(/i);
    assert.doesNotMatch(src,/\.\s*(?:Save|SaveAs|RegisterXLL)\s*\(/i);
    assert.doesNotMatch(src,/\.\s*Formula\s*=/);
    assert.doesNotMatch(src,/\bRssStockOrder\s*\(/i);
    assert.doesNotMatch(src,/explicitSafetyReset/);
    assert(src.includes('ORDER_TRANSMISSION=False'));
  }
});
test('UI model console output never prints raw buying power',()=>{
  const src=read('ui/phase57_ui_read_model_cli.mjs');
  assert(!src.includes('console.log(\u0060BUYING_POWER='));
});
