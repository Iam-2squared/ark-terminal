/**
 * Read-only optional upstream eligibility gate for the EXISTING No.1.1 Selector.
 * This is only the donor design's SMA G1, not the donor model/preopen selection.
 *
 * No scanning schedule, ranking, Watch, First Entry, portfolio, or execution
 * policy is defined here. The frozen Selector itself is not modified.
 * Data/source certification and comparative market validation are outstanding.
 */

export const TREND_GATE_ID = 'NO11_OPTIONAL_DAILY_G1_ALL_AXES_UP_V1';
export const DAILY_SMA_PERIODS = Object.freeze([5, 15, 25, 75]);
const WINDOW = 76;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const CLOSE_RE = /^(?:0|[1-9]\d*)(?:\.\d+)?$/;
const JST_TIME_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+09:00$/;

function fail(code) {
  throw new Error('NO11_TREND_G1_' + code);
}
function validDate(value) {
  return typeof value === 'string' && DATE_RE.test(value) &&
    !Number.isNaN(Date.parse(value + 'T00:00:00Z')) &&
    new Date(value + 'T00:00:00Z').toISOString().slice(0, 10) === value;
}
function jstInstant(value) {
  if (typeof value !== 'string' || !JST_TIME_RE.test(value)) return null;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}
function positiveDecimal(value) {
  if (typeof value !== 'string' || !CLOSE_RE.test(value)) return null;
  const parts = value.split('.');
  const digits = parts[0] + (parts[1] ?? '');
  const coefficient = BigInt(digits);
  return coefficient > 0n ? {coefficient, precision: (parts[1] ?? '').length} : null;
}

export function validateExchangeCalendar(session, tradingSessions) {
  if (!validDate(session) || !Array.isArray(tradingSessions) ||
      tradingSessions.length < WINDOW + 1) fail('EXCHANGE_CALENDAR_REQUIRED');
  for (let i = 0; i < tradingSessions.length; i++) {
    if (!validDate(tradingSessions[i]) ||
        (i > 0 && tradingSessions[i] <= tradingSessions[i - 1]))
      fail('EXCHANGE_CALENDAR_INVALID');
  }
  const position = tradingSessions.indexOf(session);
  if (position < WINDOW) fail('EXCHANGE_CALENDAR_COVERAGE_INSUFFICIENT');
  return Object.freeze(tradingSessions.slice(position - WINDOW, position));
}

/**
 * Evaluate one symbol against EXACT previous-session daily closes.
 * Caller must establish the official trading calendar and comparable RAW
 * prices, including corporate-action handling, before attempting admission.
 */
