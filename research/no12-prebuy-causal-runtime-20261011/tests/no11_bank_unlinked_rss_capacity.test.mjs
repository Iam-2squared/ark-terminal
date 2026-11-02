import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const path=new URL('../windows/Capture-No11BankUnlinkedRssCapacityReadOnly.ps1',import.meta.url);
const code=fs.readFileSync(path,'utf8');

test('Nov2 RSS buying power is read only from pinned account workbook and exact capacity formula',()=>{
  for(const token of [
    "'Ark_No11_MSII_RSS.xlsx'","'ARK_ACCOUNT_READONLY'",
    "RssCapacityList","'現物買付可能額'",
    "EXACT_ONE_ORIGINAL_RSS_CAPACITY_FORMULA_REQUIRED",
    "EXCEL_WINDOW_NOT_UNIQUE",
    "READ_ONLY_VALUE2_RETURNED",
    "NO11_RSS_CAPACITY_OBSERVATION_FILE=",
    "bankNotLinkedOperatorConfirmed",
    "autoSweepOffOperatorConfirmed",
    "rssVendorAsOfTimeCertified",
    "securitiesCashBalanceCertified",
    "liveApproved='false'",
    "ORDER_TRANSMISSION=False",
  ])assert.ok(code.includes(token),token);
  for(const bad of [
    /Workbooks\.Add\s*\(/i,/Workbooks\.Open\s*\(/i,
    /\.Save\s*\(/i,/\.SaveAs\s*\(/i,
    /RssStockOrder\s*\(/i,/RssMarginOpenOrder\s*\(/i,
    /RssCancelOrder\s*\(/i,/Stop-Process/i,
    /Range\s*\([^)]*\)\.Formula\s*=/i,
    /Cells\.Item\s*\([^)]*\)\.Formula\s*=/i,
  ])assert.doesNotMatch(code,bad);
});

test('No screenshot reference or LIVE cash balance certification without reviewed brokerage summary',()=>{
  assert.doesNotMatch(code,/ScreenshotFile/i);
  assert.doesNotMatch(code,/sourceDocumentPath/i);
  assert.ok(code.includes("securitiesCashBalanceCertified='false'"));
  assert.ok(code.includes("NO11_RSS_CAPACITY_LIVE_OPENING_LEDGER=NOT_ACTIVATED"));
});

test('PowerShell case-insensitive ValidateSet Account parameter is never reused for COM workbook',()=>{
  assert.match(code,/\[ValidateSet\('一般'\)\]\[string\]\$Account='一般'/);
  assert.match(code,/\$accountWorkbook=\$excel\.Workbooks\.Item\('Ark_No11_MSII_RSS\.xlsx'\)/);
  assert.match(code,/account=\$Account/);
  assert.doesNotMatch(code,/\$account\s*=/i);
  assert.doesNotMatch(code,/\$account\.(?:Worksheets|Range|Cells|Name|Close)/i);
});
