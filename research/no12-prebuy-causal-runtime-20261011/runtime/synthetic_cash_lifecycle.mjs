/**
 * Ark No.1.2 synthetic-only cash-equity event loop, separated from Frozen No.1.1.
 * No broker method, no Excel I/O, no private account read, no production switch.
 *
 * Admission -> intent -> actual (synthetic) fill. SELL_INTENT does not free cash
 * or slots. The first positive SELL_FILL in a day prohibits subsequent BUY.
 * Same knownAt timestamp: SELL_FILL is always processed before ENTRY_SIGNAL.
 */
import {rankNo12PreBuyResearch} from './prebuy_candidates.mjs';
const fail=x=>{throw Error(x)};
const parse=(x,label)=>{
 if(typeof x!=='string'||!/(Z|[+-]\d{2}:\d{2})$/.test(x)||!Number.isFinite(Date.parse(x)))fail(label);
 return Date.parse(x);
};
const sym=x=>{
 const s=String(x??'').trim().toUpperCase();
 if(!/^[0-9A-Z]{4}(?:\.T)?$/.test(s))fail('NO12_SYMBOL_INVALID');
 return s.endsWith('.T')?s:s+'.T';
};
const count=(x,label)=>Number.isSafeInteger(x)&&x>0?x:fail(label);
const px=(x,label)=>Number.isSafeInteger(x)&&x>0?BigInt(x):fail(label);
// Prices are tenth-yen, cash is yen cents, precisely represented with BigInt.
const roundUp=(a,b)=>(a+b-1n)/b;
const debit=(p,q)=>roundUp(p*BigInt(q)*10n*10005n,10000n);
const credit=(p,q)=>p*BigInt(q)*10n*9995n/10000n;
const yen2=sen=>{const n=sen<0n?-sen:sen;return (sen<0n?'-':'')+
 (n/100n).toString()+'.'+(n%100n).toString().padStart(2,'0')};
