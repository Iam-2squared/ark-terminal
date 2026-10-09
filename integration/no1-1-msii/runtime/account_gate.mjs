/**
 * Pure read-only MSII account admission. Fail closed on missing / stale / malformed
 * source evidence, broker position ambiguity, and pending/partial orders.
 * Never changes the Frozen strategy or performs an RSS/Excel operation.
 */
import {LOCKED_FLAGS,digest} from './locked_intent.mjs';

const BROKER_SOURCE='MARKETSPEED_II_RSS';
const BASELINE_SCHEMA='ARK_CASH_OWNERSHIP_BASELINE_V1';
const REQUIRED_FEEDS=Object.freeze({
  capacity:'完了',orders:'配信中',executions:'配信中',positions:'配信中'
});
const die=s=>{throw Error(s)};
function ms(s,label){
  if(typeof s!=='string'||!/(Z|[+-]\d{2}:\d{2})$/.test(s)||!Number.isFinite(Date.parse(s)))die(label);
  return Date.parse(s);
}
function symbol(s,label){
  if(typeof s!=='string')die(label);
  const x=s.trim().toUpperCase();
  if(!/^[0-9A-Z]{4}(?:\.T)?$/.test(x))die(label);
  return x.endsWith('.T')?x:x+'.T';
}
function quantity(q,label){
  if(!Number.isSafeInteger(q)||q<=0)die(label);
  return q;
}
function aggregate(rows,label) {
  if(!Array.isArray(rows))die(label+'_ARRAY_REQUIRED');
  const set=new Map();
  for(const row of rows){
    const s=symbol(row?.symbol,label+'_SYMBOL_INVALID');
    const q=quantity(row?.quantity,label+'_QUANTITY_INVALID');
    if(set.has(s))die(label+'_DUPLICATE_SYMBOL');
    set.set(s,q);
  }
  return set;
}
function boolSafety(safety,label) {
  for(const [k,v] of Object.entries(LOCKED_FLAGS)) if(safety?.[k]!==v)die(label+'_UNSAFE_'+k);
}
function validateBaseline(value) {
  if(!value||value.schemaId!==BASELINE_SCHEMA||value.frozen!==true)die('OWNERSHIP_BASELINE_NOT_FROZEN');
  const {baselineSha256,...core}=value;
  if(typeof baselineSha256!=='string'||baselineSha256!==digest(core))die('OWNERSHIP_BASELINE_HASH_MISMATCH');
  ms(value.capturedAt,'OWNERSHIP_CAPTURED_AT_INVALID');
  const external=aggregate(value.externalPositions,'EXTERNAL');
  const ark=aggregate(value.arkManagedPositions,'ARK_MANAGED');
  for(const [s,q] of ark){
    if(external.has(s))die('OWNERSHIP_OVERLAP');
    if(q%100!==0)die('ARK_MANAGED_LOT_INVALID');
  }
  return {external,ark,baselineSha256};
}
function validateRSS(snapshot,health,nowMs) {
  if(!snapshot||snapshot.schemaId!=='ARK_ACCOUNT_READONLY_SNAPSHOT_V2'||snapshot.source!==BROKER_SOURCE||snapshot.mode!=='READ_ONLY')die('ACCOUNT_SOURCE_INVALID');
  boolSafety(snapshot.safety,'SNAPSHOT');
  const captured=ms(snapshot.capturedAt,'SNAPSHOT_CAPTURE_INVALID');
  const completed=ms(snapshot.captureCompletedAt,'SNAPSHOT_COMPLETED_INVALID');
  if(completed<captured || nowMs-completed>30000 || completed>nowMs+1000)die('ACCOUNT_SNAPSHOT_STALE_OR_INVALID');
  if(!Array.isArray(snapshot.positions)||!Array.isArray(snapshot.orders)||!Array.isArray(snapshot.executions))die('ACCOUNT_ARRAYS_UNAVAILABLE');
  if(!Number.isFinite(snapshot.buyingPower)||snapshot.buyingPower<0)die('BUYING_POWER_UNAVAILABLE');
  if(!health||health.schemaId!=='ARK_MSII_RSS_SOURCE_HEALTH_V1'||health.source!==BROKER_SOURCE||health.readOnly!==true)die('RSS_SOURCE_HEALTH_MISSING');
  if(health.workbookPersisted!==true||health.addinLoaded!==true||health.rssErrors!==0)die('RSS_ADDIN_OR_WORKBOOK_NOT_READY');
  for(const [name,required] of Object.entries(REQUIRED_FEEDS)){
    const item=health.feeds?.[name];
    if(item?.state!==required)die('RSS_FEED_NOT_READY:'+name);
    const observed=ms(item.observedAt,'RSS_FEED_OBSERVED_AT_INVALID:'+name);
    if(observed>completed+1000 || completed-observed>30000)die('RSS_FEED_NOT_FRESH:'+name);
  }
  const healthAt=ms(health.healthCapturedAt,'RSS_HEALTH_CAPTURE_INVALID');
  if(Math.abs(healthAt-completed)>30000 || nowMs-healthAt>30000)die('RSS_HEALTH_STALE');
  return {captured,completed};
}
/** Never identify personal positions as Ark-managed based on symbol alone. */
export function inspectLockedAccount({snapshot,health,ownership,lockedIntent,now=new Date(),maxOrderNotional=null}={}) {
  const blockers=[];
  const withBlock=(fn)=>{try{return fn()}catch(e){blockers.push(e.message);return null}};
  const nowMs=now instanceof Date?now.getTime():ms(now,'NOW_INVALID');
  withBlock(()=>validateRSS(snapshot,health,nowMs));
  const own=withBlock(()=>validateBaseline(ownership));
  const broker=withBlock(()=>aggregate(snapshot?.positions,'BROKER'));
  if(own && broker){
    const expected=new Map([...own.external,...own.ark]);
    for(const s of new Set([...broker.keys(),...expected.keys()])){
      if(!expected.has(s))blockers.push('UNKNOWN_BROKER_POSITION:'+s);
      else if(!broker.has(s))blockers.push('BROKER_POSITION_MISSING:'+s);
      else if(broker.get(s)!==expected.get(s))blockers.push('OWNERSHIP_QUANTITY_MISMATCH:'+s);
    }
  }
  if(Array.isArray(snapshot?.orders)){
    if(snapshot.orders.length>0)blockers.push('OPEN_OR_UNVERIFIED_BROKER_ORDERS');
    for(const row of snapshot.orders){
      if(typeof row?.orderNumber!=='string'||!row.orderNumber.trim())blockers.push('BROKER_ORDER_ID_MISSING');
      if(!row.status || row.status==='UNKNOWN')blockers.push('BROKER_ORDER_STATUS_UNKNOWN');
      if(row.quantity!==undefined && row.filledQty!==undefined && row.filledQty>0 && row.filledQty<row.quantity)blockers.push('BROKER_PARTIAL_FILL');
    }
  }
  if(!lockedIntent || lockedIntent.schemaId!=='ARK_NO11_CASH_LOCKED_INTENT_V1'||lockedIntent.executable!==false||lockedIntent.transmitted!==false)blockers.push('LOCKED_INTENT_REQUIRED');
  if(lockedIntent){
    const {lockedIntentSha256,...core}=lockedIntent;
    if(digest(core)!==lockedIntentSha256)blockers.push('LOCKED_INTENT_HASH_MISMATCH');
    withBlock(()=>boolSafety(lockedIntent.safety,'INTENT'));
    const ownPosition=own?.ark.get(lockedIntent.symbol)||0;
    if(lockedIntent.side==='SELL' && (lockedIntent.positionEffect!=='CLOSE'||ownPosition<lockedIntent.quantity)){
      blockers.push('SELL_NOT_SUPPORTED_BY_ARK_OWNERSHIP');
    }
    if(lockedIntent.side==='BUY'){
      if(lockedIntent.positionEffect!=='OPEN')blockers.push('INVALID_BUY_EFFECT');
      if(own?.ark.has(lockedIntent.symbol))blockers.push('DUPLICATE_ARK_POSITION');
      if(own && own.ark.size>=3)blockers.push('MAX3_POSITION_CAP');
      // Fresh order-price and sufficient cash are not inferred from historical reference fills.
      if(!Number.isFinite(maxOrderNotional)||maxOrderNotional<=0)blockers.push('FRESH_CASH_RESERVATION_REQUIRED');
      else if(snapshot?.buyingPower<maxOrderNotional)blockers.push('INSUFFICIENT_CASH');
    }
  }
  return Object.freeze({
    schemaId:'ARK_NO11_LOCKED_ACCOUNT_INSPECTION_V1',
    status:blockers.length?'BLOCKED':'LOCKED_CANDIDATE_ONLY',
    blockers:[...new Set(blockers)],ownershipBaselineSha256:own?.baselineSha256||null,
    executionAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,transmitted:false
  });
}
