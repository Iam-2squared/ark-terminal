import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const root=new URL("../",import.meta.url);
const load=n=>fs.readFileSync(new URL(n,root),"utf8");
const launcher=load("windows/Start-ArkShadowClassicReadOnly.ps1");
const installer=load("install/Upgrade-ArkShadowClassicStartupV2ReadOnly.ps1");
const cmd=load("windows/Ark-Shadow-CLASSIC-V2-READ-ONLY.cmd");

test("exact failure reproduction: original-status first and second publish in temporary self-test",()=>{
  assert.match(launcher,/function InstallStatusAtomicWriter/);
  assert.match(launcher,/EntryPoint="MoveFileExW"/);
  assert.match(launcher,/MoveFileEx\(\$tmp,\$statusFile,9\)/);
  assert.match(launcher,/ARK_SHADOW_STATUS_REPUBLISH_SELFTEST=PASS/);
  assert.match(launcher,/OFFLINE_ATOMIC_TEST_FIRST/);
  assert.match(launcher,/OFFLINE_ATOMIC_TEST_SECOND/);
  assert.match(launcher,/STATUS_REPUBLISH_OFFLINE_SELFTEST_FAILED/);
  assert.match(launcher,/STATUS_ATOMIC_COMMIT_RETRY_EXHAUSTED_WIN32/);
  assert.doesNotMatch(launcher,/\[IO\.File\]::Replace\(\$tmp,\$statusFile/);
});

test("orphaned healthy classic UI is reused AND startup continues to MarketSpeed/Excel",()=>{
  assert.match(launcher,/ARK_SHADOW_EXISTING_UI_RECOVERY=True/);
  assert.match(launcher,/EXISTING_CLASSIC_UI_NO_LONGER_HEALTHY/);
  assert.match(launcher,/ARK_SHADOW_RESTART_CLASSIC_UI_REQUIRED_FOR_NEW_CONFIG/);
  assert.match(launcher,/PUBLISH_AFTER_CLASSIC_UI/);
  assert.match(launcher,/SET_MARKETSPEED_AND_EXCEL_FLAGS/);
  assert.match(launcher,/OPEN_MARKETSPEED/);
  assert.match(launcher,/OPEN_VERIFY_EXCEL_BOOKS/);
  assert.match(launcher,/FindMarketSpeed/);
  assert.match(launcher,/Original|ORIGINAL/);
  assert.doesNotMatch(launcher,/\bStop-Process\b|\btaskkill\b|\bRssStockOrder\s*\(/);
});

test("installer only installs two NEW V2 files and re-points the owned classic shortcut",()=>{
  assert.match(cmd,/Start-ArkShadowClassicReadOnly-V2\.ps1/);
  assert.match(installer,/dca1505025a0c43b9414b7fea00257792e5db56d/);
  assert.match(installer,/77a3a4ba8fb2875dc3aa838417a47578e42689eb/);
  assert.match(installer,/NINE_ORIGINAL_BLOBS=PASS/);
  assert.match(installer,/EXISTING_LOCAL_FILE_CHANGED/);
  assert.match(installer,/DOUBLE_PUBLISH_OFFLINE_SELFTEST_FAILED/);
  assert.match(installer,/ARK_SHADOW_STATUS_REPUBLISH_SELFTEST=PASS/);
  assert.match(installer,/CLASSIC_ICON_MISSING/);
  assert.match(installer,/SHORTCUT_NOT_OUR_CLASSIC_ICON/);
  assert.match(installer,/classic-pre-v2-/);
  assert.match(installer,/SHORTCUT_RESTORED_FROM_BACKUP/);
  assert.match(installer,/ARK_CLASSIC_V2_FAILED_STAGE/);
  assert.match(installer,/ORDER_TRANSMISSION=False/);
  assert.doesNotMatch(installer,/Stop-Process|taskkill|git\s+(?:reset|checkout|pull|push)\b/i);
  assert.doesNotMatch(installer,/no11-launcher|vbaProject|Set-ItemProperty|Excel\.AddIns/i);
});

test("PowerShell offline probe is used instead of starting Excel or Shadow",()=>{
  assert.match(installer,/ParseFile\(\$script/);
  assert.match(installer,/\-OfflineSelfTest/);
  assert.match(installer,/\[switch\]\$VerifyOnly/);
  assert.match(launcher,/ARK_SHADOW_EXCEL_STARTED=False/);
  assert.match(launcher,/ARK_SHADOW_OLD_LAUNCHER_TOUCHED=False/);
});