const importance=Object.freeze({SELL_FILL:0,BUY_FILL:1,SELL_INTENT:2,ENTRY_SIGNAL:3});
const jstClock=t=>new Intl.DateTimeFormat('en-GB',{
  timeZone:'Asia/Tokyo',hour:'2-digit',minute:'2-digit',hourCycle:'h23'
}).format(new Date(t));
export function runNo12SyntheticSession({
 mode,candidateInput,startingCashYen,events,externalSymbols=[],
 now=new Date()
}={}){
 if(mode!=='SYNTHETIC_OFFLINE_ONLY')fail('NO12_REAL_BROKER_MODE_DISABLED');
 if(!Number.isSafeInteger(startingCashYen)||startingCashYen<0)fail('NO12_START_CASH_INVALID');
 if(!Array.isArray(events)||events.length>10000)fail('NO12_EVENTS_ARRAY_REQUIRED');
 if(!Array.isArray(externalSymbols))fail('NO12_EXTERNAL_ARRAY_REQUIRED');
 const ranked=rankNo12PreBuyResearch({...candidateInput,mode:'SYNTHETIC_OFFLINE_ONLY',now});
 const source=ranked.eligible;
 const eligible=new Map(source.map(r=>[r.entryId,r]));
 const external=new Set(externalSymbols.map(sym));
 const positions=new Map(),pendingBuy=new Map(),pendingSell=new Map();
 let cash=BigInt(startingCashYen)*100n;
 let reservation=0n, firstSellObserved=null;
 let halted=false;
 const rejected=[],history=[],seenEvents=new Map(),consumedEntries=new Set();
 const syntheticOrderId=new Set();
 const decisionAt=parse(candidateInput.observationFrame.decisionAt,'NO12_DECISION_AT_MISSING');
 const session=candidateInput.batch.session;
 const clock=now instanceof Date?now.getTime():parse(now,'NO12_NOW_INVALID');
 if(decisionAt>clock+1000)fail('NO12_SOURCE_DECISION_IN_FUTURE');
 const items=events.map(e=>{
  if(!e||typeof e!=='object'||Array.isArray(e)||
     typeof e.eventId!=='string'||!/^[a-zA-Z0-9_.:-]{1,128}$/.test(e.eventId)||
     !Object.hasOwn(importance,e.kind))fail('NO12_SYNTHETIC_EVENT_INVALID');
  if(e.session!==session)fail('NO12_EVENT_SESSION_MISMATCH');
  const at=parse(e.knownAt,'NO12_EVENT_KNOWN_CLOCK_INVALID');
  if(at<decisionAt||at>clock+1000)fail('NO12_EVENT_OUTSIDE_SOURCE_CLOCK');
  return {...e,time:at};
 });
 items.sort((a,b)=>a.time-b.time||importance[a.kind]-importance[b.kind]||a.eventId.localeCompare(b.eventId));
 const block=(e,reason)=>{
  rejected.push(Object.freeze({eventId:e.eventId,reason}));
 };
 for(const e of items){
  const canonical=JSON.stringify(e);
  if(seenEvents.has(e.eventId)){
    if(seenEvents.get(e.eventId)!==canonical)fail('NO12_DUPLICATE_EVENT_ID_CONFLICT');
    continue; // same replayed synthetic event is idempotent
  }
  seenEvents.set(e.eventId,canonical);
  if(e.kind==='ENTRY_SIGNAL'){
    if(jstClock(e.time)>='15:20'){block(e,'AFTER_1520_CUTOFF');continue;}
    if(!eligible.has(e.entryId)){block(e,'NOT_ELIGIBLE_PREBUY_RESEARCH_ENTRY');continue;}
    const r=eligible.get(e.entryId);
    if(consumedEntries.has(e.entryId)){block(e,'ORIGINAL_ENTRY_ALREADY_CONSUMED');continue;}
    consumedEntries.add(e.entryId); // never reoffer rejected entry after funds change
    if(firstSellObserved){block(e,'AFTER_FIRST_SYNTHETIC_SELL_FILL_NO_BUY');continue;}
    if(external.has(r.symbol)){block(e,'PERSONAL_HOLDING_SYMBOL_PROTECTED');continue;}
    if(positions.has(r.symbol)||[...pendingBuy.values()].some(o=>o.symbol===r.symbol)){
      block(e,'DUPLICATE_SYMBOL_OR_PENDING_BUY');continue;
    }
    if(positions.size+pendingBuy.size>=3){block(e,'MAX3_SLOTS');continue;}
    const limit=px(Math.round(r.syntheticReferencePrice*10),'SYNTHETIC_REFERENCE_PRICE_INVALID');
    const needed=debit(limit,r.quantity);
    if(needed>cash-reservation){block(e,'CASH_OR_100_LOT_INSUFFICIENT');continue;}
    if(typeof e.orderId!=='string'||!e.orderId.trim()||syntheticOrderId.has(e.orderId))
      fail('NO12_SYNTHETIC_ORDER_ID_INVALID');
    syntheticOrderId.add(e.orderId);
    pendingBuy.set(e.orderId,{symbol:r.symbol,entryId:e.entryId,
      quantity:r.quantity,reserve:needed,signalAt:e.time});
    reservation+=needed;
    history.push(Object.freeze({type:'SYNTHETIC_BUY_INTENT',entryId:e.entryId,symbol:r.symbol,
      orderId:e.orderId,transmitted:false}));
  } else if(e.kind==='BUY_FILL'){
    if(!pendingBuy.has(e.orderId)){block(e,'BUY_FILL_WITHOUT_OWN_INTENT');continue;}
    const o=pendingBuy.get(e.orderId);
    if(e.time<=o.signalAt)fail('NO12_BUY_FILL_NOT_LATER_THAN_INTENT');
    const q=count(e.quantity,'NO12_BUY_FILL_QTY_INVALID');
    if(q!==o.quantity){block(e,'PARTIAL_BUY_FILL_UNRECONCILED');halted=true;break;}
    const actual=debit(px(e.fillPriceTenth,'NO12_BUY_FILL_PRICE_INVALID'),q);
    if(actual>o.reserve||actual>cash){block(e,'BUY_FILL_PRICE_OR_CASH_EXCEEDS_RESERVATION');halted=true;break;}
    cash-=actual;reservation-=o.reserve;pendingBuy.delete(e.orderId);
    if(positions.has(o.symbol))fail('NO12_DUPLICATE_ARK_POSITION_AFTER_FILL');
    positions.set(o.symbol,{symbol:o.symbol,quantity:q,costSen:actual,entryId:o.entryId});
    history.push(Object.freeze({type:'SYNTHETIC_BUY_FILL',symbol:o.symbol,quantity:q,
      observedAt:e.knownAt,brokerExecutionIdentityCertified:false}));
  } else if(e.kind==='SELL_INTENT'){
    const s=sym(e.symbol),o=positions.get(s);
    if(!o){block(e,'SELL_NOT_ARK_OWNED');continue;}
    if(pendingSell.has(e.orderId)||syntheticOrderId.has(e.orderId)||
       [...pendingSell.values()].some(row=>row.symbol===s)) {
      block(e,'DUPLICATE_SELL_INTENT');continue;
    }
    if(typeof e.orderId!=='string'||!e.orderId.trim())fail('NO12_SELL_ORDER_ID_REQUIRED');
    if(count(e.quantity,'NO12_SELL_QTY_INVALID')!==o.quantity){block(e,'SELL_NOT_FULL_ARK_QUANTITY');continue;}
    syntheticOrderId.add(e.orderId);
    pendingSell.set(e.orderId,{symbol:s,remaining:o.quantity,signalAt:e.time});
    history.push(Object.freeze({type:'SYNTHETIC_SELL_INTENT',symbol:s,
      orderId:e.orderId,transmitted:false}));
  } else if(e.kind==='SELL_FILL'){
    if(!pendingSell.has(e.orderId)){block(e,'SELL_FILL_WITHOUT_OWN_ARK_INTENT');continue;}
    const o=pendingSell.get(e.orderId),p=positions.get(o.symbol);
    if(!p||e.time<=o.signalAt)fail('NO12_SELL_FILL_NOT_LATER_THAN_INTENT');
    const q=count(e.quantity,'NO12_SELL_FILL_QTY_INVALID');
    if(q>o.remaining||q>p.quantity)fail('NO12_SELL_OVERFILL');
    if(e.syntheticMatchedOrder!==true){block(e,'SELL_FILL_LINKAGE_NOT_VERIFIED');halted=true;break;}
    cash+=credit(px(e.fillPriceTenth,'NO12_SELL_FILL_PRICE_INVALID'),q);
    o.remaining-=q;p.quantity-=q;
    if(p.quantity===0)positions.delete(o.symbol);
    if(o.remaining===0)pendingSell.delete(e.orderId);
    if(!firstSellObserved)firstSellObserved=e.knownAt;
    history.push(Object.freeze({type:'SYNTHETIC_SELL_FILL',symbol:o.symbol,quantity:q,
      observedAt:e.knownAt,brokerExecutionIdentityCertified:false}));
  }
 }
 return Object.freeze({
  schemaId:'ARK_NO12_SYNTHETIC_CASH_EQUITY_LEDGER_V1',
  status:halted?'BLOCKED_RECONCILIATION':'SYNTHETIC_SCENARIO_EVALUATED',
  session,
  startingCashYen:startingCashYen.toString()+'.00',endingCashYen:yen2(cash),
  positions:Object.freeze([...positions.values()].map(p=>Object.freeze({symbol:p.symbol,
    quantity:p.quantity,entryId:p.entryId}))),
  pendingBuyCount:pendingBuy.size,pendingSellCount:pendingSell.size,
  cashReservationYen:yen2(reservation),
  firstSyntheticSellFillObservedAt:firstSellObserved,
  subsequentBuyProhibited:firstSellObserved!==null,
  rejected:Object.freeze(rejected),history:Object.freeze(history),
  originalFrozenR0Reproduced:false,brokerExecutionIdentityCertified:false,
  brokerMoneyReconciled:false,realSourceArrivalsCertified:false,
  productionReady:false,orderTransmission:false
 });
}
