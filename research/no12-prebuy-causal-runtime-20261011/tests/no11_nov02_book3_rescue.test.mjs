import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const src=fs.readFileSync(new URL('../windows/Rescue-No11Nov02Book3ReferenceReadOnly.ps1',import.meta.url),'utf8');

test('Book3 rescue uses existing 24 genuine formulas, with no new workbook, formulas or order calls',()=>{
 for(const x of [
  "TWO_ORIGINAL_BOOKS_PLUS_EXACT_BOOK3_REQUIRED",
  "Item('Book3')",
  "NO11_REFERENCE_STAGE=RESCUE_EXISTING_BOOK3_WITHOUT_REQUERY",
  "BOOK3_NOT_ORIGINAL_RSS_FORMULAS",
  "NO11_REFERENCE_ROW_PARSED=",
  "NO11_REFERENCE_ROW_VALUE2_RETURNED=",
  "NO11_REFERENCE_RESCUE_BOOK3_PRESERVED=True",
  "NO11_SESSION_REFERENCE_FILE=",
  "NO11_REFERENCE_STAGE=SERIALIZE_SCALAR_ROWS_BEGIN",
  "NO11_REFERENCE_STAGE=SERIALIZE_SCALAR_ROWS_COMPLETE",
  "NO11_REFERENCE_RESCUE_JSON_24_DOTNET_SELFTEST=PASS",
  "System.Web.Script.Serialization.JavaScriptSerializer",
  "RESCUE_READ_EXCEEDED_30_SECONDS",
  "corporateActionReviewPerformed=$false",
  "orderTransmission=$false",
  "REFERENCE_ROW_VALUE2_BEGIN",
 ])assert.ok(src.includes(x),x);
 for(const dangerous of [
  /Workbooks\.Add\s*\(/,/Workbooks\.Open\s*\(/,
  /sheet\.Range\([^)]*\)\.Formula\s*=/,
  /\.Save\s*\(/,/\.SaveAs\s*\(/,/\.Quit\s*\(/,
  /book\.Close\s*\(/,
  /RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,/Stop-Process/,
  /approvedForSession\s*=\s*\$true/
 ])assert.doesNotMatch(src,dangerous);
});
