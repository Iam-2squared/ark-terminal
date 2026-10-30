/**
 * Existing No.1.1 G1 348 -> RSS CHART 50 capacity prescreen.
 *
 * Pure deterministic capacity allocation, NOT a fitted model, a new
 * once-daily Selector, or an order authority. It retains ALL ten original
 * Frozen Selector decision instants; only the observation universe changes.
 *
 * Previous close-only daily strength is a PREFERENCE for scarce chart slots,
 * NOT a forecast or a true Frozen Ridge score. Active Watch, held and pending
 * positions remain pinned for continued P1/State9/EXIT observation.
 */
import {createHash} from 'node:crypto';
import {inspectDailyCapture,summarizeDailyCaptures}
  from './no11_rss_daily_trend_census.mjs';
import {OBSERVED_PASS_GATE_ID}
  from './no11_observed_pass_watch_gate.mjs';
import {isJpxCashTradingDay,previousJpxCashTradingDays}
  from './jpx_cash_calendar_2026_2027.mjs';

export const CHART50_PLAN_SCHEMA='ARK_NO11_G1_PASS_CHART50_SHADOW_CAPACITY_V1';
const SYMBOL=/^[0-9A-Z]{4}\.T$/;
const fail=code=>{throw Error('NO11_CHART50_'+code)};
const check=(ok,code)=>{if(!ok)fail(code)};
const sha=data=>createHash('sha256').update(JSON.stringify(data)).digest('hex');
function distinctSymbols(values,label){
  check(Array.isArray(values),label+'_REQUIRED');
  const seen=new Set();
  for(const v of values){
    check(typeof v==='string'&&SYMBOL.test(v),label+'_SYMBOL_INVALID');
    check(!seen.has(v),label+'_DUPLICATE');
    seen.add(v);
  }
  return values;
}
/** Strength is the minimum of 8 strictly positive daily up margins,
 * with the mean as tie-breaker. This is a rule, NOT a trained estimator. */
