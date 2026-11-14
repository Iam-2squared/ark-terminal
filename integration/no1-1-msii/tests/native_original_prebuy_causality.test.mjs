import test from 'node:test';
import assert from 'node:assert/strict';
import {
  assertFrozenOriginalCore,auditOriginalPreBuyCausality,POST_FILL_FEATURES
} from '../runtime/native_original_prebuy_causality.mjs';
const args=()=>({stage:'BEFORE_BUY_FILL',decisionAt:'2026-10-13T09:36:00+09:00',
  now:new Date('2026-10-13T09:36:01+09:00')});
test('byte-exact Frozen original uses three post-fill dependent features',()=>{
 assert.equal(assertFrozenOriginalCore(),true);
 assert.deepEqual(POST_FILL_FEATURES,[
  'entry/fill_clock','entry/intent_to_fill_active_delay',
  'selector/raw_entry_vs_first_price_pct'
 ]);
});
test('before BUY fill, original frozen rank cannot be certified from realized fill data',()=>{
 const r=auditOriginalPreBuyCausality(args());
 assert.equal(r.status,'ORIGINAL_PRE_BUY_RANK_CAUSALITY_NOT_PROVEN');
 assert.equal(r.liveDecisionPublished,false);
 assert.equal(r.preBuyFrozenRankCertified,false);
 assert.equal(r.orderTransmission,false);
});
test('fabricated pre-buy observed fill timestamps cannot override stage',()=>{
 const times=Object.fromEntries(POST_FILL_FEATURES.map(k=>[k,'2026-10-13T09:35:01+09:00']));
 const r=auditOriginalPreBuyCausality({...args(),confirmedFillAt:'2026-10-13T09:35:00+09:00',
  featureKnownTimes:times});
 assert.equal(r.preBuyFrozenRankCertified,false);
});
test('post-filled feature chronology is monitoring-only, not a BUY trigger',()=>{
 const r=auditOriginalPreBuyCausality({
  ...args(),stage:'AFTER_CONFIRMED_BUY_FILL',
  confirmedFillAt:'2026-10-13T09:35:00+09:00',
  featureKnownTimes:Object.fromEntries(POST_FILL_FEATURES.map(k=>[k,'2026-10-13T09:35:01+09:00']))
 });
 assert.equal(r.status,'POST_FILL_CHRONOLOGY_OBSERVED_NOT_PRE_BUY');
 assert.equal(r.preBuyFrozenRankCertified,false);
 assert.equal(r.productionReady,false);
});
test('future fill, delayed postfill features, missing source time all fail',()=>{
 const base={...args(),stage:'AFTER_CONFIRMED_BUY_FILL',
  confirmedFillAt:'2026-10-13T09:35:00+09:00',
  featureKnownTimes:Object.fromEntries(POST_FILL_FEATURES.map(k=>[k,'2026-10-13T09:35:01+09:00']))};
 assert.throws(()=>auditOriginalPreBuyCausality({...base,confirmedFillAt:'2026-10-13T09:37:00+09:00'}),/FILL_NOT_YET/);
 assert.throws(()=>auditOriginalPreBuyCausality({...base,featureKnownTimes:{...base.featureKnownTimes,
  'entry/fill_clock':'2026-10-13T09:36:09+09:00'}}),/POSTFILL_CHRONOLOGY_INVALID/);
 const values={...base.featureKnownTimes};delete values['entry/fill_clock'];
 assert.throws(()=>auditOriginalPreBuyCausality({...base,featureKnownTimes:values}),/POSTFILL_KNOWN_TIME_MISSING/);
});
