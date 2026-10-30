import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {assessYahooSymbol,assessYahooUniverse,YAHOO_SEED_SCHEMA,YAHOO_SOURCE}
 from '../tools/no11_yahoo_weekly_seed.mjs';
import {requiredDailySessions} from '../runtime/no11_rss_daily_trend_census.mjs';

const asof='2026-10-23';
const dates=requiredDailySessions(asof);
const sorted=dates.map((d,i)=>({session:d,close:String(i+100)}));
const standard=(symbol='7203.T')=>({
 schemaId:'ARK_NO11_YAHOO_WEEKLY_HISTORY_OBSERVATION_V1',
 symbol,asOfSession:asof,sourceProvider:YAHOO_SOURCE,
 sourceInterval:'1d',autoAdjustRequested:false,
 usesYahooCloseNotAdjClose:true,corporateActionPriceBasisCertified:false,
 splitAdjustmentCertified:false,originalVendorDecimalCertified:false,
 requestedAtJst:'2026-10-23T19:05:00.000+09:00',
 receivedAtJst:'2026-10-23T19:06:00.000+09:00',
 status:'OBSERVED',rows:sorted,
 productionReady:false,orderTransmission:false
});
test('Yahoo is an auditable DISTINCT weekly provider, never a forged RSS capture',()=>{
 assert.equal(YAHOO_SEED_SCHEMA,'ARK_NO11_YAHOO_WEEKLY_SOURCE_PLAN_V1');
 assert.equal(YAHOO_SOURCE,'YFINANCE_UNOFFICIAL_PERSONAL_RESEARCH_DAILY');
 const src=fs.readFileSync(new URL('../tools/no11_yahoo_weekly_seed.mjs',import.meta.url),'utf8');
 for(const t of ['SOURCE_FILES_NOT_FULL_4328','originalFrozenUniverse','ORIGINAL_4328_ACTUAL_SOURCE_INCOMPLETE',
  'ORIGINAL_4328_MASK_INVALID','YAHOO_UNKNOWN_COVERAGE_EXCEEDS_10_PERCENT',
  'sourceProvider:YAHOO_SOURCE','closeColumn:\'Close\'',
  'priceBasisCertified:false','corporateActionsCertified:false',
  'originalFrozenG1RulesModified:false','ORDER_TRANSMISSION=False'])
  assert.ok(src.includes(t),t);
 assert.doesNotMatch(src,/(?:RssStockOrder|RssCancelOrder)\s*\(|GetActiveObject\s*\(/);
});
test('original G1 5/15/25/75 is used with exact 76 sessions, not a new model',()=>{
 const r=assessYahooSymbol(standard(),dates,asof);
 assert.equal(r.status,'PASS');
 assert.equal(r.dailySmaUp[75],true);
 assert.equal(r.dailySmaUp[25],true);
 assert.equal(r.dailySmaUp[15],true);
 assert.equal(r.dailySmaUp[5],true);
 const r2=assessYahooUniverse({asOf:asof,symbols:['7203.T','6758.T'],
  payloads:[standard('7203.T'),{...standard('6758.T'),status:'UNAVAILABLE',rows:[]}]});
 assert.deepEqual(r2.passed,['7203.T']);
 assert.equal(r2.counts.UNKNOWN,1);
});
test('Yahoo close cannot silently pass when adjusted, stale, missing, duplicate or tainted',()=>{
 for(const bad of [
  {autoAdjustRequested:true},
  {splitAdjustmentCertified:true},
  {corporateActionPriceBasisCertified:true},
  {orderTransmission:true},
  {requestedAtJst:'2026-10-23T18:59:00.000+09:00'},
  {receivedAtJst:'2026-10-23T19:04:00.000+09:00'},
  {sourceProvider:'MSII_RSS'},
  {sourceInterval:'1m'},
  {rows:[...sorted,{...sorted[0]}]},
  {rows:[...sorted,{session:'2026-10-24',close:'123'}]},
  {rows:[...sorted.slice(0,-1),{session:dates.at(-1),close:'-1'}]},
 ])assert.throws(()=>assessYahooSymbol({...standard(),...bad},dates,asof),/NO11_YAHOO_SEED_/);
 assert.equal(assessYahooSymbol({...standard(),rows:sorted.slice(0,70)},dates,asof).status,'UNKNOWN');
});
