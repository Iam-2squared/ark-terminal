import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {instant,jstDate,FREEZE} from '../lib/phase57-offline-parity.mjs';
import {reconcileState,classifyFreshness} from '../lib/phase57-operational-robustness.mjs';
export {FREEZE};
export const VERSION='PHASE57_EXECUTION_V1';
export const SAFETY=Object.freeze(Object.fromEntries(['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted'].map(k=>[k,false])));
export const finite=x=>typeof x==='number'&&Number.isFinite(x);
export function canonical(x){
  if(Array.isArray(x))return x.map(canonical);
  if(x&&typeof x==='object')return Object.fromEntries(Object.keys(x).sort().map(k=>[k,canonical(x[k])]));
  assert.ok(x===null||typeof x==='string'||typeof x==='boolean'||finite(x),'NON_JSON_VALUE');return x;
}
export const fingerprint=x=>createHash('sha256').update(JSON.stringify(canonical(x))).digest('hex');
export const checkHash=x=>assert.match(x,/^[a-f0-9]{64}$/,'EVIDENCE_HASH_REQUIRED');
export function text(x){assert.ok(typeof x==='string'&&x.trim()&&x.length<=200&&!['__proto__','constructor','prototype'].includes(x),'IDENTITY_REQUIRED');return x;}
export function timestamp(x){instant(x);return new Date(x).toISOString();}
export function quantity(x){assert.ok(Number.isSafeInteger(x)&&x>0&&x%100===0,'INVALID_LOT_QUANTITY');return x;}
export function positive(x){assert.ok(finite(x)&&x>0,'POSITIVE_NUMBER_REQUIRED');return x;}
export const VERSIONS=Object.freeze({strategyVersion:FREEZE,selectorVersion:'FROZEN_MINIMAL_HYBRID_V1',entryVersion:'MSH_ENTRY_V1',exitVersion:'EXIT_V5_DYNAMIC_RECLAIM_BAR_5',allocationVersion:'V3_B_RISK_MAX_3'});
export function orderIntent(decision,{symbols,position=null}){
  assert.ok(['ENTER','EXIT'].includes(decision.action),'INVALID_ACTION');
  assert.ok(['LONG','SHORT'].includes(decision.direction),'INVALID_DIRECTION');
  assert.ok(symbols.includes(decision.symbol),'UNKNOWN_SYMBOL');
  const decisionAt=timestamp(decision.decisionAt),createdAt=timestamp(decision.createdAt);
  assert.ok(instant(decisionAt)<=instant(createdAt),'NONCAUSAL_INTENT');
  assert.equal(decision.sessionDate,jstDate(decisionAt),'SESSION_MISMATCH');
  assert.equal(jstDate(createdAt),decision.sessionDate,'CROSS_SESSION_INTENT');
  for(const [k,v] of Object.entries(VERSIONS))assert.equal(decision[k],v,'FROZEN_VERSION_MISMATCH');
  checkHash(decision.sourceEvidenceHash);checkHash(decision.decisionEvidenceHash);
  const q=quantity(decision.quantity);const close=decision.action==='EXIT';
  if(close)assert.ok(position&&position.symbol===decision.symbol&&position.direction===decision.direction&&q<=position.quantity,'CLOSE_POSITION_UNKNOWN_OR_EXCEEDED');
  assert.ok(['LIMIT','MARKET'].includes(decision.orderType),'UNKNOWN_ORDER_TYPE');
  assert.equal(decision.timeInForce,'DAY','UNKNOWN_TIME_IN_FORCE');
  const limitPrice=decision.orderType==='LIMIT'?positive(decision.limitPrice):null;
  if(decision.orderType==='MARKET')assert.equal(decision.limitPrice,null,'MARKET_LIMIT_PRICE_MUST_BE_NULL');
  const core={decisionId:text(decision.decisionId),sessionDate:decision.sessionDate,decisionAt,symbol:decision.symbol,
    side:(decision.direction==='LONG')!==close?'BUY':'SELL',positionEffect:close?'CLOSE':'OPEN',direction:decision.direction,
    quantity:q,orderType:decision.orderType,limitPrice,timeInForce:'DAY',referencePrice:positive(decision.referencePrice),
    ...VERSIONS,sourceEvidenceHash:decision.sourceEvidenceHash,decisionEvidenceHash:decision.decisionEvidenceHash};
  return {...core,orderIntentId:fingerprint(core),createdAt};
}
export const LIMIT_KEYS=['maxSingleOrderJpy','maxSymbolExposureJpy','maxGrossExposureJpy','maxNetExposureJpy','maxOpenPositions','maxOrdersPerDecision','maxOrdersPerDay','maxDailyLossJpy','maxDailyLossPct','maxPositionQuantity','maxPendingExposureJpy','maxAccountAgeMs','maxFeedAgeMs','maxDecisionAgeMs'];
export function validateLimits(limits){for(const k of LIMIT_KEYS)positive(limits[k]);for(const k of ['maxOpenPositions','maxOrdersPerDecision','maxOrdersPerDay','maxPositionQuantity'])assert.ok(Number.isSafeInteger(limits[k]),'INTEGER_LIMIT_REQUIRED');return structuredClone(limits);}
export const ACTIVE=['READY','SUBMISSION_REQUESTED','SUBMITTED','ACCEPTED','PARTIALLY_FILLED','CANCEL_REQUESTED','UNKNOWN','RECONCILIATION_REQUIRED'];
export function portfolio(state){
  let longs=0,shorts=0,collateral=0,proceeds=0,unrealized=0;
  const positions=Object.values(state.positions);
  for(const p of positions){const v=p.quantity*p.markPrice;const sign=p.direction==='LONG'?1:-1;
    if(sign===1)longs+=v;else {shorts+=v;collateral+=p.collateral;proceeds+=p.proceeds;}
    unrealized+=sign*(p.markPrice-p.averagePrice)*p.quantity;
  }
  return {cashJpy:state.cashJpy,equityJpy:state.cashJpy+longs+collateral+proceeds-shorts,buyingPower:state.cashJpy,
    grossExposureJpy:longs+shorts,absoluteNetExposureJpy:Math.abs(longs-shorts),signedNetExposureJpy:longs-shorts,
    positionsMarketValue:longs-shorts,realizedPnl:state.realizedPnl,unrealizedPnl:unrealized,positions};
}
export function accountReconciliation(state,account){
  if(!account)return {status:'UNKNOWN',mismatches:['ACCOUNT_MISSING']};
  const expected=portfolio(state);const report=reconcileState(expected,account,{moneyJpy:0.000001,quantity:0});
  const extra=[];for(const k of ['buyingPower','positionsMarketValue','realizedPnl','unrealizedPnl'])
    if(!finite(account[k])||Math.abs(expected[k]-account[k])>0.000001)extra.push(k);
  if(!Array.isArray(account.openOrders))extra.push('OPEN_ORDERS_UNKNOWN');
  else {
    const pending=Object.values(state.orders).filter(o=>['SUBMITTED','ACCEPTED','PARTIALLY_FILLED','CANCEL_REQUESTED','UNKNOWN','RECONCILIATION_REQUIRED','SUBMISSION_REQUESTED'].includes(o.status));
    const expectedOrders=pending.map(o=>({orderIntentId:o.intent.orderIntentId,remainingQuantity:o.intent.quantity-o.filledQuantity})).sort((a,b)=>a.orderIntentId.localeCompare(b.orderIntentId));
    if(fingerprint(account.openOrders)!==fingerprint(expectedOrders))extra.push('OPEN_ORDERS_MISMATCH');
  }
  return {status:report.reconciled&&!extra.length?'MATCH':'MISMATCH',mismatches:[...report.mismatches,...extra]};
}
export function preflight(state,now,{fixture=false}={}){
  const c=state.context,blocks=[];
  for(const key of ['msiiConnected','excelConnected','networkConnected','engineReady','finalizationPassed','adapterAvailable'])if(c?.[key]!==true)blocks.push(key.toUpperCase());
  for(const [key,age] of [['feedAt',state.limits.maxFeedAgeMs],['accountAt',state.limits.maxAccountAgeMs]]){
    try{if(!classifyFreshness({sourceTimestamp:c?.[key],observedAt:now,maxAgeMs:age}).decisionAllowed)blocks.push(key.toUpperCase());}catch{blocks.push(key.toUpperCase());}
  }
  const p=portfolio(state);
  if(p.grossExposureJpy>state.limits.maxGrossExposureJpy||p.absoluteNetExposureJpy>state.limits.maxNetExposureJpy||p.positions.length>state.limits.maxOpenPositions)blocks.push('CURRENT_EXPOSURE_LIMIT');
  if(state.reconciliation!=='MATCH')blocks.push('ACCOUNT_POSITION_RECONCILIATION_REQUIRED');
  if(state.emergency)blocks.push('EMERGENCY_STOP');
  if(Object.values(state.orders).some(o=>['UNKNOWN','RECONCILIATION_REQUIRED','SUBMISSION_REQUESTED'].includes(o.status)))blocks.push('UNKNOWN_ORDERS');
  if(!fixture)blocks.push('TRANSMISSION_LOCKED');
  return blocks;
}
export function riskGate(state,intent,now){
  const blocks=preflight(state,now,{fixture:true}),l=state.limits,p=portfolio(state);
  if(!['ARMED','SHADOW','EXIT_ONLY'].includes(state.mode))blocks.push('DISARMED');
  if(state.mode==='EXIT_ONLY'&&intent.positionEffect!=='CLOSE')blocks.push('EXIT_ONLY');
  if(instant(now)-instant(intent.decisionAt)>l.maxDecisionAgeMs||instant(now)<instant(intent.createdAt)||jstDate(now)!==intent.sessionDate)blocks.push('STALE_OR_NONCAUSAL_DECISION');
  const pending=Object.values(state.orders).filter(o=>o.intent.orderIntentId!==intent.orderIntentId&&ACTIVE.includes(o.status));
  const pendingOpen=pending.filter(o=>o.intent.positionEffect==='OPEN');
  const exposure=o=>(o.intent.quantity-o.filledQuantity)*Math.max(o.intent.referencePrice,o.intent.limitPrice??0);
  const pendingExposure=pendingOpen.reduce((a,o)=>a+exposure(o),0);
  const price=Math.max(intent.referencePrice,intent.limitPrice??0),notional=price*intent.quantity;
  const count=Object.values(state.orders).filter(o=>o.intent.sessionDate===intent.sessionDate&&o.submissionCount>0);
  if(count.length>=l.maxOrdersPerDay)blocks.push('DAILY_ORDER_LIMIT');
  if(count.filter(o=>o.intent.decisionId===intent.decisionId).length>=l.maxOrdersPerDecision)blocks.push('DECISION_ORDER_LIMIT');
  if(notional>l.maxSingleOrderJpy)blocks.push('SINGLE_ORDER_LIMIT');
  if(intent.quantity>l.maxPositionQuantity)blocks.push('POSITION_QUANTITY_LIMIT');
  const dailyLoss=Math.max(0,-(p.realizedPnl+p.unrealizedPnl-state.sessionStartPnl));
  if(dailyLoss>=l.maxDailyLossJpy||dailyLoss/state.sessionStartEquity*100>=l.maxDailyLossPct)blocks.push('DAILY_LOSS_LIMIT');
  if(intent.positionEffect==='OPEN'){
    if(p.positions.some(x=>x.symbol===intent.symbol&&x.direction!==intent.direction)||pendingOpen.some(o=>o.intent.symbol===intent.symbol&&o.intent.direction!==intent.direction))blocks.push('OPPOSITE_POSITION');
    if(notional+pendingExposure>Math.min(p.cashJpy,state.context?.account?.buyingPower??0))blocks.push('INSUFFICIENT_BUYING_POWER');
    if(pendingExposure+notional>l.maxPendingExposureJpy)blocks.push('PENDING_EXPOSURE_LIMIT');
    if(p.grossExposureJpy+pendingExposure+notional>l.maxGrossExposureJpy)blocks.push('GROSS_EXPOSURE_LIMIT');
    // No assumed offset from pending opposite-side orders: either side may fill first.
    const buy=pendingOpen.filter(o=>o.intent.direction==='LONG').reduce((a,o)=>a+exposure(o),0)+(intent.direction==='LONG'?notional:0);
    const sell=pendingOpen.filter(o=>o.intent.direction==='SHORT').reduce((a,o)=>a+exposure(o),0)+(intent.direction==='SHORT'?notional:0);
    if(Math.max(Math.abs(p.signedNetExposureJpy+buy),Math.abs(p.signedNetExposureJpy-sell))>l.maxNetExposureJpy)blocks.push('NET_EXPOSURE_LIMIT');
    const symbolPositions=p.positions.filter(x=>x.symbol===intent.symbol);
    const symbolPending=pendingOpen.filter(o=>o.intent.symbol===intent.symbol);
    if(symbolPositions.reduce((a,x)=>a+x.quantity*x.markPrice,0)+symbolPending.reduce((a,o)=>a+exposure(o),0)+notional>l.maxSymbolExposureJpy)blocks.push('SYMBOL_EXPOSURE_LIMIT');
    if(symbolPositions.reduce((a,x)=>a+x.quantity,0)+symbolPending.reduce((a,o)=>a+o.intent.quantity-o.filledQuantity,0)+intent.quantity>l.maxPositionQuantity)blocks.push('POSITION_QUANTITY_LIMIT');
    if(new Set([...p.positions.map(x=>x.symbol),...pendingOpen.map(o=>o.intent.symbol),intent.symbol]).size>l.maxOpenPositions)blocks.push('POSITION_COUNT_LIMIT');
  }else{
    const position=state.positions[intent.symbol];
    const reserved=pending.filter(o=>o.intent.positionEffect==='CLOSE'&&o.intent.symbol===intent.symbol).reduce((a,o)=>a+o.intent.quantity-o.filledQuantity,0);
    if(!position||position.direction!==intent.direction||intent.quantity+reserved>position.quantity)blocks.push('CLOSE_POSITION_UNKNOWN_OR_RESERVED');
  }
  return [...new Set(blocks)];
}
