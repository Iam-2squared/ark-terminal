import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const recovery=fs.readFileSync(
 new URL('../windows/Recover-No11Book3ReferenceReadOnly.ps1',import.meta.url),'utf8');
const original=fs.readFileSync(
 new URL('../windows/Capture-No11SessionReferenceReadOnly.ps1',import.meta.url),'utf8');

test('salvage preserves original contract, no workbook changes and no fake safety review',()=>{
  for(const marker of [
   "Capture-No11SessionReferenceReadOnly.ps1",
   "no11_previous_archive_context.py",
   "no11_review_queue_from_actual_rss.py",
   "--symbols-only",
   "NO11_BOOK3_COMPETING_COLLECTOR_STILL_RUNNING",
   "Workbooks.Item('Book3')",
   "$sheet.Name -ceq 'Sheet1'",
   "GetActiveObject('Excel.Application')",
   "$formulaRange.Formula",
   "$valueRange.Value2",
   "NO11_BOOK3_ORIGINAL_RSS_FORMULA_DIFFERENT",
   "NO11_BOOK3_RSS_VALUES_SHAPE",
   "capturedAtJst=$start;completedAtJst=$end",
   "corporateActionReviewPerformed=$false",
   "readOnly=$true;productionReady=$false;orderTransmission=$false",
   "session-reference-",
   "FileMode]::CreateNew",
   "NO11_BOOK3_REFERENCE=CAPTURED_UNREVIEWED_NOT_MASTER",
   "NO11_BOOK3_TEMPORARY_BOOK=LEFT_OPEN_UNSAVED",
   "ORDER_TRANSMISSION=False",
  ])assert.ok(recovery.includes(marker),marker);
  for(const prohibited of [
   /\.Workbooks\.Add\s*\(/i,
   /\.Worksheets\.Add\s*\(/i,
   /\.SaveAs\s*\(/i,
   /\.Save\s*\(/i,
   /\.Close\s*\(/i,
   /Stop-Process\s/i,
   /Rss(?:StockOrder|MarginOpenOrder|CancelOrder)\s*\(/i,
   /EXTERNALLY_REVIEWED/
  ])assert.doesNotMatch(recovery,prohibited);
  for(const field of [
    '銘柄コード','市場コード','現在日付','前日日付','前日終値',
    '当日基準値','市場部名称','単位株数',
    '権利落日','配当落日','中配落日'
  ])assert.ok(recovery.includes(field)&&original.includes(field),field);
});

test('Book3 salvage reads same immutable original source schema and no predated receipt',()=>{
 assert.match(recovery,/RssMarket_SELECTED_REFERENCE_READONLY/);
 assert.match(recovery,/ARK_NO11_RSS_SESSION_REFERENCE_CAPTURE_V1/);
 assert.match(recovery,/SourcePath \$planFile/);
 assert.match(recovery,/SourcePath \$maskFile/);
 assert.match(recovery,/SourcePath \$PythonExecutable/);
 assert.match(recovery,/NO11_BOOK3_RSS_BULK_READ_TIMED_OUT_30S/);
 assert.match(recovery,/NO11_BOOK3_SCOPE_AND_FORMULAS=VERIFIED_47_OF_47/);
 assert.match(recovery,/NO11_BOOK3_REFERENCE_ROWS=47/);
});
