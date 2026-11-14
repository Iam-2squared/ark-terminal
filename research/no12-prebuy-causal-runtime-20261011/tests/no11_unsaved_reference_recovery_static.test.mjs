import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const p=new URL('../windows/Recover-No11UnsavedReferenceReadOnly.ps1',import.meta.url);
const src=fs.readFileSync(p,'utf8');
test('BookN recovery is BOM UTF-8 and accepts only ONE formula-identical UNSAVED third book',()=>{
 assert.equal(src.charCodeAt(0),0xfeff);
 for(const token of [
  "NO11_RECOVERY_UNSAVED_WORKBOOK=EXACTLY_ONE_VERIFIED",
  "ONE_UNSAVED_RSS_BOOK_REQUIRED",
  "UNSAVED_RSS_BOOK_IDENTITY_INVALID",
  "EXACTLY_THREE_BOOKS_REQUIRED",
  "Workbooks.Item($others[0])",
  "$sheet.Name -ceq 'Sheet1'",
  "$book.Worksheets.Count -eq 1",
  "NO11_BOOK3_SCOPE_AND_FORMULAS=VERIFIED_47_OF_47",
  "ORIGINAL_SCOPE_VALIDATION_FAILED",
  "BOOK3_ORIGINAL_RSS_FORMULA_DIFFERENT",
  "COMPETING_COLLECTOR_STILL_RUNNING",
  "NO11_BOOK3_REFERENCE_ROWS=47",
  "NO11_BOOK3_REFERENCE=CAPTURED_UNREVIEWED_NOT_MASTER",
  "NO11_BOOK3_TEMPORARY_BOOK=LEFT_OPEN_UNSAVED",
  "ORDER_TRANSMISSION=False",
 ])assert.ok(src.includes(token),token);
 assert.equal(src.includes("Workbooks.Item('Book3')"),false);
 for(const regex of [
  /\bStop-Process\b/,/\bWorkbooks\.Add\s*\(/,/\bWorksheets\.Add\s*\(/,
  /\bSaveAs\s*\(/,/\bWorkbook\.Close\s*\(/,/\$book\.Close\s*\(/,
  /\bRss(?:StockOrder|MarginOpenOrder|CancelOrder)\s*\(/,
  /\bEXTERNALLY_REVIEWED\b/
 ])assert.doesNotMatch(src,regex);
});
test('salvage writes receipt at CURRENT read time and not as previous failed receipt',()=>{
 assert.match(src,/capturedAtJst=\$start;completedAtJst=\$end/);
 assert.match(src,/corporateActionReviewPerformed=\$false/);
 assert.match(src,/readOnly=\$true;productionReady=\$false;orderTransmission=\$false/);
 assert.match(src,/HASHED_REAL_RSS_VALUES/);
 assert.match(src,/NO11_BOOK3_REFERENCE=CAPTURED_UNREVIEWED_NOT_MASTER/);
});
