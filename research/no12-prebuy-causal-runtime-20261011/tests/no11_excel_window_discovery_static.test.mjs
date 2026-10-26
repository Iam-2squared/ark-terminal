import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

for (const [file, label] of [
  ['Run-No11RssDailyTrendCensusReadOnly.ps1', 'DAILY'],
  ['Capture-No11RssTrainingBatchReadOnly.ps1', 'BATCH'],
]) {
  test(`${label} uses unique visible Excel fallback but retains original two-workbook guards`, () => {
    const source = fs.readFileSync(new URL('../windows/' + file, import.meta.url), 'utf8');
    assert.match(source, /\$arkNamed\.Count -eq 1/);
    assert.match(source, /\$arkNamed\.Count -eq 0 -and \$visible\.Count -eq 1/);
    assert.match(source, new RegExp('NO11_' + label + '_EXCEL_DISCOVERY=VISIBLE_'));
    assert.match(source, /\$excel\.Workbooks\.Count -ne 2/);
    assert.match(source, /Ark_No11_MSII_RSS\.xlsx/);
    assert.match(source, /Ark_No11_MARKET_RSS\.xlsx/);
    assert.match(source, /ARK_ACCOUNT_READONLY/);
    assert.match(source, /ARK_MARKET_READONLY/);
    assert.doesNotMatch(source, /Stop-Process|taskkill|RssStockOrder\s*\(|RssCancelOrder\s*\(/);
  });
}
