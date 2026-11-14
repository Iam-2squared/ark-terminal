import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
const root=new URL("../",import.meta.url);
const file=n=>fs.readFileSync(new URL(n,root),"utf8");
const ps=file("windows/Start-ArkShadowReadOnly.ps1");
const cmd=file("windows/Ark-Shadow-READ-ONLY.cmd");
const py=file("ui/ark_shadow_ui.py");

test("independent one-click entry never references the old desktop shortcut as target",()=>{
 assert.match(cmd,/Start-ArkShadowReadOnly\.ps1/);
 assert.doesNotMatch(cmd,/Ark-Terminal-No11\.cmd|Start-ArkTerminalNo11\.ps1/);
 assert.match(ps,/shadow-oneclick/);
 assert.match(ps,/Start-Process -FilePath \$account/);
 assert.match(ps,/Start-Process -FilePath \$market/);
 assert.doesNotMatch(ps,/git\s+(?:reset|checkout|pull|switch|push|commit)/i);
 assert.doesNotMatch(ps,/Stop-Process|taskkill/i);
});
test("read-only original frozen Shadow preflight with no broker transport",()=>{
 assert.match(ps,/Run-No11ReceivedSessionReadOnly\.ps1/);
 assert.match(ps,/Prepare-No11ReceivedInputsReadOnly\.ps1/);
 assert.match(ps,/original input|Original|ORIGINAL/);
 assert.match(ps,/Preflight\s+\$PreparedConfigFile\s+\$pinned/);
 assert.match(ps,/\-PreflightOnly/);
 assert.match(ps,/brokerExecutionConfig' -notin/);
 assert.match(ps,/orderIdWorkbookPath' -notin/);
 assert.match(ps,/shadowAccountConfig' -in/);
 assert.match(ps,/orderTransmission -eq \$false/);
 assert.match(ps,/ORDER_TRANSMISSION=False/);
 assert.match(ps,/WORKBOOK_ORDER_FORMULA|ORDER_FORMULA_FORBIDDEN/);
});
test("dashboard never exposes a broker execution/write API or fabricates real equity",()=>{
 assert.match(py,/ThreadingHTTPServer\(\("127\.0\.0\.1"/);
 assert.match(py,/def do_POST/);
 assert.match(py,/mode=ro/);
 assert.match(py,/result\["totalAssets"\] = None/);
 assert.doesNotMatch(py,/subprocess\.(run|Popen)|requests\.(post|put)|urllib\.request\.urlopen/);
 assert.match(py,/account_secondary_file/);
});
