import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const root = new URL("../", import.meta.url);
const source = fs.readFileSync(new URL("install/Repair-ArkShadowClassicLocalReadOnly.ps1",root), "utf8");

test("Recovery pins all previously-installed six rich-UI assets and original three", () => {
  assert.match(source, /\$original\.Count -eq 3/);
  assert.match(source, /\$classic\.Count -eq 6/);
  assert.match(source, /ark_shadow_classic\.py/);
  assert.match(source, /ark_shadow_ui\.py/);
  assert.match(source, /ark-readonly-overlay\.js/);
  assert.match(source, /ark-shadow-classic-bridge\.js/);
  assert.match(source, /ORIGINAL_AND_CLASSIC_BLOBS/);
  assert.match(source, /LOCAL_FILE_HASH_MISMATCH/);
});

test("Recovery must NEVER evaluate Python -c or use a remote source", () => {
  assert.match(source, /\$pythonSource = @'/);
  assert.match(source, /\& \$py -B \$probe \$uiDir/);
  assert.match(source, /classic\.classic_document\(\)/);
  assert.match(source, /PYTHON_IMPORT_OR_ASSET_TEST_FAILED/);
  assert.doesNotMatch(source, /\$py\s+-B\s+-c\b/);
  assert.doesNotMatch(source, /Invoke-WebRequest|Invoke-RestMethod|WebClient|DownloadString|HttpClient/i);
  assert.doesNotMatch(source, /Stop-Process|taskkill|git\s+(pull|checkout|reset|push)/i);
});

test("Recovery uses entirely NEW unique icon; old shortcuts/workbooks/models untouched", () => {
  assert.match(source, /Ark Terminal Classic Shadow READ ONLY\.lnk/);
  assert.match(source, /SHORTCUT_CONFLICT_NO_OVERWRITE/);
  assert.match(source, /SHORTCUT_POSTVERIFY_FAILED/);
  assert.match(source, /ARK_CLASSIC_REPAIR_EXISTING_NEW_SHADOW_UNCHANGED=True/);
  assert.match(source, /ARK_CLASSIC_REPAIR_OLD_NO11_UNCHANGED=True/);
  assert.match(source, /ORDER_TRANSMISSION=False/);
  assert.doesNotMatch(source, /\[IO\.File\]::Replace|\.Copy\(\$lnk|\$existing\.TargetPath\s*=/);
  assert.doesNotMatch(source, /Ark-Terminal-No11\.cmd/);
});

test("Recovery reports precise failure stage and exit without generic outer throw", () => {
  for (const marker of [
    'ARK_CLASSIC_REPAIR_FAILED_STAGE=', 'ARK_CLASSIC_REPAIR_EXCEPTION_TYPE=',
    'ARK_CLASSIC_REPAIR_STATUS=BLOCKED', 'ARK_CLASSIC_REPAIR_STATUS=COMPLETE',
    'ARK_CLASSIC_REPAIR_OFFLINE_SELFTEST=PASS',
    'ARK_CLASSIC_REPAIR_LOCAL_URL=http://127.0.0.1:8769/'
  ]) assert.ok(source.includes(marker), marker);
});
