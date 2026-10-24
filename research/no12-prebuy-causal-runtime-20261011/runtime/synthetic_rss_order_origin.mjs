/**
 * Synthetic only, source-shaped MarketSpeed II:
 * RssOrderIDList: RSS ID -> orderNumber; RssOrderList: orderNumber -> cumulative filledQty.
 * RssExecutionList does not provide its own execution ID or orderNumber.
 * Never infer ownership by matching symbol/time/quantity.
 */
const fail=x=>{throw Error(x)};
const time=(x,label)=>{
 if(typeof x!=='string'||!/(Z|[+-]\d{2}:\d{2})$/.test(x)||!Number.isFinite(Date.parse(x)))fail(label);
 return Date.parse(x);
};
const codeOf=s=>{
 const id=String(s??'').trim().toUpperCase();
 if(!/^[0-9A-Z]{4}(?:\.T)?$/.test(id))fail('RSS_ORDER_SYMBOL_INVALID');
 return id.endsWith('.T')?id:id+'.T';
};
const integer=(v,label)=>Number.isSafeInteger(v)&&v>=0?v:fail(label);
const orderNum=(v,label)=>{
 if(typeof v!=='string'||!/^[0-9A-Za-z_-]{1,64}$/.test(v)||v==='0')fail(label);
 return v;
};
const sourceId=(v,label)=>{
 if(!Number.isSafeInteger(v)||v<=0)fail(label);
 return v;
};
const jstDay=t=>new Intl.DateTimeFormat('en-CA',{
 timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit'
}).format(new Date(t)).replace(/\//g,'-');
export function reconcileNo12SyntheticRssOrigin({
 mode,session,observationAt,arkIssued,rssOrderIds,rssOrders,previous,externalSymbols=[],
 now=new Date()
}={}){
 if(mode!=='SYNTHETIC_OFFLINE_ONLY')fail('NO12_REAL_ORDER_ORIGIN_NOT_CERTIFIED');
 const observed=time(observationAt,'RSS_OBSERVATION_TIME_INVALID');
 const nowMs=now instanceof Date?now.getTime():time(now,'RSS_NOW_INVALID');
 if(observed>nowMs+1000||nowMs-observed>30000)fail('RSS_OBSERVATION_STALE');
 if(jstDay(observed)!==session)fail('RSS_SESSION_MISMATCH');
 if(![arkIssued,rssOrderIds,rssOrders,previous,externalSymbols].every(Array.isArray))
   fail('RSS_BROKER_ARRAY_REQUIRED');
 const external=new Set(externalSymbols.map(codeOf));
 const mapped=new Map(),original=new Map(),book=new Map(),old=new Map();
 for(const r of rssOrderIds){
  const token=sourceId(r.rssOrderId,'RSS_ORDER_TOKEN_INVALID');
  if(mapped.has(token)||r.orderFunction!=='RssStockOrder')fail('RSS_ORDER_TOKEN_DUPLICATE_OR_FUNCTION_INVALID');
  const number=orderNum(r.orderNumber,'RSS_ORDER_TOKEN_ORDER_NUMBER_UNUSABLE');
  if([...mapped.values()].some(x=>x.number===number))fail('RSS_ORDER_NUMBER_COLLISION');
  if(time(r.observedAt,'RSS_ORDER_TOKEN_OBSERVED_INVALID')>observed)fail('RSS_ORDER_TOKEN_FROM_FUTURE');
  mapped.set(token,{number});
 }
 for(const r of rssOrders){
  const number=orderNum(r.orderNumber,'RSS_ORDER_NUMBER_INVALID');
  if(book.has(number))fail('RSS_ORDER_ROW_DUPLICATE');
  const qty=integer(r.quantity,'RSS_ORDER_QUANTITY_INVALID');
  const filled=integer(r.filledQty,'RSS_ORDER_FILLED_INVALID');
  if(qty<1||filled>qty)fail('RSS_ORDER_FILLED_OUT_OF_RANGE');
  if(time(r.observedAt,'RSS_ORDER_OBSERVED_INVALID')>observed)fail('RSS_ORDER_ROW_FROM_FUTURE');
  if(r.trade!=='現物'||!['買付','売付'].includes(r.side))
    fail('RSS_NOT_CASH_LONG_ORDER');
  book.set(number,{qty,filled,side:r.side,symbol:codeOf(r.symbol)});
 }
 for(const r of previous){
  const number=orderNum(r.orderNumber,'RSS_PREVIOUS_ORDER_NUMBER_INVALID');
  if(old.has(number))fail('RSS_PREVIOUS_ORDER_DUPLICATE');
  const filled=integer(r.filledQty,'RSS_PREVIOUS_FILLED_INVALID');
  const seen=time(r.observedAt,'RSS_PREVIOUS_OBSERVED_INVALID');
  if(seen>observed)fail('RSS_CUMULATIVE_TIME_REGRESSION');
  old.set(number,{filled,seen});
 }
 for(const r of arkIssued){
  const token=sourceId(r.rssOrderId,'ARK_RSS_ID_REQUIRED');
  if(original.has(token))fail('ARK_RSS_ID_DUPLICATE');
  if(r.verifiedSyntheticOrigination!==true||
     !/^[a-f0-9]{64}$/.test(r.lockedIntentSha256??'')||
     !['BUY','SELL'].includes(r.side)||
     !Number.isSafeInteger(r.quantity)||r.quantity<100||r.quantity%100!==0)
      fail('ARK_ORDER_ORIGINATION_UNVERIFIED');
  if(time(r.issuedAt,'ARK_ORDER_ISSUED_CLOCK_INVALID')>observed)fail('ARK_ORDER_ISSUED_IN_FUTURE');
  const s=codeOf(r.symbol);
  if(external.has(s))fail('PERSONAL_SYMBOL_CANNOT_BE_ARK_ORDER');
  if(!mapped.has(token))fail('ARK_RSS_ID_NOT_PRESENT_IN_BROKER_RESPONSE');
  original.set(token,{symbol:s,side:r.side,qty:r.quantity});
 }
 let tracked=0,sellDelta=0,buyDelta=0;
 const matchedNumbers=new Set();
 for(const [token,issued] of original){
  const number=mapped.get(token).number;
  if(matchedNumbers.has(number))fail('ARK_MULTIPLE_IDS_ONE_BROKER_ORDER_UNRESOLVED');
  matchedNumbers.add(number);
  const order=book.get(number);
  if(!order)fail('ARK_BROKER_ORDER_NOT_VISIBLE');
  if(order.symbol!==issued.symbol||order.qty!==issued.qty||
      order.side!==(issued.side==='BUY'?'買付':'売付'))fail('ARK_ORDER_IDENTITY_MISMATCH');
  const last=old.get(number);
  if(!last)fail('ARK_ORDER_CUMULATIVE_BASELINE_MISSING');
  if(last.filled>order.filled)fail('ARK_ORDER_FILLED_COUNTER_REGRESSED');
  const delta=order.filled-last.filled;
  if(issued.side==='SELL')sellDelta+=delta;
  else buyDelta+=delta;
  tracked++;
 }
 const others=book.size-tracked;
 return Object.freeze({
  schemaId:'ARK_NO12_SYNTHETIC_RSS_ORDER_ORIGIN_V1',
  status:others>0?'BROKER_OTHER_ORDERS_EXCLUDED':'SYNTHETIC_RSS_ORDER_ORIGIN_RECONCILED',
  arkOriginOrders:tracked,otherOrders:others,
  observedSellFilledQtyDelta:sellDelta,observedBuyFilledQtyDelta:buyDelta,
  conservativeHoldNewBuys:sellDelta>0,
  brokerExactFillTime:null,brokerExecutionIdCertified:false,
  cashReleaseCertified:false,slotReleaseCertified:false,
  realOrderOriginCertified:false,productionReady:false,orderTransmission:false
 });
}
