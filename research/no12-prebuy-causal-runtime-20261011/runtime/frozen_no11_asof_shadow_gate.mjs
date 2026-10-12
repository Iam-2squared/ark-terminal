/**
 * Original No.1.1 as-of INPUT timeline gate. Synthetic/offline Shadow ONLY.
 * Original Selector/First Entry/State9/24 models/Capital/EXIT are NOT changed.
 * This validates claimed local PC first-seen times, not broker arrival proof.
 */
import {createHash} from 'node:crypto';
export const NO11_ASOF_GATE_SCHEMA='ARK_NO11_ASOF_SHADOW_INPUT_V1';
export const NO11_FROZEN_ID='ARK_INTEGRATED_NO1_V5_SHARP_DROP_FREEZE_20261008';
// Provisional Shadow engineering limits; NOT Frozen trading thresholds.
export const NO11_SHADOW_AGE_LIMITS=Object.freeze({
  firstEntryIntentMs:90000,state9BarMs:90000,
  rssPriceMs:30000,decisionSnapshotMs:30000
});
const fail=reason=>{throw Error(reason)};
const iso=(s,reason)=>{
  if(typeof s!=='string'||!/^20\d{2}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(s))
    fail(reason);
  const v=Date.parse(s);
  if(!Number.isFinite(v))fail(reason);
  return v;
};
const day=ms=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tokyo',
  year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(ms)).replace(/\//g,'-');
const sha=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
const code=x=>{
  if(typeof x!=='string'||!/^[0-9A-Z]{4}\.T$/.test(x))fail('ASOF_SYMBOL_INVALID');
  return x;
};
const hex=x=>{
  if(typeof x!=='string'||!/^[0-9a-f]{64}$/.test(x))fail('ASOF_HASH_INVALID');
  return x;
};
const allowedStates=new Set(['RISE_STOP','RISE','SHARP_RISE','RANGE','REBOUND',
  'DROP','DROP_STOP','PULLBACK','SHARP_DROP']);
const forbiddenKey=/^(?:fill_price|fill_timestamp|fill_minute|actual_fill_price|actual_fill_time|historical_future_open|future_high|teacher_outcome|entry\/fill_clock|entry\/intent_to_fill_active_delay|selector\/raw_entry_vs_first_price_pct)$/i;
function rejectPostFillKeys(obj,depth=0){
  if(depth>8)fail('ASOF_SOURCE_NESTING_EXCESSIVE');
  if(!obj||typeof obj!=='object')return;
  for(const [k,v] of Object.entries(obj)){
    if(forbiddenKey.test(k))fail('ASOF_POSTFILL_OR_TEACHER_FEATURE_FORBIDDEN');
    if(v&&typeof v==='object')rejectPostFillKeys(v,depth+1);
  }
}
function checkedSource(source,kind,symbol,decision,session,limitMs=null){
  if(!source||typeof source!=='object'||Array.isArray(source)||
    source.kind!==kind||code(source.symbol)!==symbol)
    fail('ASOF_SOURCE_KIND_OR_SYMBOL_INVALID');
  const asOf=iso(source.sourceAsOf,'ASOF_SOURCE_ASOF_INVALID');
  const received=iso(source.receivedAt,'ASOF_PC_FIRST_SEEN_INVALID');
  const known=iso(source.knownAt,'ASOF_SOURCE_KNOWN_INVALID');
  if(asOf>received||received>known||known>decision||
    asOf>decision||day(asOf)!==session||day(known)!==session)
    fail('ASOF_FUTURE_OR_CROSS_SESSION_SOURCE');
  if(limitMs!==null&&decision-asOf>limitMs)
    fail('ASOF_SOURCE_TOO_OLD');
  if(source.barClosedAt!==undefined){
    const closed=iso(source.barClosedAt,'ASOF_BAR_CLOSED_INVALID');
    if(closed>asOf||closed>received||day(closed)!==session)
      fail('ASOF_UNCLOSED_BAR_OR_LABEL_AMBIGUOUS');
  }
  if(source.receiptSha256!==undefined)hex(source.receiptSha256);
  if(source.brokerArrivalCertified===true||source.productionReady===true||
    source.orderTransmission===true||source.liveOrderEnabled===true)
    fail('ASOF_UNVERIFIED_CERTIFICATION_CLAIM');
  return Object.freeze({asOf,received,known});
}
export function inspectFrozenNo11AsOfShadowInputs({
 mode,snapshot,now=new Date()
}={}){
  if(mode!=='SYNTHETIC_OFFLINE_ONLY')
    fail('ASOF_LIVE_EXECUTION_FORBIDDEN');
  if(snapshot?.schemaId!==NO11_ASOF_GATE_SCHEMA||
    snapshot.frozenId!==NO11_FROZEN_ID||
    snapshot.evidenceMode!=='OBSERVED_READ_ONLY'||
    snapshot.productionReady!==false||snapshot.orderTransmission!==false)
    fail('ASOF_SNAPSHOT_CONTRACT_INVALID');
  rejectPostFillKeys(snapshot);
  const symbol=code(snapshot.symbol);
  const decision=iso(snapshot.decisionAt,'ASOF_DECISION_INVALID');
  const captured=iso(snapshot.capturedAt,'ASOF_CAPTURE_INVALID');
  const current=now instanceof Date?now.getTime():iso(now,'ASOF_NOW_INVALID');
  if(!Number.isFinite(current)||decision>captured||captured>current+1000||
    current-decision>NO11_SHADOW_AGE_LIMITS.decisionSnapshotMs)
    fail('ASOF_DECISION_STALE_OR_FUTURE');
  const session=day(decision);
  if(snapshot.session!==session)fail('ASOF_SESSION_INVALID');
  const selector=checkedSource(snapshot.selector,'FROZEN_SELECTOR_EVENT',
    symbol,decision,session);
  const entry=checkedSource(snapshot.firstEntry,'FROZEN_FIRST_ENTRY_INTENT',
    symbol,decision,session);
  const state=checkedSource(snapshot.state9,'FROZEN_NATIVE_STATE9_CLOSED',
    symbol,decision,session,NO11_SHADOW_AGE_LIMITS.state9BarMs);
  const market=checkedSource(snapshot.market,'MARKETSPEED_II_RSS_MARKET_OBSERVATION',
    symbol,decision,session,NO11_SHADOW_AGE_LIMITS.rssPriceMs);
  if(!snapshot.state9.barClosedAt||!snapshot.firstEntry.barClosedAt)
    fail('ASOF_NATIVE_CLOSED_BAR_PROOF_REQUIRED');
  if(typeof snapshot.selector.eventId!=='string'||
    !/^[A-Za-z0-9_.:|-]{1,160}$/.test(snapshot.selector.eventId))
    fail('ASOF_SELECTOR_EVENT_ID_INVALID');
  const intent=iso(snapshot.firstEntry.intentAt,'ASOF_INTENT_INVALID');
  if(intent<selector.asOf||intent>entry.known||intent>decision||
    entry.asOf>intent||state.asOf>decision)
    fail('ASOF_FIRST_ENTRY_INTENT_CHRONOLOGY_INVALID');
  if(decision-intent>NO11_SHADOW_AGE_LIMITS.firstEntryIntentMs)
    fail('ASOF_FIRST_ENTRY_INTENT_EXPIRED');
  if(typeof snapshot.firstEntry.score!=='number'||
    !Number.isFinite(snapshot.firstEntry.score)||
    typeof snapshot.firstEntry.threshold!=='number'||
    !Number.isFinite(snapshot.firstEntry.threshold)||
    snapshot.firstEntry.threshold<=0)
    fail('ASOF_FIRST_ENTRY_SCORE_INVALID');
  if(snapshot.firstEntry.score<snapshot.firstEntry.threshold)
    fail('ASOF_FIRST_ENTRY_NOT_TRIGGERED');
  if(!allowedStates.has(snapshot.state9.primary))
    fail('ASOF_FORMAL_STATE9_MISSING');
  if(snapshot.state9.primary==='PULLBACK'||snapshot.state9.primary==='SHARP_DROP')
    fail('ASOF_FROZEN_ENTRY_STATE_EXCLUDED');
  if(typeof snapshot.market.lastPrice!=='number'||
    !Number.isFinite(snapshot.market.lastPrice)||snapshot.market.lastPrice<=0)
    fail('ASOF_MARKET_PRICE_INVALID');
  if(snapshot.market.priceAsOf!==snapshot.market.sourceAsOf)
    fail('ASOF_MARKET_PRICE_SOURCE_TIME_MISMATCH');
  if(typeof snapshot.selector.modelArtifactSha256!=='string')
    fail('ASOF_SELECTOR_MODEL_PIN_MISSING');
  hex(snapshot.selector.modelArtifactSha256);
  const result={
    schemaId:'ARK_NO11_ASOF_SHADOW_INPUT_RESULT_V1',
    status:'ASOF_SOURCE_TIMELINE_ACCEPTED_RESEARCH_ONLY',
    session,symbol,decisionAt:snapshot.decisionAt,frozenId:NO11_FROZEN_ID,
    sourceReceiptSummarySha256:sha([
      snapshot.selector.receiptSha256??null,
      snapshot.firstEntry.receiptSha256??null,
      snapshot.state9.receiptSha256??null,
      snapshot.market.receiptSha256??null
    ]),
    sourceTimes:Object.freeze({
      selectorKnownAt:snapshot.selector.knownAt,
      firstEntryKnownAt:snapshot.firstEntry.knownAt,
      state9KnownAt:snapshot.state9.knownAt,
      marketKnownAt:snapshot.market.knownAt
    }),
    observedPrice:snapshot.market.lastPrice,
    firstEntryScore:snapshot.firstEntry.score,
    firstEntryThreshold:snapshot.firstEntry.threshold,
    formalState9Primary:snapshot.state9.primary,
    frozenSelectorModelPinObserved:snapshot.selector.modelArtifactSha256,
    firstEntryIntentAt:snapshot.firstEntry.intentAt,
    selectorWatchPersistsUntilSessionClose:true,
    originalFrozenModelsExecuted:false,
    originalFrozenSelectorIdentityCertified:false,
    actualBrokerArrivalCertified:false,
    dataLicensingCertified:false,
    liveOrderReconciliationCertified:false,
    historicalFillPriceUsed:false,
    featureAdaptationRequired:true,
    productionReady:false,orderTransmission:false
  };
  return Object.freeze({...result,resultSha256:sha(result)});
}