export function evaluateOriginalSelectorTrendG1({
  instrument, expectedSessions, decisionCutoffJst,
}) {
  if (!Array.isArray(expectedSessions) || expectedSessions.length !== WINDOW)
    fail('EXPECTED_SESSIONS_INVALID');
  const cutoff = jstInstant(decisionCutoffJst);
  if (cutoff === null) fail('DECISION_CUTOFF_INVALID');
  const unknown = reason => ({
    status: 'UNKNOWN', reason, axes: {long: null, medium: null, short: null},
    dailySmaUp: null,
  });
  if (!instrument || !Array.isArray(instrument.bars))
    return unknown('DAILY_HISTORY_MISSING');
  if (instrument.priceBasis !== 'COMPARABLE_RAW' ||
      instrument.corporateActionsCleared !== true)
    return unknown('PRICE_BASIS_OR_CORPORATE_ACTION_NOT_VERIFIED');
  const wanted = new Set(expectedSessions);
  const mapped = new Map();
  for (const bar of instrument.bars) {
    if (!bar || !wanted.has(bar.session)) continue;
    if (mapped.has(bar.session)) return unknown('DUPLICATE_SESSION');
    mapped.set(bar.session, bar);
  }
  if (mapped.size !== WINDOW) return unknown('REQUIRED_DAILY_HISTORY_MISSING');
  const observed = [];
  for (const session of expectedSessions) {
    const bar = mapped.get(session);
    const instant = jstInstant(bar.knownAtJst);
    if (instant === null || instant > cutoff ||
        !bar.knownAtJst.startsWith(session) &&
        // Corrected/retrieved older histories can be first observed later;
        // only require receipt <= decision, never invent an earlier time.
        !validDate(bar.knownAtJst?.slice(0, 10)))
      return unknown('KNOWN_AT_MISSING_OR_LATE');
    const value = positiveDecimal(bar.close);
    if (value === null) return unknown('CLOSE_INVALID_OR_NOT_ORIGINAL_DECIMAL');
    observed.push(value);
  }
  const precision = Math.max(...observed.map(x => x.precision));
  const prices = observed.map(x =>
    x.coefficient * 10n ** BigInt(precision - x.precision));
  const newest = prices[WINDOW - 1];
  const up = n => {
    const old = prices[WINDOW - 1 - n];
    const smaSum = prices.slice(WINDOW - n).reduce((a, b) => a + b, 0n);
    return newest > old && BigInt(n) * newest > smaSum;
  };
  const smaUp = {
    5: up(5), 15: up(15), 25: up(25), 75: up(75),
  };
  const axes = {
    long: smaUp[75],
    medium: smaUp[25] && smaUp[15],
    short: smaUp[5],
  };
  const numberUp = Object.values(axes).filter(Boolean).length;
  const status = numberUp === 3 ? 'PASS' : numberUp === 0 ? 'REJECT' : 'WAIT';
  return {status, reason: status === 'PASS' ? 'ALL_AXES_UP' :
    status === 'WAIT' ? 'MIXED_TREND_NOT_ADMITTED' : 'NO_UP_AXES',
  axes, dailySmaUp: smaUp};
}

/**
 * Optional PRE-selector universe gate, not a once-per-day Selector.
 * Run the existing original Selector at all of its original times on the
 * eligible identity set, ONLY after coverage/capacity tests pass.
 */
export function prefilterOriginalSelectorUniverse({
  session, decisionCutoffJst, tradingSessions, instruments, rssMarketCap = 500,
}) {
  const expectedSessions = validateExchangeCalendar(session, tradingSessions);
  if (typeof decisionCutoffJst !== 'string' ||
      !decisionCutoffJst.startsWith(session + 'T') ||
      jstInstant(decisionCutoffJst) === null)
    fail('DECISION_CUTOFF_INVALID');
  if (!Array.isArray(instruments) || !Number.isSafeInteger(rssMarketCap) ||
      rssMarketCap <= 0) fail('UNIVERSE_INPUT_INVALID');
  const eligibleSymbols = [];
  const results = [];
  const counts = {PASS: 0, WAIT: 0, REJECT: 0, UNKNOWN: 0};
  const seen = new Set();
  for (const instrument of instruments) {
    if (!instrument || typeof instrument.symbol !== 'string' ||
        !instrument.symbol.trim() || seen.has(instrument.symbol))
      fail('SYMBOL_IDENTITY_INVALID');
    seen.add(instrument.symbol);
    const result = evaluateOriginalSelectorTrendG1({
      instrument, expectedSessions, decisionCutoffJst,
    });
    counts[result.status] += 1;
    results.push({symbol: instrument.symbol, ...result});
    if (result.status === 'PASS') eligibleSymbols.push(instrument.symbol);
  }
  return {
    schemaId: TREND_GATE_ID, session, expectedLatestSession: expectedSessions.at(-1),
    decisionCutoffJst, evaluated: results.length, counts, eligibleSymbols,
    results, rssMarketCap, withinRssMarketCap: eligibleSymbols.length <= rssMarketCap,
    truncatedForCap: false, frozenSelectorAlgorithmModified: false,
    originalIntradaySelectionScheduleModified: false,
    newModelTraining: false, marketPerformanceCertified: false,
    actualProviderReceiptCertified: false, productionReady: false,
    orderTransmission: false,
  };
}