export function dailyG1CapacityPriority(expectedSessions,rows){
  check(Array.isArray(expectedSessions)&&expectedSessions.length===76,
    'EXPECTED_DAILY_SESSIONS_REQUIRED');
  check(Array.isArray(rows),'DAILY_ROWS_REQUIRED');
  const source=new Map();
  for(const row of rows){
    if(!expectedSessions.includes(row?.session))continue;
    check(!source.has(row.session),'DUPLICATE_DAILY_DATE');
    check(typeof row.close==='string'&&
      /^(?:0|[1-9]\d*)(?:\.\d+)?$/.test(row.close),
      'DAILY_CLOSE_NOT_ORIGINAL_DECIMAL');
    const n=Number(row.close);
    check(Number.isFinite(n)&&n>0,'DAILY_CLOSE_INVALID');
    source.set(row.session,n);
  }
  check(source.size===76,'DAILY_HISTORY_INCOMPLETE');
  const prices=expectedSessions.map(d=>source.get(d));
  const last=prices[75],margins=[];
  for(const n of [5,15,25,75]){
    const old=prices[75-n];
    const average=prices.slice(76-n).reduce((a,b)=>a+b,0)/n;
    const slope=100*(last/old-1);
    const elevation=100*(last/average-1);
    check(Number.isFinite(slope)&&Number.isFinite(elevation)&&
      slope>0&&elevation>0,'NOT_G1_ALL_UP');
    margins.push(slope,elevation);
  }
  return Object.freeze({
    minMarginPct:Math.min(...margins),
    meanMarginPct:margins.reduce((a,b)=>a+b,0)/margins.length
  });
}
export function rankVerifiedG1PassForChartBudget(plan,captures,mask){
  check(mask?.schemaId===OBSERVED_PASS_GATE_ID&&
    mask.asOfSession===plan?.asOfSession&&
    mask.planId===plan?.planId&&
    mask.shadowOnly===true&&mask.productionReady===false&&
    mask.orderTransmission===false,'G1_MASK_NOT_SAFE');
  const {summary}=summarizeDailyCaptures(plan,captures);
  check(summary.status==='COMPLETE_OBSERVED_STRUCTURE_ONLY',
    'COMPLETE_ORIGINAL_CAPTURE_REQUIRED');
  const passes=new Set(mask.observedPassSymbols);
  distinctSymbols(mask.observedPassSymbols,'G1_PASS');
  check(passes.size===summary.observedStructureCounts.PASS,
    'G1_PASS_COUNT_MISMATCH');
  const ranked=[];
  for(const row of captures){
    const classification=inspectDailyCapture(row,plan);
    const allowed=passes.has(row.symbol);
    check(allowed===(classification.status==='PASS'),'G1_MEMBERSHIP_MISMATCH');
    if(!allowed)continue;
    ranked.push({symbol:row.symbol,
      ...dailyG1CapacityPriority(plan.expectedSessions,row.rows)});
  }
  check(ranked.length===passes.size,'CAPTURE_G1_COVERAGE_INCOMPLETE');
  ranked.sort((a,b)=>b.minMarginPct-a.minMarginPct||
    b.meanMarginPct-a.meanMarginPct||a.symbol.localeCompare(b.symbol));
  return ranked;
}
export function makeNo11G1Chart50Plan({
  mask,priorityRows,sessionDate,
  heldSymbols=[],activeWatchSymbols=[],pendingOrderSymbols=[],
  otherChartFunctions=0,emptySafetySlots=3,
  otherQuoteCapacity=0,otherQuoteSymbols=[],
  // Optional VERIFIED, session-scoped ordinary-equity source whitelist for
  // first LIVE admissions. Never a replacement for actual datedMaster proof.
  reviewedEntrySymbols=null,reviewedEvidenceSha256=null
}={}){
  check(mask?.schemaId===OBSERVED_PASS_GATE_ID&&
    mask.shadowOnly===true&&mask.productionReady===false&&
    mask.orderTransmission===false&&
    mask.strictNoUnknownFallback===true,'MASK_NOT_SAFE');
  check(typeof sessionDate==='string'&&isJpxCashTradingDay(sessionDate),
    'SESSION_INVALID');
  check(mask.asOfSession===previousJpxCashTradingDays(sessionDate,1)[0],
    'LATEST_PREVIOUS_DAY_MASK_REQUIRED');
  const pass=distinctSymbols(mask.observedPassSymbols,'G1_PASS');
  const scoped=reviewedEntrySymbols!==null || reviewedEvidenceSha256!==null;
  if(scoped){
    check(typeof reviewedEvidenceSha256==='string'&&/^[a-f0-9]{64}$/.test(reviewedEvidenceSha256),
      'REVIEWED_EQUITY_EVIDENCE_SHA_REQUIRED');
    check(Array.isArray(reviewedEntrySymbols)&&reviewedEntrySymbols.length>=1,
      'REVIEWED_EQUITY_SYMBOLS_REQUIRED');
    distinctSymbols(reviewedEntrySymbols,'REVIEWED_EQUITY');
    const passSet=new Set(pass);
    check(reviewedEntrySymbols.every(x=>passSet.has(x)),'REVIEWED_EQUITY_NOT_G1_PASS');
    // Prevent the known 2026-10-30 ETF/ETN leak independently of the broker
    // Python + JS transport BUY-deny checks. This is not an exhaustive banlist.
    const banned=new Set(['1671.T','1690.T','1699.T','2014.T','2038.T']);
    check(!reviewedEntrySymbols.some(x=>banned.has(x)),'REVIEWED_NON_EQUITY');
  }
  check(mask.observedPassCount===pass.length&&pass.length>=1&&pass.length<=500,
    'G1_PASS_CAP_INVALID');
  const ranks=priorityRows;
  check(Array.isArray(ranks)&&ranks.length===pass.length,
    'PRIORITIES_REQUIRED_FOR_ALL_G1_PASS');
  const all=new Set(pass),seenRanked=new Set();
  for(const p of ranks){
    check(p&&typeof p.symbol==='string'&&all.has(p.symbol)&&
      !seenRanked.has(p.symbol)&&
      typeof p.minMarginPct==='number'&&Number.isFinite(p.minMarginPct)&&
      p.minMarginPct>0&&typeof p.meanMarginPct==='number'&&
      Number.isFinite(p.meanMarginPct)&&p.meanMarginPct>0,
      'PRIORITY_DATA_INVALID');
    seenRanked.add(p.symbol);
  }
  const positions=distinctSymbols(heldSymbols,'HELD');
  const watches=distinctSymbols(activeWatchSymbols,'WATCH');
  const pending=distinctSymbols(pendingOrderSymbols,'PENDING');
  const otherQuote=distinctSymbols(otherQuoteSymbols,'OTHER_QUOTE');
  const pinned=[...new Set([...positions,...watches,...pending])];
  check(Number.isInteger(otherChartFunctions)&&
    otherChartFunctions>=0&&otherChartFunctions<=50,
    'OTHER_CHART_FUNCTIONS_INVALID');
  check(Number.isInteger(emptySafetySlots)&&
    emptySafetySlots>=0&&emptySafetySlots<=10,
    'EMPTY_SLOT_RESERVE_INVALID');
  check(Number.isInteger(otherQuoteCapacity)&&otherQuoteCapacity>=0&&
    otherQuoteCapacity<=500,'OTHER_QUOTE_CAPACITY_INVALID');
  const quoteSet=new Set([...pass,...pinned,...otherQuote]);
  check(quoteSet.size+otherQuoteCapacity<=500,'MARKET_500_CAPACITY_EXCEEDED');
  const budget=50-otherChartFunctions;
  check(pinned.length<=budget,'PROTECTED_WATCH_OR_EXIT_OVER_CHART_CAP');
  const afterProtected=budget-pinned.length;
  const reserved=Math.min(emptySafetySlots,afterProtected);
  const scanBudget=afterProtected-reserved;
  const pinnedSet=new Set(pinned);
  const reviewed=new Set(scoped?reviewedEntrySymbols:pass);
  const eligible=ranks
    .filter(p=>!pinnedSet.has(p.symbol)&&reviewed.has(p.symbol))
    .sort((a,b)=>b.minMarginPct-a.minMarginPct||
      b.meanMarginPct-a.meanMarginPct||a.symbol.localeCompare(b.symbol));
  const scan=eligible.slice(0,scanBudget).map(p=>p.symbol);
  const charts=[...pinned,...scan];
  // Protected holdings/watch remain chart-observed for original EXIT. In the
  // narrow first-BUY profile, an unreviewed protected symbol is NOT admitted
  // to the Selector, even if it remains watched for exit continuity.
  const selectorInput=charts.filter(s=>all.has(s)&&reviewed.has(s));
  check(new Set(charts).size===charts.length &&
    charts.length+otherChartFunctions<=50,
    'CHART_FUNCTION_BUDGET_BREACH');
  const core={
    schemaId:CHART50_PLAN_SCHEMA,
    sessionDate,asOfSession:mask.asOfSession,sourcePlanId:mask.planId,
    selectionMethod:'G1_COMPLETE_DAILY_STRENGTH_MIN8_THEN_MEAN8_NO_TRAINING',
    observedG1PassCount:pass.length,
    ...(scoped?{
      entryUniverseMode:'EXPLICIT_REVIEWED_EQUITY_ONLY_NOT_AUTOMATICALLY_CERTIFIED',
      reviewedEntrySymbols:[...reviewedEntrySymbols],
      reviewedEntryEvidenceSha256:reviewedEvidenceSha256,
      unreviewedG1SymbolsExcludedFromEntry:pass.filter(x=>!reviewed.has(x)).length
    }:{}),
    heldSymbols:[...positions],activeWatchSymbols:[...watches],
    pendingOrderSymbols:[...pending],
    protectedChartSymbols:pinned,
    scanChartSymbols:scan,allRequestedChartSymbols:charts,
    selectorInputSymbols:selectorInput,
    g1UnscannedCount:pass.filter(s=>!selectorInput.includes(s)).length,
    occupiedByOtherChartFunctions:otherChartFunctions,
    reserveEmptyChartSlots:reserved,
    arkChartsUsed:charts.length,
    totalChartFunctionsBudgeted:otherChartFunctions+charts.length,
    chartFunctionLimit:50,existingOtherQuoteSlots:otherQuoteCapacity,
    totalQuoteSlotsBudgeted:quoteSet.size+otherQuoteCapacity,
    marketQuoteLimit:500,
    originalFrozenDecisionTimesModified:false,
    originalFrozenWeightsModified:false,
    originalSelectorPopulationPreserved:false,
    crossSectionBreadthChangedByUpstreamScreen:true,
    exactMinuteVaProvided:false,
    liveChartAllocationObserved:false,
    originalNativeSelectorConnected:false,
    shadowOnly:true,productionReady:false,orderTransmission:false
  };
  return Object.freeze({...core,planSha256:sha(core)});
}
export function validateNo11Chart50Plan({chartPlan,mask,sessionDate}={}){
  check(chartPlan?.schemaId===CHART50_PLAN_SCHEMA,
    'PLAN_SCHEMA_REQUIRED');
  const {planSha256,...body}=chartPlan;
  check(typeof planSha256==='string'&&
    planSha256===sha(body),'PLAN_HASH_MISMATCH');
  check(chartPlan.productionReady===false&&
    chartPlan.orderTransmission===false&&chartPlan.shadowOnly===true,
    'PLAN_TRADING_STATE_INVALID');
  check(chartPlan.sessionDate===sessionDate&&
    chartPlan.asOfSession===mask?.asOfSession&&
    chartPlan.sourcePlanId===mask?.planId&&
    chartPlan.observedG1PassCount===mask?.observedPassCount,
    'PLAN_MASK_OR_DAY_MISMATCH');
  const pass=new Set(distinctSymbols(mask.observedPassSymbols,'G1_PASS'));
  const selected=distinctSymbols(chartPlan.selectorInputSymbols,'SELECTOR_INPUT');
  const charts=distinctSymbols(chartPlan.allRequestedChartSymbols,'CHART_FUNCTION');
  const pinned=distinctSymbols(chartPlan.protectedChartSymbols,'PINNED');
  const scan=distinctSymbols(chartPlan.scanChartSymbols,'SCAN');
  const scoped=chartPlan.entryUniverseMode!==undefined;
  if(scoped){
    const reviewed=distinctSymbols(chartPlan.reviewedEntrySymbols,'REVIEWED_EQUITY');
    const denied=new Set(['1671.T','1690.T','1699.T','2014.T','2038.T']);
    check(chartPlan.entryUniverseMode==='EXPLICIT_REVIEWED_EQUITY_ONLY_NOT_AUTOMATICALLY_CERTIFIED'&&
      typeof chartPlan.reviewedEntryEvidenceSha256==='string'&&
      /^[a-f0-9]{64}$/.test(chartPlan.reviewedEntryEvidenceSha256)&&
      reviewed.length>=1&&reviewed.every(s=>pass.has(s)&&!denied.has(s))&&
      chartPlan.unreviewedG1SymbolsExcludedFromEntry===pass.size-reviewed.length&&
      selected.every(s=>reviewed.includes(s))&&
      scan.every(s=>reviewed.includes(s)),'REVIEWED_EQUITY_SCOPE_OR_EVIDENCE_INVALID');
  }
  check(selected.length>0&&selected.every(s=>pass.has(s))&&
    selected.every(s=>charts.includes(s))&&
    pinned.every(s=>charts.includes(s))&&
    scan.every(s=>pass.has(s))&&
    chartPlan.arkChartsUsed===charts.length&&
    chartPlan.totalChartFunctionsBudgeted===
      chartPlan.arkChartsUsed+chartPlan.occupiedByOtherChartFunctions&&
    chartPlan.totalChartFunctionsBudgeted<=50&&
    chartPlan.totalQuoteSlotsBudgeted<=500&&
    chartPlan.originalFrozenWeightsModified===false&&
    chartPlan.originalFrozenDecisionTimesModified===false&&
    chartPlan.originalSelectorPopulationPreserved===false&&
    chartPlan.productionReady===false,'CHART_50_BUDGET_OR_MEMBERSHIP_INVALID');
  return Object.freeze([...selected]);
}
