import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const FILE = new URL("../../tools/phase57_msii_windows_full_session.ps1", import.meta.url);
const source = fs.readFileSync(FILE, "utf8");

const FALSE_KEYS = ["executionAllowed","brokerWriteAllowed","excelOrderWriteAllowed","rssOrderFunctionAllowed","liveTradingAllowed","paperTradingAllowed","automaticPromotionAllowed","productionUpdateAllowed"];
const FORBIDDEN_RSS_ORDER_FUNCTIONS = ["RssStockOrder","RssMarginOpenOrder","RssMarginCloseOrder","RssModifyOrder","RssCancelOrder","RssFOPOpenOrder","RssFOPCloseOrder","RssFOPModifyOrder","RssFOPCancelOrder","RssFutureOrder","RssOptionOrder"];

test("Windows Lane M launcher is read-only and cannot mutate the repository remote", () => {
  for (const key of FALSE_KEYS) assert.match(source, new RegExp(`${key}\\s*=\\s*\\$false`, "i"));
  for (const token of FORBIDDEN_RSS_ORDER_FUNCTIONS) assert.equal(source.toLowerCase().includes(token.toLowerCase()), false, `forbidden RSS function ${token}`);
  for (const command of ["git push", "git checkout", "git switch", "git reset", "git commit"]) assert.equal(source.toLowerCase().includes(command), false, `launcher must not contain ${command}`);
});

test("Windows Lane M launcher starts verified fresh prospective capture before consuming capsules", () => {
  const capture = source.indexOf("Start-Process -FilePath $Python");
  const freshEvidence = source.indexOf("$captureReady = $true");
  const sync = source.indexOf("Start-Job -FilePath $syncScript");
  const watcher = source.indexOf("phase57_msii_full_session_runner.mjs");
  assert.ok(capture > 0);
  assert.ok(freshEvidence > capture);
  assert.ok(sync > freshEvidence);
  assert.ok(watcher > sync);
  assert.match(source, /phase58_excel_multisymbol_microstructure_capture\.py/);
  assert.match(source, /MarketSpeed capture produced no fresh evidence/);
  assert.match(source, /Another Lane M full-session launcher appears to own/);
  assert.match(source, /\[System\.IO\.FileShare\]::None/);
  assert.match(source, /automation\/phase57-realtime-live-data/);
  assert.match(source, /msii-envelopes/);
  assert.match(source, /\[string\]\$StopAtJst = "16:10"/);
});

test("Windows Lane M launcher synchronizes immutable envelopes without touching main", () => {
  assert.match(source, /git fetch --quiet origin 'refs\/heads\/automation\/phase57-realtime-live-data:refs\/remotes\/origin\/automation\/phase57-realtime-live-data'/);
  assert.match(source, /git ls-tree -r --name-only \$DurableRef/);
  assert.match(source, /git show "\$\{DurableRef\}:\$remotePath"/);
  assert.match(source, /if\(Test-Path \$destination\)\{ continue \}/);
  assert.match(source, /Move-Item -LiteralPath \$temp -Destination \$destination/);
});
