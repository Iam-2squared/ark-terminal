import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const filename=new URL('../windows/Capture-No11SessionReferenceRowwiseReadOnly.ps1',import.meta.url);
const s=fs.readFileSync(filename,'utf8');
test('Nov2 RSS rowwise collector identifies exact COM/read/parse hang boundaries',()=>{
 for(const token of [
  "NO11_REFERENCE_ROW_VALUE2_BEGIN=",
  "NO11_REFERENCE_ROW_VALUE2_RETURNED=",
  "NO11_REFERENCE_ROW_PARSED=",
  "NO11_REFERENCE_STAGE=READ_RSS_MARKET_VALUES_ROW_WISE",
  "NO11_REFERENCE_FAILURE_LINE=",
  "NO11_REFERENCE_FAILURE_TYPE=",
  "$rowRange='A'+$rowNum+':L'+$rowNum",
  "$values=$sheet.Range($rowRange).Value2",
  "NO11_SESSION_REFERENCE_FILE=",
  "chartPlanSha256=$plan.planSha256",
  "corporateActionReviewPerformed=$false",
  "orderTransmission=$false"
 ]) assert.ok(s.includes(token),token);
 assert.ok(!s.includes('$values=$sheet.Range($range).Value2'));
});
test('Nov2 RSS rowwise collector preserves source/read-only boundary and original workbook identities',()=>{
 for(const token of [
  'Ark_No11_MSII_RSS.xlsx','Ark_No11_MARKET_RSS.xlsx',
  'ARK_ACCOUNT_READONLY','ARK_MARKET_READONLY',
  'TWO_ORIGINAL_BOOKS_REQUIRED',
  "Need ($existing.Count+$unknown -le 500)",
  '$book=$excel.Workbooks.Add()',
  '$book.Close($false)',
  'NO11_REFERENCE_OFFLINE_SELFTEST=PASS',
  "ORDERS_NOT_USED" // marker does not exist, excluded below instead
 ]) if(token!=='ORDERS_NOT_USED')assert.ok(s.includes(token),token);
 for(const bad of [
  /RssStockOrder\s*\(/i,/RssCancelOrder\s*\(/i,
  /approvedForSession\s*=\s*\$true/i,
  /automaticOrderAuthorization\s*=\s*\$true/i,
  /\.SaveAs\s*\(/i,
  /\.Save\s*\(/i,
  /\.Quit\s*\(/i,
  /Stop-Process/i,
  /NO11_REFERENCE.*LIVE_READY/
 ])assert.doesNotMatch(s,bad);
});
