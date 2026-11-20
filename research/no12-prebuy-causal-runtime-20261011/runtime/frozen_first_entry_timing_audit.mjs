/**
 * Strict read-only chronology of original FIRST ENTRY v2 research timing.
 * References (immutable):
 * persistent-watchlist-uptrend-first-entry-20261003-v2/{common.py,first_entry.py,teacher.py}
 * and capital-v5-max3-slot-intelligence-20261004-v1/core_features.py.
 * The planned next regular-open minute can be computed from the date/clock,
 * but next open PRICE and any actual broker fill are NOT thereby known.
 * This is a diagnostic only, never a substitute ML model, score or order.
 */
export const ORIGINAL_ENTRY_TIMING_RESEARCH_SCHEMA='ARK_NO11_FROZEN_FIRST_ENTRY_TIMING_AUDIT_V1';
const fail=s=>{throw Error(s)};
const numericMinute=(v,label)=>{
 if(!Number.isInteger(v)||v<0||v>1440)fail(label);
 return v;
};
const date=(value)=>{
 if(typeof value!=='string'||!/^\d{4}-\d\d-\d\d$/.test(value)||
    !Number.isFinite(Date.parse(value+'T00:00:00Z'))||
    new Date(value+'T00:00:00Z').toISOString().slice(0,10)!==value)
    fail('FROZEN_ENTRY_SESSION_DATE_INVALID');
 return value;
};
/** Byte-equivalent to original common.py regular_starts(day) except opening
 * auction first minutes 09:00 and 12:30 excluded by teacher.next_fill. */
