import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {auditReference,previousCashDay} from '../tools/no11_reference_fields_diagnostic.mjs';
const day='2026-10-27',prev='2026-10-26';
function fixture(){
 const selectedSymbols=Array.from({length:47},(_,i)=>String(1000+i)+'.T');
 return {
  schemaId:'ARK_NO11_RSS_SESSION_REFERENCE_CAPTURE_V1',
  source:'RssMarket_SELECTED_REFERENCE_READONLY',sessionDate:day,
  readOnly:true,corporateActionReviewPerformed:false,
  productionReady:false,orderTransmission:false,
  capturedAtJst:day+'T10:02:01.000+09:00',
  completedAtJst:day+'T10:02:05.000+09:00',
  selectedSymbols,rows:selectedSymbols.map(symbol=>({
   symbol,marketCode:'T',marketDate:day,previousDate:prev,
   previousClose:1234,dayBasePrice:1234,marketSection:'東証P',lotShares:100
  }))
 };
}
test('checks actual prior JPX cash session, never guesses previous calendar day',()=>{
 assert.equal(previousCashDay('2026-10-27'),'2026-10-26');
 assert.equal(previousCashDay('2026-10-26'),'2026-10-23');
 assert.equal(previousCashDay('2026-10-29'),'2026-10-28');
 assert.throws(()=>previousCashDay('2026-10-25'),/TARGET_NOT_CASH_SESSION/);
});
test('complete RSS reference never authorizes corporate review or Shadow',()=>{
 const r=auditReference(fixture(),day);
 assert.equal(r.completeRows,47);
 assert.equal(r.status,'FIELDS_PRESENT_NOT_EXTERNALLY_REVIEWED');
 assert.equal(r.expectedPreviousSession,prev);
 assert.equal(r.independentCorporateReview,false);
 assert.equal(r.datedMasterCreated,false);
 assert.equal(r.shadowPreflightPassed,false);
 assert.equal(r.orderTransmission,false);
});
test('single missing field exposes the real failing field without fabricated defaults',()=>{
 const x=fixture();
 for(const row of x.rows)row.marketSection='東証プライム';
 x.rows[0].previousClose=null;
 const r=auditReference(x,day);
 assert.equal(r.completeRows,0);
 assert.equal(r.present.MARKET_SECTION_RECOGNIZED,0);
 assert.equal(r.present.PREVIOUS_CLOSE_POSITIVE,46);
 assert.equal(r.present.PREVIOUS_DATE_CASH_SESSION,47);
 assert.equal(r.missingRows,47);
 assert.equal(r.orderTransmission,false);
});
test('wrong day, modified scope and unreviewed safety flags fail closed',()=>{
 const x=fixture();
 assert.throws(()=>auditReference(x,'2026-10-28'),/UNREVIEWED_SOURCE/);
 x.rows[1].symbol=x.rows[0].symbol;
 assert.throws(()=>auditReference(x,day),/SYMBOL_SCOPE_OR_ORDER/);
 const y=fixture();y.corporateActionReviewPerformed=true;
 assert.throws(()=>auditReference(y,day),/UNREVIEWED_SOURCE/);
});
test('diagnostic code is read-only, no fake review, Excel or order dispatch',()=>{
 const code=fs.readFileSync(new URL('../tools/no11_reference_fields_diagnostic.mjs',import.meta.url),'utf8');
 for(const marker of [
  /RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,/GetActiveObject\s*\(/,
  /writeFileSync\s*\(/,/renameSync\s*\(/,/EXTERNALLY_REVIEWED['"]\s*:/,
  /orderTransmission\s*:\s*true/,
 ])assert.doesNotMatch(code,marker);
});
