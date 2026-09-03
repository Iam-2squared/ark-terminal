import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const FILE = new URL("../../tools/phase57_msii_windows_full_session_dashboard.ps1", import.meta.url);
const source = fs.readFileSync(FILE, "utf8");

const FALSE_KEYS = [
  "executionAllowed","brokerWriteAllowed","excelOrderWriteAllowed","rssOrderFunctionAllowed",
  "liveTradingAllowed","paperTradingAllowed","automaticPromotionAllowed","productionUpdateAllowed",
];
const FORBIDDEN = [
  "RssStockOrder","RssMarginOpenOrder","RssMarginCloseOrder","RssModifyOrder","RssCancelOrder",
  "RssFOPOpenOrder","RssFOPCloseOrder","RssFOPModifyOrder","RssFOPCancelOrder","RssFutureOrder","RssOptionOrder",
];

test("Windows Lane M dashboard wrapper remains read-only", () => {
  for (const key of FALSE_KEYS) assert.match(source, new RegExp(`${key}\\s*=\\s*\\$false`, "i"));
  for (const token of FORBIDDEN) assert.equal(source.toLowerCase().includes(token.toLowerCase()), false, `forbidden order function ${token}`);
  for (const command of ["git push", "git checkout", "git switch", "git reset", "git commit"]) assert.equal(source.toLowerCase().includes(command), false, `wrapper must not contain ${command}`);
});

test("Windows Lane M dashboard wrapper launches dashboard plus core prospective session and checks artifacts", () => {
  assert.match(source, /phase57_msii_dashboard_watch\.mjs/);
  assert.match(source, /phase57_msii_windows_full_session\.ps1/);
  assert.match(source, /dashboard-latest\.json/);
  assert.match(source, /dashboard-history\.json/);
  assert.match(source, /strategyCount/);
  assert.match(source, /coveragePercent/);
  assert.match(source, /\[string\]\$StopAtJst = "16:10"/);
});
