import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const file = new URL('../windows/Prepare-No11NextSessionNightlyReadOnly.ps1', import.meta.url);
const source = fs.readFileSync(file, 'utf8');

test('nightly entry is explicitly read-only and safe on Windows PowerShell 5.1', () => {
  assert.equal(source.charCodeAt(0), 0xFEFF, 'UTF-8 BOM required');
  assert.match(source, /\[switch\]\$OfflineSelfTest/);
  assert.match(source, /NO11_NIGHTLY_OFFLINE_SELFTEST=PASS/);
  assert.match(source, /NO11_NIGHTLY_EXCEL_STARTED=False/);
  assert.match(source, /NO11_NIGHTLY_SELECTOR_OR_PORTFOLIO_STARTED=False/);
  assert.match(source, /ORDER_TRANSMISSION=False/);
  assert.doesNotMatch(source, /RssStockOrder\s*\(|RssCancelOrder\s*\(|RssStockOrder|RssCancelOrder/);
  assert.doesNotMatch(source, /productionReady\s*=\s*true|orderTransmission\s*=\s*true/i);
  assert.doesNotMatch(source, /git\s+(?:pull|push|reset|checkout)|taskkill|Stop-Process|Workbooks\.Close/);
});
test('nightly preparation runs daily census then pass/Chart50 then previous archive', () => {
  const daily = source.indexOf('=== NIGHTLY STAGE 1: FULL-UNIVERSE DAILY G1 ===');
  const plan = source.indexOf('=== NIGHTLY STAGE 2: OBSERVED PASS AND CHART50 PLAN ===');
  const previous = source.indexOf('=== NIGHTLY STAGE 3: ORIGINAL PREVIOUS-SESSION 1M ARCHIVE ===');
  assert.ok(daily > 0 && plan > daily && previous > plan);
  assert.match(source, /NO11_NIGHTLY_DAILY_NOT_YET_ELIGIBLE|DAILY_NOT_YET_ELIGIBLE/);
  assert.match(source, /NO11_NIGHTLY_NOT_YET_READY=DATED_MASTER_SECURITY_EVIDENCE_AND_BOOTSTRAP/);
  assert.match(source, /CAPACITY_ONLY_NO_BROKER_POSITION_CERTIFICATION/);
  assert.match(source, /-PinsFile/);
  assert.match(source, /\$LASTEXITCODE -eq 0/);
});

test('nightly plan identity selects the active pinned run even when stale as-of folders coexist', () => {
  assert.match(source, /identityTool=Join-Path \$base/);
  assert.match(source, /node \$identityTool plan --symbols \$SymbolsFile --root \$DailyRoot/);
  assert.match(source, /DAILY_G1_RESOLVED_PLAN_INCOMPLETE/);
  assert.doesNotMatch(source, /Get-ChildItem -LiteralPath \$DailyRoot -Directory -Filter/);
});
