/**
 * Read-only funding projection for Ark Integrated No.1.1 / Frozen Capital v5.
 * The human-selected policy allocates up to 100% of broker RSS cash buying power.
 * Personal holdings are not subtracted a second time and never enter Ark equity.
 * This is an account INPUT PREVIEW, not a live-ready Capital allocator/order.
 */
import {digest} from './locked_intent.mjs';
import {inspectReadOnlySnapshot} from './account_gate.mjs';

export const CAPITAL_CASH_POLICY='FULL_RSS_CASH_BUYING_POWER_NO_PERSONAL_STOCK_DOUBLE_DEDUCTION_V1';
const fail=message=>{throw Error(message)};
const money=(value,label,{positive=false}={})=>{
  if(typeof value!=='number'||!Number.isFinite(value)||value<0||
     !Number.isSafeInteger(Math.trunc(value))||(positive&&value<=0))fail(label);
  return value;
};
function symbol(raw,label) {
  if(typeof raw!=='string')fail(label);
  const value=raw.trim().toUpperCase();
  if(!/^[0-9A-Z]{4}(?:\.T)?$/.test(value))fail(label);
  return value.endsWith('.T')?value:value+'.T';
}
function rowsToMap(rows,label,{ark=false}={}) {
  if(!Array.isArray(rows))fail(label+'_ARRAY_REQUIRED');
  const map=new Map();
  for(const row of rows){
    const key=symbol(row?.symbol,label+'_SYMBOL_INVALID');
    const quantity=row?.quantity;
    if(!Number.isSafeInteger(quantity)||quantity<=0||(ark&&quantity%100!==0)) {
      fail(label+'_QUANTITY_INVALID');
    }
    if(map.has(key))fail(label+'_DUPLICATE_SYMBOL');
    map.set(key,quantity);
  }
  return map;
}
function assertOwnership(ownership) {
  if(ownership?.schemaId!=='ARK_CASH_OWNERSHIP_BASELINE_V1'||
     ownership.frozen!==true||
     ownership.source!=='MARKETSPEED_II_RSS_EXPLICIT_OWNER_CONFIRMED') {
    fail('EXPLICIT_FROZEN_OWNERSHIP_REQUIRED');
  }
  const {baselineSha256,...core}=ownership;
  if(typeof baselineSha256!=='string'||baselineSha256!==digest(core)) {
    fail('OWNERSHIP_BASELINE_HASH_MISMATCH');
  }
  const external=rowsToMap(ownership.externalPositions,'EXTERNAL');
  const managed=rowsToMap(ownership.arkManagedPositions,'ARK_MANAGED',{ark:true});
  if(managed.size>3)fail('ARK_MAX3_ALREADY_EXCEEDED');
  for(const key of external.keys()) {
    if(managed.has(key))fail('PERSONAL_AND_ARK_SYMBOL_OVERLAP');
  }
  return {external,managed};
}
function validateBroker(snapshot,ownership) {
  const broker=rowsToMap(snapshot.positions,'BROKER');
  const expected=new Map([...ownership.external,...ownership.managed]);
  if(broker.size!==expected.size)fail('BROKER_POSITION_OWNERSHIP_MISMATCH');
  for(const [key,quantity] of broker) {
    if(!expected.has(key)||expected.get(key)!==quantity) {
      fail('BROKER_POSITION_OWNERSHIP_MISMATCH');
    }
  }
  let arkExposure=0;
  for(const row of snapshot.positions) {
    const key=symbol(row.symbol,'BROKER_SYMBOL_INVALID');
    if(!ownership.managed.has(key))continue;
    arkExposure+=money(row.marketValue,'ARK_MARKET_VALUE_UNAVAILABLE',{positive:true});
    money(arkExposure,'ARK_EXPOSURE_OVERFLOW');
  }
  return arkExposure;
}
const locked=(blockers,inputs=null,arkPositions=0)=>Object.freeze({
  schemaId:'ARK_NO11_CAPITAL_FUNDING_PREVIEW_V1',
  status:blockers.length?'BLOCKED':'READ_ONLY_CAPITAL_PREVIEW',
  blockers:Object.freeze([...new Set(blockers)]),
  policyId:CAPITAL_CASH_POLICY,
  arkCapitalInputs:inputs,
  arkManagedPositionCount:arkPositions,
  externalHoldingsIncludedInEquity:false,
  extraDeductionForPersonalStock:false,
  allocationInputsForTradingCertified:false,
  actualFeedTimestampCertified:false,
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,liveTradingAllowed:false,
  transmitted:false,productionReady:false
});
/**
 * Returns (cash, equity, exposure) for Frozen Capital v5, shadow-only:
 * cash = 100% of RSS 現物買付可能額, equity = cash + Ark-managed market value,
 * exposure = Ark-managed market value. Do not treat this as certified cash.
 * Existing S/A/B bands and frozen signals are supplied independently.
 */
export function inspectNo11CapitalFunding({snapshot,health,ownership,now=new Date()}={}) {
  const blockers=[];
  let inputs=null,managedCount=0;
  try {
    const inspection=inspectReadOnlySnapshot({snapshot,health,now});
    if(inspection.status!=='RSS_STATUS_OBSERVED_READ_ONLY') {
      fail('RSS_READ_ONLY_GATE_BLOCKED:'+inspection.blockers.join(','));
    }
    if(snapshot.orders.length!==0)fail('BROKER_ORDERS_UNVERIFIED_BLOCK_NEW_BUY');
    const owner=assertOwnership(ownership);
    managedCount=owner.managed.size;
    const exposure=validateBroker(snapshot,owner);
    const cash=money(snapshot.buyingPower,'RSS_BUYING_POWER_INVALID');
    const equity=money(cash+exposure,'ARK_ONLY_EQUITY_INVALID');
    inputs=Object.freeze({cash,equity,exposure});
  } catch(error) {
    blockers.push(error instanceof Error?error.message:'CAPITAL_FUNDING_UNKNOWN_FAILURE');
  }
  return locked(blockers,blockers.length?null:inputs,managedCount);
}
