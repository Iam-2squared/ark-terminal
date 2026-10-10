/**
 * Freezes only positions explicitly classified by their human owner.
 * Does not infer Ark ownership from a broker position or silently default
 * current holdings to External. The local JSON is PRIVATE, never committed.
 */
import {digest} from './locked_intent.mjs';
import {inspectReadOnlySnapshot} from './account_gate.mjs';

const fail=reason=>{throw Error(reason);};
function symbol(value) {
  if(typeof value!=='string')fail('OWNERSHIP_SYMBOL_REQUIRED');
  const x=value.trim().toUpperCase();
  if(!/^[0-9A-Z]{4}(?:\.T)?$/.test(x))fail('OWNERSHIP_SYMBOL_INVALID');
  return x.endsWith('.T')?x:x+'.T';
}
function normalize(rows,label) {
  if(!Array.isArray(rows))fail(label+'_ARRAY_REQUIRED');
  const items=[], seen=new Set();
  for(const row of rows){
    const s=symbol(row?.symbol),q=row?.quantity;
    if(!Number.isSafeInteger(q)||q<=0)fail(label+'_QUANTITY_INVALID');
    if(seen.has(s))fail(label+'_SYMBOL_DUPLICATE');
    seen.add(s);items.push({symbol:s,quantity:q});
  }
  return items.sort((a,b)=>a.symbol.localeCompare(b.symbol));
}
export function freezeConfirmedOwnership({
  snapshot,health,confirmedExternal,confirmedArkManaged,
  explicitUserConfirmation,now=new Date()
}={}) {
  if(explicitUserConfirmation!=='I_CONFIRM_EACH_POSITION_OWNER')fail('EXPLICIT_POSITION_OWNERSHIP_CONFIRMATION_REQUIRED');
  const probe=inspectReadOnlySnapshot({snapshot,health,now});
  if(probe.status!=='RSS_STATUS_OBSERVED_READ_ONLY')fail('FRESH_READ_ONLY_SOURCE_REQUIRED');
  if(snapshot.orders.length>0)fail('OPEN_ORDERS_BLOCK_BASELINE_FREEZE');
  const broker=normalize(snapshot.positions,'BROKER');
  const external=normalize(confirmedExternal,'EXTERNAL');
  const managed=normalize(confirmedArkManaged,'ARK_MANAGED');
  if(managed.some(x=>x.quantity%100!==0))fail('ARK_MANAGED_100_SHARE_LOT_REQUIRED');
  const owners=new Map();
  for(const row of [...external,...managed]){
    if(owners.has(row.symbol))fail('POSITION_OWNER_OVERLAP');
    owners.set(row.symbol,row.quantity);
  }
  if(owners.size!==broker.length||broker.some(x=>owners.get(x.symbol)!==x.quantity)) {
    fail('BROKER_OWNERSHIP_CLASSIFICATION_MISMATCH');
  }
  const core={
    schemaId:'ARK_CASH_OWNERSHIP_BASELINE_V1',
    capturedAt:snapshot.captureCompletedAt,
    source:'MARKETSPEED_II_RSS_EXPLICIT_OWNER_CONFIRMED',
    frozen:true,externalPositions:external,arkManagedPositions:managed
  };
  return {...core,baselineSha256:digest(core)};
}
