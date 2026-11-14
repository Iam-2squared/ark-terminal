/**
 * Broker order / execution SOURCE COVERAGE inspection, READ ONLY.
 *
 * Official MarketSpeed II RSS function-return schema (2026-03-30):
 * RssOrderList has orderNumber and optional status/side/receivedAt;
 * RssExecutionList includes execution timestamp, symbol, account, side,
 * quantity and price BUT NO ORDER ID AND NO UNIQUE EXECUTION ID.
 *
 * A position or sell execution can belong to a personal EXTERNAL holding.
 * Never infer a SELL fill linkage from a matching symbol, date or quantity.
 */
import {inspectReadOnlySnapshot} from './account_gate.mjs';
import {digest} from './locked_intent.mjs';
const fail=x=>{throw Error(x)};
const symbol=x=>{
  if(typeof x!=='string')fail('BROKER_SYMBOL_UNAVAILABLE');
  const s=x.trim().toUpperCase();
  if(!/^[0-9A-Z]{4}(?:\.T)?$/.test(s))fail('BROKER_SYMBOL_INVALID');
  return s.endsWith('.T')?s:s+'.T';
};
const qty=(n,label)=>Number.isSafeInteger(n)&&n>0?n:fail(label);
const price=(n,label)=>typeof n==='number'&&Number.isFinite(n)&&n>0?n:fail(label);
const parseJst=s=>{
  if(typeof s!=='string'||!/^\d{4}\/\d\d\/\d\d \d\d:\d\d:\d\d$/.test(s))fail('BROKER_EXECUTION_TIME_UNVERIFIED');
  const ms=Date.parse(s.replaceAll('/','-').replace(' ','T')+'+09:00');
  if(!Number.isFinite(ms)||new Date(ms).toLocaleString('sv-SE',{timeZone:'Asia/Tokyo'}).slice(0,19).replace(' ','T')!==s.replaceAll('/','-').replace(' ','T'))fail('BROKER_EXECUTION_TIME_UNVERIFIED');
  return ms;
};
function validateOwners(value){
  if(!value||value.schemaId!=='ARK_CASH_OWNERSHIP_BASELINE_V1'||value.frozen!==true)
    fail('FROZEN_OWNERSHIP_REQUIRED');
  const {baselineSha256,...core}=value;
  if(baselineSha256!==digest(core))fail('OWNERSHIP_CHECKSUM_MISMATCH');
  if(!Array.isArray(value.externalPositions)||!Array.isArray(value.arkManagedPositions))fail('OWNERSHIP_LIST_INVALID');
  const external=new Set(),ark=new Set();
  for(const x of value.externalPositions){
    const id=symbol(x?.symbol);
    qty(x?.quantity,'PERSONAL_QTY_INVALID');
    if(external.has(id))fail('PERSONAL_SYMBOL_DUPLICATE');
    external.add(id);
  }
  for(const x of value.arkManagedPositions){
    const id=symbol(x?.symbol);
    const n=qty(x?.quantity,'ARK_QTY_INVALID');
    if(n%100||ark.has(id)||external.has(id))fail('ARK_OWNERSHIP_INVALID');
    ark.add(id);
  }
  if(ark.size>3)fail('ARK_MAX3_EXCEEDED');
  return {external,ark};
}
export function inspectNo11BrokerRssIdentityCoverage({
 snapshot,health,ownership,now=new Date()
}={}){
 const admitted=inspectReadOnlySnapshot({snapshot,health,now});
 if(admitted.status!=='RSS_STATUS_OBSERVED_READ_ONLY')fail('BROKER_SOURCE_READONLY_GATE_BLOCKED');
 const own=validateOwners(ownership);
 if(!Array.isArray(snapshot.orders)||!Array.isArray(snapshot.executions))fail('BROKER_ORDER_EXECUTION_LIST_MISSING');
 let personalSellRows=0,unlinkedSellRows=0;
 const ids=new Set();
 for(const row of snapshot.orders){
   const id=String(row?.orderNumber??'').trim();
   if(!id||ids.has(id))fail('BROKER_ORDER_ID_MISSING_OR_DUPLICATE');
   ids.add(id);
   symbol(row.symbol);
   const n=qty(row.quantity,'BROKER_ORDER_QTY_INVALID');
   if(row.filledQty!==null&&row.filledQty!==undefined){
      if(!Number.isSafeInteger(row.filledQty)||row.filledQty<0||row.filledQty>n)
        fail('BROKER_ORDER_FILLED_QTY_INVALID');
   }
 }
 for(const row of snapshot.executions){
   parseJst(row.executionDate);
   const id=symbol(row.symbol);
   const side=String(row.side??'').trim();
   if(!['買付','売付'].includes(side))fail('BROKER_EXECUTION_SIDE_OR_TYPE_UNVERIFIED');
   qty(row.quantity,'BROKER_EXECUTION_QTY_INVALID');
   price(row.price,'BROKER_EXECUTION_PRICE_INVALID');
   if(typeof row.account!=='string'||!row.account.trim())fail('BROKER_EXECUTION_ACCOUNT_UNAVAILABLE');
   if(side==='売付'){
      unlinkedSellRows++;
      if(own.external.has(id))personalSellRows++;
   }
 }
 const rowCounts=Object.freeze({orders:snapshot.orders.length,executions:snapshot.executions.length});
 const reasons=[];
 if(rowCounts.orders)reasons.push('BROKER_ORDER_SIDE_AND_RECEIPT_NOT_CAPTURED');
 if(rowCounts.executions)reasons.push('RSS_EXECUTION_ROWS_HAVE_NO_ORDER_OR_EXECUTION_ID');
 if(personalSellRows)reasons.push('PERSONAL_SELL_ROW_MUST_NEVER_TRIGGER_ARK_LATCH');
 return Object.freeze({
  schemaId:'ARK_NO11_RSS_BROKER_IDENTITY_COVERAGE_V1',
  status:reasons.length?'BROKER_IDENTITY_UNCERTIFIED':'ZERO_BROKER_ORDER_EXECUTION_ROWS',
  blockers:Object.freeze(reasons),rowCounts,unlinkedSellRows,personalSellRows,
  arkSellFillIdentityCertified:false,firstSellFillLatchedFromRss:false,
  liveOrderReconciliationCertified:false,sourceActualBrokerArrivalCertified:false,
  orderTransmission:false,productionReady:false
 });
}
