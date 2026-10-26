import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";

const root = new URL("../", import.meta.url);
const file = n=>fs.readFileSync(new URL(n,root),"utf8");
const launcher=file("windows/Start-ArkShadowClassicReadOnly.ps1");
const cmd=file("windows/Ark-Shadow-CLASSIC-READ-ONLY.cmd");
const installer=file("install/Install-ArkShadowClassicReadOnly.ps1");
const backend=file("ui/ark_shadow_classic.py");
const bridge=file("ui/classic/ark-shadow-classic-bridge.js");
const prior=file("ui/classic/ark-readonly-overlay.js");
const originalFile=new URL("ui/classic/index.html",root);

test("classic package preserves byte-exact original rich UI assets",()=>{
  const originalHtml=new URL("../../no1-1-msii/ui/public/index.html",root);
  const originalOverlay=new URL("../../no1-1-msii/ui/public/ark-readonly-overlay.js",root);
  assert.equal(fs.readFileSync(originalFile).equals(fs.readFileSync(originalHtml)),true);
  assert.equal(fs.readFileSync(new URL("ui/classic/ark-readonly-overlay.js",root))
    .equals(fs.readFileSync(originalOverlay)),true);
  assert.ok(fs.statSync(originalFile).size > 200000);
});

test("classic launcher is a separate restricted observer, never updates old frozen files",()=>{
  assert.match(cmd,/Start-ArkShadowClassicReadOnly\.ps1/);
  assert.match(launcher,/ui\\ark_shadow_classic\.py/);
  assert.match(launcher,/Port=8769/);
  assert.match(launcher,/shadow-oneclick-classic/);
  assert.match(launcher,/NO11_BOOTSTRAP_PREFLIGHT=EXISTING_ASSETS_LOADED_NOT_LIVE_VERIFIED/);
  assert.match(launcher,/ARK_SHADOW_FAILURE_STAGE/);
  assert.match(launcher,/ARK_SHADOW_OFFLINE_SELFTEST=PASS/);
  assert.match(launcher,/ORDER_TRANSMISSION=False/);
  assert.match(launcher,/ORIGINAL_SHEET_MISMATCH/);
  assert.match(launcher,/ORIGINAL_CONTROLLER_OBSERVER/);
  assert.doesNotMatch(launcher,/Stop-Process|taskkill|RssStockOrder|git\s+(pull|reset|checkout|push)/i);
  assert.doesNotMatch(cmd,/Ark-Terminal-No11\.cmd/);
});

test("classic browser only reads verified RSS and simulator receipts and never exposes writes",()=>{
  assert.match(backend,/import ark_shadow_ui as original/);
  assert.match(backend,/account_read_model/);
  assert.match(backend,/ORIGINAL_CLASSIC_SCRIPT_SET_UNEXPECTED/);
  assert.match(backend,/def _local_origin/);
  assert.match(backend,/def do_GET/);
  assert.match(backend,/positionsTruncated/);
  assert.match(backend,/tradeReadiness": "BLOCKED"/);
  assert.match(backend,/mode/i);
  assert.match(bridge,/\/api\/status/);
  assert.match(bridge,/ark-readonly-screen/);
  assert.match(bridge,/arksc-equity/);
  assert.match(bridge,/arksc-sim-rows/);
  assert.match(bridge,/arksc-real-rows/);
  assert.match(bridge,/replaceChildren/);
  assert.doesNotMatch(backend,/subprocess\.(run|Popen)|urllib\.request\.urlopen|request\.(post|put|patch)/i);
  assert.doesNotMatch(bridge,/eval\s*\(|innerHTML\s*=\s*(?:entry|data|s)\b/);
  assert.match(prior,/MUTATION_SELECTORS/);
});

test("installer accepts only exact new Shadow files, adds six new files and backs up only the new shortcut",()=>{
  assert.match(installer,/ORIGINAL_SHADOW_FILE_CHANGED/);
  assert.match(installer,/CLASSIC_DOWNLOAD_HASH_MISMATCH/);
  assert.match(installer,/CLASSIC_LOCAL_FILE_MODIFIED/);
  assert.match(installer,/SHORTCUT_TARGET_NOT_OURS/);
  assert.match(installer,/original-shadow-shortcut-/);
  assert.match(installer,/File\]::Replace/);
  assert.match(installer,/Ark Terminal Shadow READ ONLY\.lnk/);
  assert.match(installer,/NEW_CLASSIC_OFFLINE_SELFTEST_FAILED/);
  assert.match(installer,/ARK_CLASSIC_OLD_NO11_LAUNCHER_UNCHANGED=True/);
  assert.doesNotMatch(installer,/no11-launcher\\|Stop-Process|taskkill|git\s+(reset|checkout|pull|push)/i);
});
