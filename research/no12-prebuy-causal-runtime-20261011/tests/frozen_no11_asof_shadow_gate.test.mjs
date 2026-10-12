import test from 'node:test';
import assert from 'node:assert/strict';
import {
  inspectFrozenNo11AsOfShadowInputs as inspect,
  NO11_ASOF_GATE_SCHEMA as SCHEMA,NO11_FROZEN_ID as FROZEN,
  NO11_SHADOW_AGE_LIMITS as LIMITS
} from '../runtime/frozen_no11_asof_shadow_gate.mjs';
const s='7203.T',pin='a'.repeat(64);
const at=t=>'2026-10-13T'+t+'+09:00';
const source=(kind,t,received,known,extras={})=>({
  kind,symbol:s,sourceAsOf:at(t),receivedAt:at(received),
  knownAt:at(known),receiptSha256:'b'.repeat(64),...extras
});
function fixture(){
 const snapshot={
  schemaId:SCHEMA,frozenId:FROZEN,evidenceMode:'OBSERVED_READ_ONLY',
  session:'2026-10-13',symbol:s,decisionAt:at('09:35:10'),
  capturedAt:at('09:35:10'),productionReady:false,orderTransmission:false,
  selector:source('FROZEN_SELECTOR_EVENT','09:30:00','09:30:02','09:30:03',{
    eventId:'2026-10-13|09:30|7203',modelArtifactSha256:pin
  }),
  firstEntry:source('FROZEN_FIRST_ENTRY_INTENT','09:35:00','09:35:02','09:35:03',{
    barClosedAt:at('09:35:00'),intentAt:at('09:35:00'),score:0.78,threshold:0.70
  }),
  state9:source('FROZEN_NATIVE_STATE9_CLOSED','09:35:00','09:35:03','09:35:04',{
    barClosedAt:at('09:35:00'),primary:'RISE'
  }),
  market:source('MARKETSPEED_II_RSS_MARKET_OBSERVATION','09:35:08','09:35:09','09:35:09',{
    priceAsOf:at('09:35:08'),lastPrice:1250
  })
 };
 return {mode:'SYNTHETIC_OFFLINE_ONLY',snapshot,now:new Date(at('09:35:11'))};
}
const rejects=(mutate,pattern)=>{
 const x=fixture();mutate(x);
 assert.throws(()=>inspect(x),pattern);
};
test('accepts only causal source-time inputs and remains non-executable',()=>{
 const r=inspect(fixture());
 assert.equal(r.status,'ASOF_SOURCE_TIMELINE_ACCEPTED_RESEARCH_ONLY');
 assert.equal(r.observedPrice,1250);
 assert.equal(r.originalFrozenModelsExecuted,false);
 assert.equal(r.originalFrozenSelectorIdentityCertified,false);
 assert.equal(r.featureAdaptationRequired,true);
 assert.equal(r.historicalFillPriceUsed,false);
 assert.equal(r.productionReady,false);
 assert.equal(r.orderTransmission,false);
 assert.match(r.resultSha256,/^[a-f0-9]{64}$/);
});
test('persistent Selector event is NOT incorrectly expired after five minutes',()=>{
 const x=fixture();
 x.snapshot.selector=source('FROZEN_SELECTOR_EVENT','09:00:00','09:00:03','09:00:04',{
  eventId:'2026-10-13|09:00|7203',modelArtifactSha256:pin
 });
 const r=inspect(x);
 assert.equal(r.selectorWatchPersistsUntilSessionClose,true);
});
test('future quote, future knownAt and future state are all rejected',()=>{
 rejects(x=>x.snapshot.market.sourceAsOf=at('09:36:00'),/ASOF_FUTURE_OR_CROSS_SESSION_SOURCE/);
 rejects(x=>x.snapshot.state9.knownAt=at('09:35:12'),/ASOF_FUTURE_OR_CROSS_SESSION_SOURCE/);
 rejects(x=>x.snapshot.state9.barClosedAt=at('09:36:00'),/ASOF_UNCLOSED_BAR_OR_LABEL_AMBIGUOUS/);
});
test('local PC first-seen must not predate the claimed source event',()=>{
 rejects(x=>x.snapshot.market.receivedAt=at('09:35:06'),/ASOF_FUTURE_OR_CROSS_SESSION_SOURCE/);
 rejects(x=>x.snapshot.market.knownAt=at('09:35:07'),/ASOF_FUTURE_OR_CROSS_SESSION_SOURCE/);
});
test('market and formal State9 source freshness are independently checked',()=>{
 rejects(x=>{
  x.snapshot.market.sourceAsOf=at('09:34:30');
  x.snapshot.market.priceAsOf=at('09:34:30');
 },/ASOF_SOURCE_TOO_OLD/);
 rejects(x=>x.snapshot.state9.sourceAsOf=at('09:33:00'),/ASOF_SOURCE_TOO_OLD/);
 assert.equal(LIMITS.rssPriceMs,30000);
 assert.equal(LIMITS.state9BarMs,90000);
});
test('First Entry score and threshold cannot be silently bypassed',()=>{
 rejects(x=>x.snapshot.firstEntry.score=0.6,/ASOF_FIRST_ENTRY_NOT_TRIGGERED/);
 rejects(x=>x.snapshot.firstEntry.threshold=0,/ASOF_FIRST_ENTRY_SCORE_INVALID/);
 rejects(x=>x.snapshot.firstEntry.score=NaN,/ASOF_FIRST_ENTRY_SCORE_INVALID/);
 rejects(x=>x.snapshot.firstEntry.intentAt=at('09:35:20'),/ASOF_FIRST_ENTRY_INTENT_CHRONOLOGY_INVALID/);
});
test('stale intent is rejected without mutating original First Entry',()=>{
 rejects(x=>{
  x.snapshot.firstEntry=source('FROZEN_FIRST_ENTRY_INTENT','09:32:00','09:32:02','09:32:03',{
    barClosedAt:at('09:32:00'),intentAt:at('09:32:00'),score:0.8,threshold:0.7
  });
 },/ASOF_FIRST_ENTRY_INTENT_EXPIRED/);
});
test('original frozen PULLBACK and SHARP_DROP entry exclusions are preserved',()=>{
 rejects(x=>x.snapshot.state9.primary='PULLBACK',/ASOF_FROZEN_ENTRY_STATE_EXCLUDED/);
 rejects(x=>x.snapshot.state9.primary='SHARP_DROP',/ASOF_FROZEN_ENTRY_STATE_EXCLUDED/);
 rejects(x=>x.snapshot.state9.primary='NOT_A_NATIVE_STATE',/ASOF_FORMAL_STATE9_MISSING/);
});
test('no actual fill, archived fill, teacher or future High may enter prebuy envelope',()=>{
 for(const k of ['fill_price','fill_timestamp','fill_minute','historical_future_open',
    'future_high','teacher_outcome','entry/fill_clock','entry/intent_to_fill_active_delay']){
  rejects(x=>x.snapshot.market[k]=1000,/ASOF_POSTFILL_OR_TEACHER_FEATURE_FORBIDDEN/);
 }
 rejects(x=>x.snapshot.firstEntry.metadata={fill_price:1234},
  /ASOF_POSTFILL_OR_TEACHER_FEATURE_FORBIDDEN/);
});
test('non-frozen identity, live mode and unverified certification claims are blocked',()=>{
 rejects(x=>x.mode='LIVE_TRADING',/ASOF_LIVE_EXECUTION_FORBIDDEN/);
 rejects(x=>x.snapshot.frozenId='ARK_NO12_ALTERNATIVE_RANK',/ASOF_SNAPSHOT_CONTRACT_INVALID/);
 rejects(x=>x.snapshot.market.brokerArrivalCertified=true,/ASOF_UNVERIFIED_CERTIFICATION_CLAIM/);
 rejects(x=>x.snapshot.productionReady=true,/ASOF_SNAPSHOT_CONTRACT_INVALID/);
});
test('symbol mismatch, session mismatch, stale decision and bad source pins fail',()=>{
 rejects(x=>x.snapshot.state9.symbol='6758.T',/ASOF_SOURCE_KIND_OR_SYMBOL_INVALID/);
 rejects(x=>x.snapshot.session='2026-10-12',/ASOF_SESSION_INVALID/);
 rejects(x=>x.now=new Date(at('09:36:00')),/ASOF_DECISION_STALE_OR_FUTURE/);
 rejects(x=>x.snapshot.selector.modelArtifactSha256='not-sha',/ASOF_HASH_INVALID/);
});
test('an exchange timestamp alone cannot be passed off as PC first-seen proof',()=>{
 rejects(x=>delete x.snapshot.market.receivedAt,/ASOF_PC_FIRST_SEEN_INVALID/);
 rejects(x=>delete x.snapshot.firstEntry.barClosedAt,/ASOF_NATIVE_CLOSED_BAR_PROOF_REQUIRED/);
 rejects(x=>x.snapshot.market.priceAsOf=at('09:35:07'),/ASOF_MARKET_PRICE_SOURCE_TIME_MISMATCH/);
});
test('gate has no Excel, broker, order or networking operations',async()=>{
 const fs=await import('node:fs');
 const src=fs.readFileSync(new URL('../runtime/frozen_no11_asof_shadow_gate.mjs',import.meta.url),'utf8');
 for(const pattern of [/RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,/Excel.Application/,
    /\bfetch\s*\(/,/productionReady\s*:\s*true/,/orderTransmission\s*:\s*true/])
  assert.doesNotMatch(src,pattern);
});