export function originalResearchNextEligibleFillMinute({session,intentMinute}={}){
 const d=date(session),at=numericMinute(intentMinute,'FROZEN_ENTRY_INTENT_MINUTE_INVALID');
 const pmEnd=d<'2024-11-05'?900:925;
 for(const [start,end] of [[541,690],[751,pmEnd]]){
  const next=Math.max(start,at);
  if(next<end)return next;
 }
 return null;
}
/** Byte-equivalent to common.active_elapsed for actual regular sessions. */
export function originalResearchActiveElapsed({session,startMinute,endMinute}={}){
 const d=date(session),a=numericMinute(startMinute,'FROZEN_ENTRY_START_INVALID'),
   b=numericMinute(endMinute,'FROZEN_ENTRY_END_INVALID');
 if(b<a)fail('FROZEN_ENTRY_ACTIVE_TIME_REVERSED');
 const pmEnd=d<'2024-11-05'?900:925;
 return [[540,690],[750,pmEnd]].reduce((n,[lo,hi])=>
   n+Math.max(0,Math.min(b,hi)-Math.max(a,lo)),0);
}
export function auditNo11OriginalScheduledEntryClock({
 mode,session,selectorMinute,intentMinute,archivedFillMinute=null,
 archivedFillDelay=null,archivedSelectorToFillDelay=null
}={}){
 if(mode!=='SYNTHETIC_OFFLINE_ONLY')fail('FROZEN_ENTRY_REAL_EXECUTION_DISABLED');
 const d=date(session),selector=numericMinute(selectorMinute,'FROZEN_ENTRY_SELECTOR_MINUTE_INVALID'),
  intent=numericMinute(intentMinute,'FROZEN_ENTRY_INTENT_MINUTE_INVALID');
 if(intent<selector)fail('FROZEN_ENTRY_INTENT_BEFORE_SELECTOR');
 const planned=originalResearchNextEligibleFillMinute({session:d,intentMinute:intent});
 const selectorWait=originalResearchActiveElapsed({session:d,startMinute:selector,endMinute:intent});
 const plannedIntentToFill=planned===null?null:originalResearchActiveElapsed({session:d,startMinute:intent,endMinute:planned});
 const plannedSelectorToFill=planned===null?null:originalResearchActiveElapsed({session:d,startMinute:selector,endMinute:planned});
 // Archived fills are private historical counterfactual evidence ONLY.
 // These comparisons must never become pre-buy available inputs.
 const archivedPresent=archivedFillMinute!==null;
 if(archivedPresent)numericMinute(archivedFillMinute,'FROZEN_ENTRY_ARCHIVED_FILL_INVALID');
 if((archivedFillDelay!==null||archivedSelectorToFillDelay!==null)&&!archivedPresent)
   fail('FROZEN_ENTRY_ARCHIVED_DELAY_WITHOUT_FILL');
 if(archivedFillDelay!==null&&(!Number.isInteger(archivedFillDelay)||archivedFillDelay<0))
   fail('FROZEN_ENTRY_ARCHIVED_DELAY_INVALID');
 if(archivedSelectorToFillDelay!==null&&(!Number.isInteger(archivedSelectorToFillDelay)||archivedSelectorToFillDelay<0))
   fail('FROZEN_ENTRY_ARCHIVED_SELECTOR_DELAY_INVALID');
 const compare=archivedPresent?(planned===archivedFillMinute&&
    (archivedFillDelay===null||plannedIntentToFill===archivedFillDelay)&&
    (archivedSelectorToFillDelay===null||plannedSelectorToFill===archivedSelectorToFillDelay)) : null;
 return Object.freeze({schemaId:ORIGINAL_ENTRY_TIMING_RESEARCH_SCHEMA,
  status:planned===null?'NO_NEXT_RESEARCH_REGULAR_FILL':'SCHEDULE_ONLY_NOT_ACTUAL_FILL',
  session:d,selectorMinute:selector,intentMinute:intent,
  plannedNextEligibleResearchBarMinute:planned,
  selectorToIntentActiveMinutes:selectorWait,
  plannedIntentToFillActiveMinutes:plannedIntentToFill,
  plannedSelectorToFillActiveMinutes:plannedSelectorToFill,
  archivedFillScheduleMatched:compare,
  // The critical gap. At intent we know only planned TIME, not future next OPEN.
  modelFieldAvailabilityBeforePurchase:Object.freeze({
   'entry/p1_score':'AVAILABLE_IF_FIRST_ENTRY_PRODUCER_VERIFIED',
   'entry/p1_threshold':'AVAILABLE_IF_FIRST_ENTRY_PRODUCER_VERIFIED',
   'entry/intent_clock':'AVAILABLE',
   'selector/to_intent_active_delay':'AVAILABLE',
   'entry/fill_clock':'PLANNED_CLOCK_ONLY_ACTUAL_FILL_UNPROVEN',
   'entry/intent_to_fill_active_delay':'PLANNED_DELAY_ONLY_ACTUAL_FILL_UNPROVEN',
   'selector/to_entry_active_delay':'PLANNED_DELAY_ONLY_ACTUAL_FILL_UNPROVEN',
   'selector/raw_entry_vs_first_price_pct':'FUTURE_NEXT_OPEN_PRICE_UNKNOWN',
   'state/path_as_of_planned_fill':'SOURCE_ARRIVAL_NOT_VERIFIED'
  }),
  archivedFutureOpenPriceUsableForPreBuy:false,
  originalH2H3H5RankReproduced:false,
  frozenNo11Changed:false,productionReady:false,orderTransmission:false});
}
export function summarizeNo11OriginalClockParity({mode,rows=[]}={}){
 if(mode!=='SYNTHETIC_OFFLINE_ONLY')fail('FROZEN_ENTRY_REAL_EXECUTION_DISABLED');
 if(!Array.isArray(rows)||rows.length>100000)fail('FROZEN_ENTRY_AUDIT_ROWS_INVALID');
 const summary={total:0,archivedFilled:0,archivedNoFill:0,
  deterministicScheduleMatch:0,scheduleMismatch:0,noScheduledEligibleBar:0};
 for(const row of rows){
  const checked=auditNo11OriginalScheduledEntryClock({mode,session:row.session,
   selectorMinute:row.selector_minute,intentMinute:row.first_intent?.intent_minute,
   archivedFillMinute:row.fill_minute??null,
   archivedFillDelay:row.intent_to_fill_active_delay??null,
   archivedSelectorToFillDelay:row.selector_to_entry_active_delay??null});
  summary.total++;
  if(checked.plannedNextEligibleResearchBarMinute===null)summary.noScheduledEligibleBar++;
  if(row.fill_minute===null||row.fill_minute===undefined)summary.archivedNoFill++;
  else{
   summary.archivedFilled++;
   if(checked.archivedFillScheduleMatched)summary.deterministicScheduleMatch++;
   else summary.scheduleMismatch++;
  }
 }
 return Object.freeze({...summary,
  status:'PRIVATE_HISTORICAL_TIME_PARITY_AUDIT_ONLY',
  archivedNextOpenPricesInspected:false,brokerActualFillCertified:false,
  researchModelRankReproduced:false,productionReady:false,orderTransmission:false});
}
