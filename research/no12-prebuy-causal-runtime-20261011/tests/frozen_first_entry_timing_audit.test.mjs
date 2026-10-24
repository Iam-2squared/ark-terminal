import test from 'node:test';
import assert from 'node:assert/strict';
import {auditNo11OriginalScheduledEntryClock as audit,
 originalResearchNextEligibleFillMinute as next,
 originalResearchActiveElapsed as elapsed,
 summarizeNo11OriginalClockParity as summarize} from '../runtime/frozen_first_entry_timing_audit.mjs';
const mode='SYNTHETIC_OFFLINE_ONLY';
const base={mode,session:'2026-10-13',selectorMinute:565,intentMinute:570};
test('original study next_fill prefers eligible same-minute bar: time planned but future open UNKNOWN',()=>{
 const x=audit(base);
 assert.equal(x.plannedNextEligibleResearchBarMinute,570);
 assert.equal(x.selectorToIntentActiveMinutes,5);
 assert.equal(x.plannedIntentToFillActiveMinutes,0);
 assert.equal(x.modelFieldAvailabilityBeforePurchase['selector/raw_entry_vs_first_price_pct'],'FUTURE_NEXT_OPEN_PRICE_UNKNOWN');
 assert.equal(x.originalH2H3H5RankReproduced,false);
 assert.equal(x.productionReady,false);
});
test('original regular first-open exclusions: 09:00 skips 09:00, 12:30 skips 12:30',()=>{
 assert.equal(next({session:'2026-10-13',intentMinute:540}),541);
 assert.equal(next({session:'2026-10-13',intentMinute:750}),751);
 assert.equal(next({session:'2026-10-13',intentMinute:690}),751);
 assert.equal(next({session:'2026-10-13',intentMinute:924}),924);
 assert.equal(next({session:'2026-10-13',intentMinute:925}),null);
});
test('expected ACTIVE gap across lunch is one actual regular minute, not 61 wall-clock minutes',()=>{
 const x=audit({...base,selectorMinute:685,intentMinute:690});
 assert.equal(x.plannedNextEligibleResearchBarMinute,751);
 assert.equal(x.plannedIntentToFillActiveMinutes,1);
 assert.equal(x.selectorToIntentActiveMinutes,5);
 assert.equal(x.plannedSelectorToFillActiveMinutes,6);
});
test('historical market close convention changes correctly from 2024-11-05',()=>{
 assert.equal(next({session:'2024-11-01',intentMinute:899}),899);
 assert.equal(next({session:'2024-11-01',intentMinute:900}),null);
 assert.equal(next({session:'2024-11-05',intentMinute:900}),900);
 assert.equal(next({session:'2024-11-05',intentMinute:925}),null);
 assert.equal(elapsed({session:'2024-11-01',startMinute:900,endMinute:930}),0);
 assert.equal(elapsed({session:'2024-11-05',startMinute:900,endMinute:925}),25);
});
test('archived research bar matched time is NOT a broker fill price or live model rank',()=>{
 const a=audit({...base,archivedFillMinute:570,archivedFillDelay:0,
  archivedSelectorToFillDelay:5});
 assert.equal(a.archivedFillScheduleMatched,true);
 assert.equal(a.archivedFutureOpenPriceUsableForPreBuy,false);
 assert.equal(a.originalH2H3H5RankReproduced,false);
 assert.equal(a.orderTransmission,false);
});
test('archived missing bar moves fill to later bar; planned time mismatch is explicit',()=>{
 const a=audit({...base,archivedFillMinute:573,archivedFillDelay:3});
 assert.equal(a.archivedFillScheduleMatched,false);
 assert.equal(a.plannedNextEligibleResearchBarMinute,570);
});
test('numeric bad/future or old actual fill without known information cannot be promoted',()=>{
 assert.throws(()=>audit({...base,mode:'LIVE_TRADING'}),/FROZEN_ENTRY_REAL_EXECUTION_DISABLED/);
 assert.throws(()=>audit({...base,selectorMinute:580}),/FROZEN_ENTRY_INTENT_BEFORE_SELECTOR/);
 assert.throws(()=>audit({...base,intentMinute:2000}),/FROZEN_ENTRY_INTENT_MINUTE_INVALID/);
 assert.throws(()=>audit({...base,session:'2026-02-30'}),/FROZEN_ENTRY_SESSION_DATE_INVALID/);
 assert.throws(()=>audit({...base,archivedFillDelay:5}),/FROZEN_ENTRY_ARCHIVED_DELAY_WITHOUT_FILL/);
});
test('private historic row aggregate gives only summary counts, not symbol, open price or model scores',()=>{
 const rows=[
  {session:'2026-10-13',symbol:'1111.T',selector_minute:565,first_intent:{intent_minute:570},
   fill_minute:570,intent_to_fill_active_delay:0,selector_to_entry_active_delay:5,fill_price:2000},
  {session:'2026-10-13',symbol:'2222.T',selector_minute:565,first_intent:{intent_minute:570},
   fill_minute:573,intent_to_fill_active_delay:3,selector_to_entry_active_delay:8,fill_price:5000},
  {session:'2026-10-13',symbol:'3333.T',selector_minute:900,first_intent:{intent_minute:930},fill_minute:null}
 ];
 const x=summarize({mode,rows});
 assert.equal(x.total,3);assert.equal(x.archivedFilled,2);
 assert.equal(x.deterministicScheduleMatch,1);assert.equal(x.scheduleMismatch,1);
 assert.equal(x.noScheduledEligibleBar,1);
 assert.equal(JSON.stringify(x).includes('1111'),false);
 assert.equal(JSON.stringify(x).includes('2000'),false);
 assert.equal(x.researchModelRankReproduced,false);
});
