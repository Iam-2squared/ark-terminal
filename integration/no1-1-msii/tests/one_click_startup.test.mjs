import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const read=(p)=>fs.readFileSync(path.join(root,p),'utf8');
const launcher=read('windows/Start-ArkTerminalNo11.ps1');
const cmd=read('windows/Ark-Terminal-No11.cmd');
const install=read('windows/Install-ArkTerminalDesktopShortcut.ps1');

test('one click startup reuses verified workbook and Frozen checkout only',()=>{
  assert.match(launcher,/Ark_No11_MSII_RSS\.xlsx/);
  assert.match(launcher,/ARK_ACCOUNT_READONLY/);
  assert.match(launcher,/10c94c92c4bd2a59a22744667fd0210252602df4/);
  assert.match(launcher,/Start-No11DesktopUi\.ps1/);
  assert.match(launcher,/C:\\ArkTerminal\\repo/);
  assert.match(launcher,/RSS_FOUR_STATUS_CELLS_OBSERVED=True/);
  assert.match(launcher,/Get-WorkbookOpenState/);
  assert.match(launcher,/EXCEL_COM_BUSY_WAITING_WITHOUT_REOPEN/);
  assert.match(launcher,/ARK_DUPLICATE_WORKBOOK_INSTANCES_BLOCKED/);
  assert.match(launcher,/ACTUAL_BROKER_DELIVERY_TIMESTAMP_CERTIFIED=False/);
  assert.match(launcher,/Local\\ArkTerminal_No11_DesktopLauncher/);
});

test('startup never enables RSS order permission or modifies Excel cells',()=>{
  for(const src of [launcher,cmd,install]){
    assert.doesNotMatch(src,/\bRss(?:StockOrder|ModifyOrder|CancelOrder)\s*\(/i);
    assert.doesNotMatch(src,/\.Formula(?:2)?\s*=/i);
    assert.doesNotMatch(src,/\.SaveAs\s*\(/i);
    assert.doesNotMatch(src,/RegisterXLL\s*\(/i);
    assert.doesNotMatch(src,/executionAllowed\s*=\s*true|transmitted\s*=\s*true/);
    assert.doesNotMatch(src,/git\s+(?:merge|reset|push|checkout)/i);
  }
  assert.match(launcher,/EXCEL_RSS_ORDER_PERMISSION=KEEP_OFF/);
  assert.match(launcher,/ARK_RSS_STATUS_NOT_READY_TIMEOUT/);
  assert.match(launcher,/ARK_WORKBOOK_ORDER_RSS_FORMULA_FORBIDDEN/);
  assert.match(launcher,/ARK_WORKBOOK_MACRO_BINARY_BLOCKED/);
  assert.match(launcher,/Assert-PortAvailable/);
});

test('desktop one-click is a separate installer, not an implicit overwrite',()=>{
  assert.match(cmd,/"%~dp0Start-ArkTerminalNo11.ps1"/);
  assert.match(install,/ARK_DESKTOP_SHORTCUT_ALREADY_EXISTS_DO_NOT_OVERWRITE/);
  assert.match(install,/ARK_DESKTOP_SHORTCUT_CREATED=True/);
  assert.match(install,/Ark-Terminal-No11\.cmd/);
  assert.doesNotMatch(install,/Remove-Item|Force\s*=\s*true|Move-Item/);
});
