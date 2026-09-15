import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const setup = fs.readFileSync(new URL('./Initialize-ArkAccountReadOnlySheet.ps1', import.meta.url), 'utf8');
const snapshot = fs.readFileSync(new URL('./Start-ArkAccountReadOnlySnapshot.ps1', import.meta.url), 'utf8');

const formulaAssignments = [...setup.matchAll(/\.Formula\s*=\s*['"]([^'"]+)['"]/g)].map(match => match[1]);

const forbiddenWriteFunctions = [
  'RssStockOrder',
  'RssMarginOpenOrder',
  'RssMarginCloseOrder',
  'RssModifyOrder',
  'RssCancelOrder',
  'RssFOPOpenOrder',
  'RssFOPCloseOrder',
  'RssFOPMultiOpenOrder',
  'RssFOPMultiCloseOrder',
  'RssFOPModifyOrder',
  'RssFOPCancelOrder',
];

test('one-time account sheet initializer writes only four read-only RSS list formulas', () => {
  assert.deepEqual(formulaAssignments, [
    '=RssCapacityList(L2:L2)',
    '=RssOrderList(N2:W2,0,1)',
    '=RssExecutionList(AA2:AI2,1)',
    '=RssPositionList(AL2:AU2)',
  ]);
  for (const formula of formulaAssignments) {
    for (const forbidden of forbiddenWriteFunctions) {
      assert.equal(formula.includes(forbidden), false, `${formula} must not contain ${forbidden}`);
    }
  }
});

test('initializer preserves the parser column contract for cash account data', () => {
  for (const token of [
    '"L2").Value2 = "現物買付可能額"',
    '"注文番号"', '"通常注文状況"', '"注文数量"', '"約定数量"',
    '"約定日"', '"口座区分"', '"約定単価"',
    '"保有数量"', '"平均取得価額"', '"時価評価額"', '"評価損益額"', '"評価損益率"',
  ]) {
    assert.equal(setup.includes(token), true, `missing setup token: ${token}`);
  }
});

test('snapshot launcher verifies layout and RSS readiness before exporting fresh state', () => {
  assert.equal(snapshot.includes('Assert-ArkAccountSheetLayout'), true);
  assert.equal(snapshot.includes('Wait-ArkReadOnlyRssReady'), true);
  assert.equal(snapshot.includes('RSS_READ_ONLY_SOURCE_NOT_READY'), true);
  assert.equal(snapshot.includes('ACCOUNT_SHEET_SETUP_REQUIRED'), true);
  assert.equal(snapshot.includes('averagePrice=$acct.Cells.Item($row,43).Value2'), true);
  assert.equal(snapshot.includes('marketPrice=$acct.Cells.Item($row,44).Value2'), true);
  assert.equal(snapshot.includes('marketValue=$acct.Cells.Item($row,45).Value2'), true);
  assert.equal(snapshot.includes('unrealizedPnl=$acct.Cells.Item($row,46).Value2'), true);
  assert.equal(snapshot.includes('unrealizedPnlPercent=$acct.Cells.Item($row,47).Value2'), true);
});
