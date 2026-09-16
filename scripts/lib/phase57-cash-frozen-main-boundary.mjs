import assert from 'node:assert/strict';
import {FROZEN_MAIN_POLICY} from './phase57-frozen-main-engine.mjs';

export const CASH_FROZEN_MAIN_BOUNDARY_VERSION='phase57-cash-frozen-main-boundary-v1';
export const CASH_FROZEN_MAIN_SAFETY=Object.freeze({
  executionAllowed:false,
  brokerWriteAllowed:false,
  excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,
  paperTradingAllowed:false,
  marginTradingAllowed:false,
  shortSellingAllowed:false,
  marginFallbackAllowed:false,
  automaticPromotionAllowed:false,
  productionUpdateAllowed:false,
  transmitted:false,
});

const finite=x=>typeof x==='number'&&Number.isFinite(x);
const symbol=x=>{const s=String(x??'').trim().toUpperCase();assert.match(s,/^[0-9A-Z]{4}\.T$/,'CASH_BOUNDARY_SYMBOL_INVALID');return s;};
const quantity=x=>{const q=Number(x);assert.ok(Number.isInteger(q)&&q>0&&q%100===0,'CASH_BOUNDARY_100_SHARE_LOT_REQUIRED');return q;};

function assertPolicy(){
  assert.equal(FROZEN_MAIN_POLICY.allocation,'V3_B_RISK','CASH_BOUNDARY_ALLOCATION_POLICY_MISMATCH');
  assert.equal(FROZEN_MAIN_POLICY.capacity,'MAX_3','CASH_BOUNDARY_CAPACITY_POLICY_MISMATCH');
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted']){
    assert.equal(FROZEN_MAIN_POLICY[key],false,`CASH_BOUNDARY_UNSAFE_POLICY:${key}`);
  }
}

/**
 * Translate the already-decided Frozen Main ledger trace into cash-only actions.
 * It never re-ranks or changes Selector/Entry/EXIT/Allocation decisions.
 *
 * Any accepted/open SHORT state blocks the entire bridge. Skipping a short while
 * allowing the upstream shadow portfolio to keep it would desynchronize capital,
 * exits, and account state, so the boundary deliberately fails closed.
 */
export function adaptFrozenMainTraceToCashActions(trace){
  assertPolicy();
  assert.ok(trace&&typeof trace==='object','CASH_BOUNDARY_TRACE_REQUIRED');
  assert.ok(Number.isFinite(Date.parse(String(trace.timestamp??''))),'CASH_BOUNDARY_TIMESTAMP_REQUIRED');
  assert.ok(Array.isArray(trace.entries)&&Array.isArray(trace.exits)&&Array.isArray(trace.openPositions),'CASH_BOUNDARY_TRACE_ARRAYS_REQUIRED');
  const blockers=[];
  const shortEntries=trace.entries.filter(x=>String(x?.direction).toUpperCase()==='SHORT');
  const shortExits=trace.exits.filter(x=>String(x?.direction).toUpperCase()==='SHORT');
  const shortOpen=trace.openPositions.filter(x=>String(x?.direction).toUpperCase()==='SHORT');
  if(shortEntries.length)blockers.push('SHORT_ENTRY_ACCEPTED_UPSTREAM');
  if(shortExits.length)blockers.push('SHORT_EXIT_PRESENT_UPSTREAM');
  if(shortOpen.length)blockers.push('SHORT_POSITION_PRESENT_UPSTREAM');
  if(blockers.length){
    return Object.freeze({version:CASH_FROZEN_MAIN_BOUNDARY_VERSION,status:'BLOCKED',blockers:Object.freeze(blockers),actions:Object.freeze([]),cashOnly:true,marginAllowed:false,shortSellingAllowed:false,safety:CASH_FROZEN_MAIN_SAFETY});
  }

  const actions=[];
  for(const row of [...trace.exits].sort((a,b)=>String(a.eventId).localeCompare(String(b.eventId)))){
    assert.equal(String(row.direction).toUpperCase(),'LONG','CASH_BOUNDARY_LONG_EXIT_REQUIRED');
    const q=quantity(row.quantity),s=symbol(row.symbol);
    const notional=Number(row.referenceNotionalJpy);
    assert.ok(finite(notional)&&notional>0,'CASH_BOUNDARY_EXIT_NOTIONAL_REQUIRED');
    actions.push(Object.freeze({
      actionId:`${trace.timestamp}|EXIT|${row.eventId}`,
      sourceEventId:String(row.eventId),
      sourceKind:'FROZEN_MAIN_EXIT',
      symbol:s,direction:'LONG',side:'SELL',positionEffect:'CLOSE',quantity:q,
      orderType:'MARKET',limitPrice:null,timeInForce:'DAY',estimatedNotional:notional,
      allocation:'V3_B_RISK',capacity:'MAX_3',selector:FROZEN_MAIN_POLICY.selector,entry:FROZEN_MAIN_POLICY.entry,exit:FROZEN_MAIN_POLICY.exit,
      executable:false,transmitted:false,
    }));
  }
  for(const row of [...trace.entries].sort((a,b)=>String(a.eventId).localeCompare(String(b.eventId)))){
    assert.equal(String(row.direction).toUpperCase(),'LONG','CASH_BOUNDARY_LONG_ENTRY_REQUIRED');
    const q=quantity(row.quantity),s=symbol(row.symbol);
    const requiredCash=Number(row.requiredCashJpy),notional=Number(row.entryNotionalJpy);
    assert.ok(finite(notional)&&notional>0,'CASH_BOUNDARY_ENTRY_NOTIONAL_REQUIRED');
    assert.ok(finite(requiredCash)&&requiredCash>=notional,'CASH_BOUNDARY_REQUIRED_CASH_INVALID');
    actions.push(Object.freeze({
      actionId:`${trace.timestamp}|ENTRY|${row.eventId}`,
      sourceEventId:String(row.eventId),
      sourceKind:'FROZEN_MAIN_ENTRY',
      symbol:s,direction:'LONG',side:'BUY',positionEffect:'OPEN',quantity:q,
      orderType:'MARKET',limitPrice:null,timeInForce:'DAY',estimatedNotional:notional,requiredCashJpy:requiredCash,
      allocation:'V3_B_RISK',capacity:'MAX_3',selector:FROZEN_MAIN_POLICY.selector,entry:FROZEN_MAIN_POLICY.entry,exit:FROZEN_MAIN_POLICY.exit,
      executable:false,transmitted:false,
    }));
  }
  return Object.freeze({
    version:CASH_FROZEN_MAIN_BOUNDARY_VERSION,
    status:actions.length?'READY':'NO_ACTION',
    blockers:Object.freeze([]),
    actions:Object.freeze(actions),
    eventOrder:Object.freeze(actions.map(x=>x.sourceKind)),
    requiresSequentialAccountReconciliation:actions.length>1,
    cashOnly:true,marginAllowed:false,shortSellingAllowed:false,
    safety:CASH_FROZEN_MAIN_SAFETY,
  });
}
