/** Official MSII cash-side/status interpretation; pure read-only calculation.
 * Source: official RSS item list ohm_002_07 (cash sides are 買付 / 売付).
 * An acknowledgement, cancellation request and terminal cancellation differ.
 * No order function, network, Excel write or portfolio mutation exists here.
 */
const need=(ok,code)=>{if(!ok)throw Error('NO11_ACCOUNT_'+code)};
const integer=(x,min=0)=>Number.isSafeInteger(x)&&x>=min;
export function cashSide(value){
 const sides={'買付':'BUY','売付':'SELL','買':'BUY','売':'SELL'};
 need(typeof value==='string'&&Object.hasOwn(sides,value),'CASH_SIDE_UNRESOLVED');
 return sides[value]; // The short names support existing normalized test/source adapters.
}
export function observedCashOrder(r){
 need(r&&typeof r.orderNumber==='string'&&/^[0-9]{1,32}$/.test(r.orderNumber),'ORDER_ID_INVALID');
 need(typeof r.symbol==='string'&&/^[0-9A-Z]{4}(?:\.T)?$/.test(r.symbol),'SYMBOL_INVALID');
 need(integer(r.quantity,1)&&integer(r.filledQty)&&r.filledQty<=r.quantity&&
  typeof r.account==='string'&&r.account.length>0&&r.trade==='現物','ORDER_FIELDS_INVALID');
 const side=cashSide(r.side),symbol=r.symbol.endsWith('.T')?r.symbol:r.symbol+'.T';
 const status=typeof r.status==='string'?r.status.replaceAll('(','（').replaceAll(')','）'):'';
 need(status.length>0,'ORDER_STATUS_MISSING');
 const cancelled=['取消済（出来無）','取消済（出来有）'].includes(status);
 const expired=['出来ず（出来無）','出来ず（出来有）'].includes(status);
 const cancelPending=['取消中（出来無）','取消中（出来有）'].includes(status);
 if(status==='約定')need(r.filledQty===r.quantity,'FALSE_COMPLETE_FILL');
 if((cancelled||expired||cancelPending)&&status.endsWith('（出来無）'))need(r.filledQty===0,'FALSE_NO_FILL_STATUS');
 if((cancelled||expired||cancelPending)&&status.endsWith('（出来有）'))need(r.filledQty>0&&r.filledQty<r.quantity,'FALSE_PARTIAL_STATUS');
 if(status==='出来有')need(r.filledQty>0&&r.filledQty<r.quantity,'FALSE_PARTIAL_STATUS');
 const known=['執行待ち','執行中','訂正済','出来有','約定'].includes(status)||cancelled||expired||cancelPending;
 const terminal=status==='約定'||cancelled||expired;
 const phase=status==='約定'?'FILLED':cancelled?'CANCELLED':expired?'EXPIRED':cancelPending?'CANCEL_PENDING':
  !known?'UNKNOWN':r.filledQty>0?'PARTIAL':'ACKNOWLEDGED';
 return {symbol,side,account:r.account,quantity:r.quantity,filledQty:r.filledQty,status,terminal,phase};
}
/** Bind a caller-supplied immutable intent origin to RSS's actual ID/order map.
 * This is observation only. It never turns a synthetic origin into a real fill.
 * Real execution prices still require independently attributable receipts.
 */
export function bindObservedOrder({origin,idRows,orders,sessionDate,throughJst,previousFilled=0}){
 need(origin&&origin.schemaId==='ARK_NO11_RECORDED_ORDER_ORIGIN_V1'&&
  origin.evidenceMode==='RECORDED_NOT_AUTHORIZATION'&&origin.productionReady===false&&
  origin.orderTransmission===false,'ORDER_ORIGIN_REQUIRED');
 need(origin.sessionDate===sessionDate&&typeof origin.intentId==='string'&&/^[a-f0-9]{64}$/.test(origin.intentId)&&
  integer(origin.rssOrderId,1)&&origin.rssOrderId<=2147483647&&
  typeof origin.recordedAtJst==='string'&&origin.recordedAtJst.slice(0,10)===sessionDate,
  'ORDER_ORIGIN_IDENTITY');
 const recorded=Date.parse(origin.recordedAtJst),now=Date.parse(throughJst);
 need(Number.isFinite(recorded)&&Number.isFinite(now)&&recorded<=now&&throughJst.slice(0,10)===sessionDate,
  'ORDER_ORIGIN_CLOCK');
 need(Array.isArray(idRows)&&idRows.length<=5000&&Array.isArray(orders)&&orders.length<=5000,'IDENTITY_ROWS_INVALID');
 const ids=idRows.filter(x=>x.rssOrderId===origin.rssOrderId);
 need(ids.length===1,'RSS_ID_NOT_UNIQUE_OR_MISSING');
 const id=ids[0];
 need(id.functionName==='RssStockOrder'&&id.orderDate===sessionDate&&
  typeof id.orderNumber==='string'&&/^[0-9]{1,32}$/.test(id.orderNumber)&&
  typeof id.orderTime==='string'&&/^\d\d:\d\d:\d\d$/.test(id.orderTime),
  'RSS_ID_BINDING_INVALID');
 const orderAt=Date.parse(sessionDate+'T'+id.orderTime+'+09:00');
 // Vendor time is second-granularity. Do not discard a same-second mapping,
 // but never accept an order more than 999ms before its recorded local intent.
 need(Number.isFinite(orderAt)&&recorded-999<=orderAt&&orderAt<=now,'RSS_ID_ORDER_CLOCK');
 need(idRows.filter(x=>x.orderNumber===id.orderNumber&&x.functionName==='RssStockOrder').length===1,
  'BROKER_ORDER_BOUND_TO_MULTIPLE_IDS');
 const matches=orders.filter(r=>r.orderNumber===id.orderNumber);
 need(matches.length===1,'BROKER_ORDER_NOT_UNIQUE_OR_MISSING');
 const order=observedCashOrder(matches[0]);
 need(origin.symbol===order.symbol&&origin.side===order.side&&origin.account===order.account&&
  origin.quantity===order.quantity&&['BUY','SELL'].includes(origin.side),'ORIGIN_ORDER_MISMATCH');
 need(integer(previousFilled)&&previousFilled<=order.filledQty,'CUMULATIVE_FILL_REVERSED');
 return {schemaId:'ARK_NO11_ORDER_ID_OBSERVED_LINK_V1',intentId:origin.intentId,rssOrderId:origin.rssOrderId,
  brokerOrderNumber:id.orderNumber,sessionDate,order,observedFilledDelta:order.filledQty-previousFilled,
  filledQuantityObserved:true,executionPriceAttributed:false,executionTimeCertified:false,
  sellFillObserved:order.side==='SELL'&&order.filledQty>0,
  orderCanBeResent:false,cancelAcknowledged:order.phase==='CANCELLED',
  productionReady:false,orderTransmission:false};
}
