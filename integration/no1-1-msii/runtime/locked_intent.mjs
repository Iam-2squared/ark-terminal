/**
 * Mechanical, non-transmitting intake for an already-decided Ark Integrated No.1.1 action.
 * This is a NEW integration envelope, NOT a claim that the research branch emits it yet.
 * Never infer an action from research score, trace, or historical reference fill.
 */
import {createHash} from 'node:crypto';

export const FREEZE_HEAD = '10c94c92c4bd2a59a22744667fd0210252602df4';
export const FREEZE_VERSION = '1.1.0-RESEARCH-FROZEN';
export const DECISION_SCHEMA = 'ARK_NO11_LOCKED_DECISION_EXPORT_V1';
export const INTENT_SCHEMA = 'ARK_NO11_CASH_LOCKED_INTENT_V1';

export const LOCKED_FLAGS = Object.freeze({
  executionAllowed:false, brokerWriteAllowed:false, excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false, liveTradingAllowed:false, paperTradingAllowed:false,
  automaticPromotionAllowed:false, productionUpdateAllowed:false, transmitted:false,
  productionReady:false,
});

export function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value !== null && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map(k => [k, canonical(value[k])]));
  }
  return value;
}
export const digest = v => createHash('sha256').update(JSON.stringify(canonical(v))).digest('hex');
const fail = name => { throw Error(name); };
const nonempty = (s,name) => typeof s === 'string' && s.trim() !== '' ? s.trim() : fail(name);
const sha = (s,name) => typeof s === 'string' && /^[a-f0-9]{64}$/.test(s) ? s : fail(name);
const qty = (n,name) => Number.isSafeInteger(n) && n>0 && n%100===0 ? n : fail(name);
const timestamp = (s,name) => {
  if(typeof s!=='string' || !/(?:Z|[+-]\d{2}:\d{2})$/.test(s) || !Number.isFinite(Date.parse(s))) fail(name);
  return Date.parse(s);
};
const tokyoDay = ms => new Intl.DateTimeFormat('en-CA', {
  timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit'
}).format(new Date(ms)).replace(/\//g,'-');

function validateSymbolMap(sourceSymbol, mapping) {
  if (!Array.isArray(mapping)) fail('SYMBOL_MAP_ARRAY_REQUIRED');
  const source=nonempty(sourceSymbol,'SOURCE_SYMBOL_REQUIRED').toUpperCase();
  const matches=mapping.filter(row => row?.sourceSymbol===source);
  if(matches.length!==1) fail('SYMBOL_MAP_UNRESOLVED_OR_AMBIGUOUS');
  const row=matches[0];
  const broker=nonempty(row.brokerSymbol,'BROKER_SYMBOL_REQUIRED').toUpperCase();
  if(!/^[0-9A-Z]{4}\.T$/.test(broker)) fail('BROKER_SYMBOL_FORMAT_INVALID');
  if(row.verified!==true || row.authority!=='DATED_SECURITY_MASTER_AND_MSII') fail('SYMBOL_MAP_NOT_VERIFIED');
  timestamp(row.verifiedAt,'SYMBOL_MAP_VERIFIED_AT_INVALID');
  if(!/^(?:[0-9A-Z]{5}|[0-9A-Z]{4}\.T)$/.test(source)) fail('SOURCE_SYMBOL_FORMAT_INVALID');
  if(mapping.some(other=>other!==row && other?.brokerSymbol===broker && other?.verified===true)) {
    fail('BROKER_SYMBOL_MAPPING_COLLISION');
  }
  return {brokerSymbol:broker, sourceSymbol:source, mappingProof:sha(row.mappingProofSha256,'SYMBOL_MAPPING_PROOF_REQUIRED')};
}

function validateSafety(safety) {
  if(!safety || typeof safety!=='object') fail('SOURCE_SAFETY_REQUIRED');
  for(const [key,value] of Object.entries(LOCKED_FLAGS)) {
    if(safety[key]!==value) fail('SOURCE_SAFETY_NOT_LOCKED:'+key);
  }
}
function verifyDecisionEnvelope(decision) {
  if(!decision || typeof decision!=='object' || Array.isArray(decision)) fail('DECISION_OBJECT_REQUIRED');
  if(decision.schemaId!==DECISION_SCHEMA) fail('DECISION_SCHEMA_REQUIRED');
  const {decisionSha256,...core}=decision;
  if(sha(decisionSha256,'DECISION_HASH_REQUIRED')!==digest(core)) fail('DECISION_HASH_MISMATCH');
  if(decision.strategyFreezeCommit!==FREEZE_HEAD || decision.strategyVersion!==FREEZE_VERSION) fail('FROZEN_STRATEGY_IDENTITY_MISMATCH');
  validateSafety(decision.safety);
  if(decision.evidenceMode!=='SYNTHETIC' && decision.evidenceMode!=='LIVE_ATTESTED') fail('EVIDENCE_MODE_REQUIRED');
  if(decision.evidenceMode==='LIVE_ATTESTED') {
    nonempty(decision.liveSourceReceiptId,'LIVE_SOURCE_RECEIPT_REQUIRED');
    if(decision.liveSourceCertified!==true) fail('LIVE_SOURCE_NOT_CERTIFIED');
  } else if(decision.liveSourceCertified===true) fail('SYNTHETIC_CANNOT_BE_LIVE_CERTIFIED');
  return core;
}

/**
 * No order defaults. All action values are frozen upstream values or explicit
 * separately-verified venue configuration. The adapter can only reject.
 */
export function makeLockedIntent(decision, {symbolMap}={}) {
  verifyDecisionEnvelope(decision);
  const eventId=nonempty(decision.eventId,'SOURCE_EVENT_ID_REQUIRED');
  const intentId=nonempty(decision.intentId,'SOURCE_INTENT_ID_REQUIRED');
  const strategyId=nonempty(decision.strategyId,'STRATEGY_ID_REQUIRED');
  const session=nonempty(decision.session,'TRADING_SESSION_REQUIRED');
  if(!/^\d{4}-\d{2}-\d{2}$/.test(session)) fail('TRADING_SESSION_INVALID');
  const decisionAt=timestamp(decision.decisionAt,'DECISION_AT_INVALID');
  const knownAt=timestamp(decision.sourceKnownAt,'SOURCE_KNOWN_AT_INVALID');
  if(knownAt>decisionAt) fail('FUTURE_INFORMATION_USED');
  if(tokyoDay(decisionAt)!==session) fail('SESSION_TIMESTAMP_MISMATCH');
  const symbol=validateSymbolMap(decision.sourceSymbol,symbolMap);
  const direction=nonempty(decision.direction,'DIRECTION_REQUIRED');
  if(direction!=='LONG') fail('CASH_LONG_ONLY');
  const kind=nonempty(decision.intentKind,'INTENT_KIND_REQUIRED');
  const side=nonempty(decision.side,'SIDE_REQUIRED');
  const effect=nonempty(decision.positionEffect,'POSITION_EFFECT_REQUIRED');
  if(!((kind==='ENTRY'&&side==='BUY'&&effect==='OPEN')||(kind==='EXIT'&&side==='SELL'&&effect==='CLOSE'))) {
    fail('LONG_SIDE_EFFECT_MISMATCH');
  }
  if(decision.admission!=='APPROVED_BY_FROZEN_NO11') fail('UPSTREAM_FROZEN_ADMISSION_REQUIRED');
  const quantity=qty(decision.quantity,'CASH_100_LOT_REQUIRED');
  const orderType=nonempty(decision.orderType,'ORDER_TYPE_REQUIRED');
  if(!['MARKET','LIMIT'].includes(orderType)) fail('ORDER_TYPE_NOT_SUPPORTED');
  const limitPrice=decision.limitPrice;
  if(orderType==='MARKET' && limitPrice!==null) fail('MARKET_MUST_NOT_HAVE_LIMIT');
  if(orderType==='LIMIT' && (!Number.isFinite(limitPrice)||limitPrice<=0)) fail('LIMIT_PRICE_INVALID');
  if(decision.timeInForce!=='DAY') fail('DAY_ORDERS_ONLY');
  if(typeof decision.sor!=='boolean') fail('SOR_NOT_EXPLICIT');
  if(!Number.isInteger(decision.accountType) || decision.accountType<0 || decision.accountType>3) fail('ACCOUNT_TYPE_INVALID');
  if(decision.accountTypeVerified!==true) fail('ACCOUNT_TYPE_NOT_VERIFIED');
  sha(decision.frozenEventSourceSha256,'FROZEN_EVENT_SOURCE_HASH_REQUIRED');
  if(kind==='ENTRY') {
    if(decision.stateObserved!==true) fail('ENTRY_STATE_UNAVAILABLE');
    const state=nonempty(decision.formalState9Primary,'FORMAL_ENTRY_STATE_REQUIRED');
    if(state==='PULLBACK'||state==='SHARP_DROP') fail('NO11_ENTRY_STATE_EXCLUDED');
    const stateKnownAt=timestamp(decision.stateKnownAt,'STATE_KNOWN_AT_REQUIRED');
    if(stateKnownAt>decisionAt) fail('FUTURE_STATE_USED');
    if(decision.entryBefore1520!==true) fail('FROZEN_ENTRY_TIME_GATE_REQUIRED');
    const jstClock=new Intl.DateTimeFormat('en-GB',{
      timeZone:'Asia/Tokyo',hour:'2-digit',minute:'2-digit',hourCycle:'h23'
    }).format(new Date(decisionAt));
    if(jstClock>='15:20') fail('CASH_ENTRY_CUTOFF_1520');
  }
  const core={
    schemaId:INTENT_SCHEMA,originSchemaId:DECISION_SCHEMA,
    strategyFreezeCommit:FREEZE_HEAD,strategyVersion:FREEZE_VERSION,
    evidenceMode:decision.evidenceMode,sourceEventId:eventId,sourceIntentId:intentId,
    strategyId,session,decisionAt:decision.decisionAt,sourceKnownAt:decision.sourceKnownAt,
    sourceSymbol:symbol.sourceSymbol,symbol:symbol.brokerSymbol,
    symbolMappingProofSha256:symbol.mappingProof,
    direction:'LONG',side,positionEffect:effect,quantity,orderType,
    limitPrice,timeInForce:'DAY',sor:decision.sor,accountType:decision.accountType,
    sourceDecisionSha256:decision.decisionSha256,
    frozenEventSourceSha256:decision.frozenEventSourceSha256,
    executable:false,transmitted:false,cashOnly:true,
    marginAllowed:false,shortSellingAllowed:false,marginFallbackAllowed:false,
    safety:LOCKED_FLAGS,
  };
  return Object.freeze({...core,lockedIntentSha256:digest(core)});
}

export function sealSyntheticDecision(core) {
  if(core?.evidenceMode!=='SYNTHETIC') fail('SYNTHETIC_ONLY_HELPER');
  return {...core,decisionSha256:digest(core)};
}
