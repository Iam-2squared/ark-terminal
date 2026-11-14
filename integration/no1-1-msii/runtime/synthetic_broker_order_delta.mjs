/**
 * Offline model of exact broker-order-number cumulative fill progression.
 * Distinguishes broker order cumulative filled quantity from a SELL intent
 * or a unique broker execution. Neither a broker execution ID nor a fill time
 * may be inferred from this RSS quantity alone.
 *
 * Synthetic-only until order placement identity and RSS readback are certified.
 */
const fail=x=>{throw Error(x)};
const stamp=(v,label)=>{
 if(typeof v!=='string'||!/(Z|[+-]\d{2}:\d{2})$/.test(v)||!Number.isFinite(Date.parse(v)))fail(label);
 return Date.parse(v);
};
const symbol=v=>{
 const s=String(v??'').trim().toUpperCase();
 if(!/^[0-9A-Z]{4}(?:\.T)?$/.test(s))fail('ORDER_SYMBOL_INVALID');
 return s.endsWith('.T')?s:s+'.T';
};
const integer=(n,label)=>Number.isSafeInteger(n)&&n>=0?n:fail(label);
const id=s=>{
 if(typeof s!=='string'||!s.trim()||s.trim().length>128)fail('BROKER_ORDER_NUMBER_INVALID');
 return s.trim();
};
export function reconcileNo11SyntheticBrokerOrderDelta({
  mode,session,observedAt,arkOrders,brokerRows,previous,now=new Date()
}={}){
 if(mode!=='SYNTHETIC_OFFLINE_ONLY')fail('REAL_ORDER_LINK_IDENTITY_NOT_CERTIFIED');
 const current=stamp(observedAt,'BROKER_ORDER_OBSERVATION_TIME_INVALID');
 const clock=now instanceof Date?now.getTime():stamp(now,'NOW_INVALID');
 if(current>clock+1000||clock-current>30000)fail('BROKER_ORDER_OBSERVATION_STALE');
 if(!/^\d{4}-\d\d-\d\d$/.test(session??''))fail('BROKER_ORDER_SESSION_REQUIRED');
 const day=new Intl.DateTimeFormat('en-CA',{
  timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit'
 }).format(new Date(current)).replace(/\//g,'-');
 if(day!==session)fail('BROKER_ORDER_SESSION_MISMATCH');
 if(!Array.isArray(arkOrders)||!Array.isArray(brokerRows)||!Array.isArray(previous))
  fail('BROKER_ORDER_OBSERVATION_ARRAY_REQUIRED');
 const orders=new Map(),brokers=new Map(),before=new Map();
 for(const row of arkOrders){
  const key=id(row.orderNumber);
  if(orders.has(key))fail('ARK_ORIGIN_ORDER_ID_DUPLICATE');
  const qty=integer(row.quantity,'ARK_ORIGIN_ORDER_QTY_INVALID');
  if(qty<100||qty%100||row.verifiedOrigination!==true||
     !/^[a-f0-9]{64}$/.test(row.lockedIntentSha256??'')||
     !['BUY','SELL'].includes(row.side))fail('ARK_ORDER_ORIGINATION_NOT_VERIFIED');
  const submitted=stamp(row.submittedAt,'ARK_ORDER_SUBMISSION_CLOCK_INVALID');
  if(submitted>current||submitted<current-86400000)fail('ARK_ORDER_SUBMISSION_NOT_CAUSALLY_ADMISSIBLE');
  if(row.side==='SELL'&&row.arkOwnedAtSubmission!==true)fail('PERSONAL_OR_UNVERIFIED_SELL_NOT_ARK_ORDER');
  orders.set(key,{...row,quantity:qty,symbol:symbol(row.symbol)});
 }
 for(const row of brokerRows){
  const key=id(row.orderNumber);
  if(brokers.has(key))fail('BROKER_ORDER_DUPLICATE_ID');
  const qty=integer(row.quantity,'BROKER_ORDER_QTY_UNAVAILABLE');
  const filled=integer(row.filledQty,'BROKER_FILLED_QTY_UNAVAILABLE');
  if(qty<=0||filled>qty)fail('BROKER_ORDER_CUMULATIVE_QUANTITY_INVALID');
  brokers.set(key,{qty,filled,symbol:symbol(row.symbol)});
 }
 for(const row of previous){
  const key=id(row.orderNumber);
  if(before.has(key))fail('PREVIOUS_BROKER_ORDER_OBSERVATION_DUPLICATE');
  const prior=integer(row.filledQty,'PREVIOUS_CUMULATIVE_FILLED_INVALID');
  const seen=stamp(row.observedAt,'PREVIOUS_OBSERVATION_TIME_INVALID');
  if(seen>current||seen<current-86400000)fail('BROKER_ORDER_CLOCK_REGRESSION');
  before.set(key,{filled:prior,observedAt:seen});
 }
 let totalBuyDelta=0,totalSellDelta=0,foreign=0,observed=0;
 for(const [key,broker] of brokers){
   if(!orders.has(key)){foreign++;continue;}
   const order=orders.get(key);
   if(order.symbol!==broker.symbol||order.quantity!==broker.qty)
     fail('BROKER_ORDER_NOT_SAME_ARK_ORIGIN');
   const prior=before.get(key);
   if(!prior)fail('BROKER_ORDER_PREVIOUS_CUMULATIVE_OBSERVATION_REQUIRED');
   if(prior.filled>broker.filled)fail('BROKER_FILLED_QTY_REGRESSION');
   if(prior.filled>order.quantity)fail('PRIOR_FILLED_QTY_EXCEEDS_ORDER');
   const delta=broker.filled-prior.filled;
   if(order.side==='SELL')totalSellDelta+=delta;
   else totalBuyDelta+=delta;
   observed++;
 }
 for(const key of orders.keys())if(!brokers.has(key))fail('ARK_ORDER_MISSING_FROM_BROKER_FEED');
 return Object.freeze({
  schemaId:'ARK_NO11_SYNTHETIC_BROKER_ORDER_FILL_DELTA_V1',
  status:foreign>0?'UNKNOWN_EXTERNAL_ORDERS_PRESENT':'SYNTHETIC_ORDER_CUMULATIVE_RECONCILED',
  arkOrdersObserved:observed,otherOrders:foreign,
  totalBuyFillQuantityIncrease:totalBuyDelta,
  totalSellFillQuantityIncrease:totalSellDelta,
  buyHaltOnObservedSellDelta:totalSellDelta>0,
  // Aggregate order quantities prove neither separate executions nor their exact timestamps.
  brokerExecutionIdentityCertified:false,
  exactFillOccurredAt:null,legalSellFillLatchingCertified:false,
  cashAndSlotReleaseCertified:false,executionAllowed:false,
  transmitted:false,productionReady:false
 });
}
