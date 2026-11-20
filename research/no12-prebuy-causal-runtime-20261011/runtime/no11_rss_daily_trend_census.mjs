/** RSS daily-close census only. Never imports a model, broker or order writer. */
import {classifyDailySmaStructure} from './no11_existing_selector_trend_prefilter.mjs';
import {isJpxCashTradingDay, JPX_CASH_CALENDAR_SOURCE} from './jpx_cash_calendar_2026_2027.mjs';

export const DAILY_SOURCE_SCHEMA = 'ARK_NO11_RSS_DAILY_CAPTURE_V1';
export const DAILY_PLAN_SCHEMA = 'ARK_NO11_RSS_DAILY_CENSUS_PLAN_V1';
export const DAILY_CENSUS_SCHEMA = 'ARK_NO11_RSS_DAILY_STRUCTURE_CENSUS_V1';
export const DAILY_HEADERS = Object.freeze(['銘柄名称','市場名称','足種','日付','時刻','始値','高値','安値','終値','出来高']);
export const ORIGINAL_SYMBOLS_SHA256 = '22d31026c76dd1a555a2deed2d2b5743004687a239dcc8856b5abeae47782056';
const problem = code => { throw Error('NO11_DAILY_' + code); };
const shift = (date, offset) => new Date(Date.parse(date + 'T00:00:00Z') + offset * 86400000).toISOString().slice(0, 10);
export function validSymbol(symbol) { return typeof symbol === 'string' && /^[0-9A-Z]{4}\.T$/.test(symbol); }
export function jstNow() { return new Date(Date.now() + 9 * 3600000).toISOString().slice(0, 23) + '+09:00'; }
export function validInstant(value) {
  if (typeof value !== 'string' || !/^20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?\+09:00$/.test(value)) return false;
  const ms = Date.parse(value);
  if (!Number.isFinite(ms)) return false;
  const normalized = new Date(ms + 9 * 3600000).toISOString();
  return normalized.slice(0, value.includes('.') ? 23 : 19) + '+09:00' === value;
}
export function lastCompletedSession(now) {
  if (!validInstant(now)) problem('CLOCK_INVALID');
  const date = now.slice(0, 10);
  // Conservative collection policy, NOT proof of provider finality.
  const offset = now.slice(11, 16) >= '18:00' ? 0 : 1;
  for (let i = offset; i < 15; i++) { const day = shift(date, -i); if (isJpxCashTradingDay(day)) return day; }
  problem('CALENDAR_INCOMPLETE');
}
export function requiredDailySessions(asOf) {
  if (!isJpxCashTradingDay(asOf)) problem('ASOF_NOT_CASH_SESSION');
  const days = [];
  for (let i = 0; i < 180 && days.length < 76; i++) {
    const day = shift(asOf, -i); if (isJpxCashTradingDay(day)) days.push(day);
  }
  if (days.length !== 76) problem('HISTORY_CALENDAR_INCOMPLETE');
  return days.reverse();
}
export function parseRequestSymbols(text) {
  const symbols = text.replace(/^\uFEFF/, '').split(/\r?\n/).map(x => x.trim()).filter(Boolean);
  if (!symbols.length || symbols.length > 5000 || symbols.some(x => !validSymbol(x)) || new Set(symbols).size !== symbols.length) problem('SYMBOL_LIST_INVALID');
  // The previous bulk request deliberately excluded the already captured Toyota.
  const baselineAdded = symbols.includes('7203.T') ? [] : ['7203.T'];
  return {symbols: [...symbols, ...baselineAdded], baselineAdded};
}
export function dailyFormula(symbol) {
  if (!validSymbol(symbol)) problem('SYMBOL_INVALID');
  return `=RssChart($A$2:$J$2,"${symbol}","D",100)`;
}
function decimal(value, zero = false) {
  return typeof value === 'string' && value.length <= 96 && /^(?:0|[1-9]\d*)(?:\.\d+)?$/.test(value) && Number.isFinite(Number(value)) && (zero ? Number(value) >= 0 : Number(value) > 0);
}
export function inspectDailyCapture(payload, plan) {
  if (!payload || payload.schemaId !== DAILY_SOURCE_SCHEMA || payload.planId !== plan.planId ||
      !plan.symbols.includes(payload.symbol) || payload.formula !== dailyFormula(payload.symbol) ||
      payload.asOfSession !== plan.asOfSession || payload.period !== 'D' ||
      payload.orderTransmission !== false || payload.productionReady !== false ||
      payload.priceBasis !== 'RSS_CHART_UNVERIFIED' || payload.decimalProvenance !== 'EXCEL_VALUE2_ROUNDTRIP' ||
      payload.corporateActionsCleared !== false || payload.originalVendorDecimalCertified !== false ||
      !validInstant(payload.observedStartJst) || !validInstant(payload.observedEndJst) ||
      payload.observedEndJst < payload.observedStartJst ||
      payload.observedStartJst < plan.createdAtJst ||
      payload.observedEndJst < plan.asOfSession + 'T18:00:00+09:00' ||
      !Array.isArray(payload.rows) || payload.rows.length > 100 ||
      !Number.isSafeInteger(payload.invalidRows) || payload.invalidRows < 0 ||
      !['OBSERVED','UNAVAILABLE'].includes(payload.status)) problem('CAPTURE_CONTRACT_INVALID');
  if ((payload.status === 'UNAVAILABLE') !== (payload.rows.length === 0)) problem('CAPTURE_STATUS_INVALID');
  const unknown = reason => ({symbol: payload.symbol, status: 'UNKNOWN', reason});
  if (payload.invalidRows > 0) return unknown('MALFORMED_SOURCE_ROWS');
  if (payload.status === 'UNAVAILABLE') return unknown('SOURCE_UNAVAILABLE');
  const wanted = new Set(plan.expectedSessions), values = new Map();
  let ignoredLaterRows = 0;
  for (const row of payload.rows) {
    // Date validation is calendar-backed; do not silently remove bad dates.
    if (typeof row?.session !== 'string' || !isJpxCashTradingDay(row.session)) return unknown('SOURCE_DATE_INVALID');
    if (row.session > plan.asOfSession) { ignoredLaterRows++; continue; }
    if (!wanted.has(row.session)) continue;
    if (values.has(row.session)) return unknown('DUPLICATE_SESSION');
    if (['open','high','low','close'].some(field => !decimal(row[field])) ||
        !decimal(row.volume, true) || !/^\d+$/.test(row.volume) ||
        Number(row.low) > Math.min(Number(row.open), Number(row.close)) ||
        Number(row.high) < Math.max(Number(row.open), Number(row.close))) return unknown('SOURCE_OHLCV_INVALID');
    values.set(row.session, row.close);
  }
  if (values.size !== 76) return unknown('REQUIRED_SESSIONS_MISSING');
  return {...classifyDailySmaStructure(plan.expectedSessions.map(day => values.get(day))), symbol: payload.symbol, ignoredLaterRows};
}
export function summarizeDailyCaptures(plan, captures) {
  if (plan?.schemaId !== DAILY_PLAN_SCHEMA || !Array.isArray(plan.symbols) ||
      !plan.symbols.length || plan.symbols.some(x => !validSymbol(x)) || new Set(plan.symbols).size !== plan.symbols.length ||
      JSON.stringify(plan.expectedSessions) !== JSON.stringify(requiredDailySessions(plan.asOfSession))) problem('PLAN_INVALID');
  const map = new Map();
  for (const capture of captures) {
    if (map.has(capture.symbol)) problem('DUPLICATE_CAPTURE');
    map.set(capture.symbol, inspectDailyCapture(capture, plan));
  }
  const details = plan.symbols.map(symbol => map.get(symbol) ?? {symbol, status: 'UNKNOWN', reason: 'NOT_CAPTURED'});
  const counts = {PASS: 0, WAIT: 0, REJECT: 0, UNKNOWN: 0}, reasons = {};
  for (const row of details) { counts[row.status]++; reasons[row.reason] = (reasons[row.reason] ?? 0) + 1; }
  const summary = {
    schemaId: DAILY_CENSUS_SCHEMA, status: captures.length === plan.symbols.length ? 'COMPLETE_OBSERVED_STRUCTURE_ONLY' : 'PARTIAL_OBSERVED_STRUCTURE_ONLY',
    planId: plan.planId, asOfSession: plan.asOfSession, historyStart: plan.expectedSessions[0], requiredSessions: 76,
    requestedSymbols: plan.symbols.length, capturedSymbols: captures.length, uncapturedSymbols: plan.symbols.length - captures.length,
    universeScope: 'HISTORICAL_REQUEST_LIST_PLUS_7203_NOT_CURRENT_DATED_MASTER',
    observedStructureCounts: counts, unknownReasons: Object.fromEntries(Object.entries(reasons).filter(([key]) => !['ALL_AXES_UP','MIXED_TREND_NOT_ADMITTED','NO_UP_AXES'].includes(key))),
    baselineSymbolAdded: plan.baselineAdded,
    capacity: {marketCeiling: 500, chartFunctionCeiling: 50, observedPass: counts.PASS,
      unresolved: counts.UNKNOWN, observedCountExceedsMarketCeiling: counts.PASS > 500,
      allUnknownCouldFitMarketCeiling: counts.PASS + counts.UNKNOWN <= 500,
      existingWorkbookCapacityCounted: false, fullMarketBreadthInputResolved: false,
      nativeMinuteVaResolved: false, liveCapacityCertified: false, truncated: false},
    admittedLiveSymbols: null, priceBasisCertified: false, corporateActionsCertified: false,
    originalVendorDecimalCertified: false, historicalKnownAtCertified: false,
    scope: 'ARITHMETIC_ON_RSS_OBSERVED_DAILY_CLOSES_NOT_TRADING_ADMISSION',
    sourceCalendar: JPX_CASH_CALENDAR_SOURCE, newFits: 0, selectorExecuted: false,
    originalIntradaySelectionScheduleModified: false, productionReady: false, orderTransmission: false,
  };
  return {summary, details};
}
