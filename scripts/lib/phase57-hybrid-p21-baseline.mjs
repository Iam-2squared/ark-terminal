import { createHash } from 'node:crypto';

// Offline measurement helpers only. No provider, selector, model-fitting or order calls.
export const SAFETY = Object.freeze(Object.fromEntries([
  'executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed', 'rssOrderFunctionAllowed',
  'liveTradingAllowed', 'paperTradingAllowed', 'automaticPromotionAllowed', 'productionUpdateAllowed', 'transmitted',
].map(key => [key, false])));
export const MODEL_DIGEST = '444e296d31b0e59263f268706b4c8a7c7e9e59d6f7c9547e9f90342a24040fc2';
export const FREEZE_DIGEST = 'a744d599e430d23efe4dea6600e418d3410d8a18df5055b35e1cc71432bf64da';
export const HORIZONS = Object.freeze([1, 3, 6, 12]);
const FIVE_MINUTES = 300000;
const sha = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
const timestamp = value => {
  if (typeof value !== 'string' || !/(Z|[+-]\d{2}:\d{2})$/.test(value) || !Number.isFinite(Date.parse(value))) throw new Error('EXPLICIT_TIMESTAMP_REQUIRED');
  return Date.parse(value);
};
export const sessionOf = value => new Date(timestamp(value) + 9 * 3600000).toISOString().slice(0, 10);
function expectedStarts(decisionAt, count) {
  const date = sessionOf(decisionAt);
  const close = timestamp(`${date}T${date < '2024-11-05' ? '15:00' : '15:30'}:00+09:00`);
  const lunchStart = timestamp(`${date}T11:30:00+09:00`), lunchEnd = timestamp(`${date}T12:30:00+09:00`);
  const starts = []; let t = timestamp(decisionAt);
  for (let i = 0; i < count; i++) {
    if (t >= lunchStart && t < lunchEnd) t = lunchEnd;
    starts.push(t < close ? t : null); t += FIVE_MINUTES;
  }
  return starts;
}
const finite = x => typeof x === 'number' && Number.isFinite(x);
const mean = xs => xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null;
const median = xs => { const a = [...xs].sort((x, y) => x - y); return a.length ? (a[Math.floor((a.length - 1) / 2)] + a[Math.floor(a.length / 2)]) / 2 : null; };

export function verifyFreeze(model, freeze) {
  const { modelDigest, ...modelCore } = model;
  const { freezeSha256, ...freezeCore } = freeze;
  if (modelDigest !== MODEL_DIGEST || sha(modelCore) !== MODEL_DIGEST || freeze.modelDigest !== MODEL_DIGEST || freezeSha256 !== FREEZE_DIGEST || sha(freezeCore) !== FREEZE_DIGEST) throw new Error('FROZEN_HYBRID_MISMATCH');
  return true;
}

export function timeBucket(value) {
  const time = new Date(timestamp(value) + 9 * 3600000).toISOString().slice(11, 16);
  if (time >= '09:00' && time < '10:30') return 'MORNING_EARLY';
  if (time >= '10:30' && time <= '11:30') return 'MORNING_LATE';
  if (time >= '12:30' && time < '14:00') return 'AFTERNOON_EARLY';
  if (time >= '14:00' && time <= '15:30') return 'AFTERNOON_LATE';
  throw new Error('OUTSIDE_SESSION');
}

export function auditAdmission(input) {
  const blockers = [];
  for (const key of ['sourceRightsConfirmed', 'rawDataAvailable', 'sourceFingerprintsVerified', 'selectorAdapterParityVerified', 'p21AdapterParityVerified', 'priorHistoryAvailable', 'corporateActionBasisVerified', 'costContractVerified']) {
    if (input[key] !== true) blockers.push(key);
  }
  if (input.role !== 'ENTRY_DEVELOPMENT_DIAGNOSTIC') blockers.push('INVALID_ROLE');
  if (input.sourceClass !== 'HISTORICAL_RECONSTRUCTION_LATER_FETCHED') blockers.push('INVALID_SOURCE_CLASS');
  if (input.formalOos !== false || input.modelFittingAllowed !== false) blockers.push('FORBIDDEN_PROMOTION');
  if (!Array.isArray(input.sessions) || !input.sessions.length || new Set(input.sessions).size !== input.sessions.length) blockers.push('EMPTY_OR_DUPLICATE_SESSIONS');
  const allowed = new Set(input.precommittedSessions ?? []);
  const protectedDates = new Set(input.protectedSessions ?? []);
  for (const date of input.sessions ?? []) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !allowed.has(date) || protectedDates.has(date)) blockers.push('SESSION_NOT_RELEASED');
    if (input.baselineClass === 'CURRENT_FROZEN_P21_BASELINE' && date < '2026-08-13') blockers.push('CURRENT_P21_HISTORY_OUTSIDE_CAUSAL_WINDOW');
  }
  if (input.baselineClass !== 'CURRENT_FROZEN_P21_BASELINE') blockers.push('DIFFERENT_BASELINE_CLASS_REQUIRES_SEPARATE_CONTRACT');
  return { ready: !blockers.length, blockers: [...new Set(blockers)], safety: SAFETY };
}

// Accept already-scored rows only; does not fabricate P21 outputs or implement a new P21.
export function buildStatefulLedger(events) {
  const seen = new Set(), states = new Map(), ledger = [];
  const ordered = [...events].sort((a, b) => timestamp(a.decisionAt) - timestamp(b.decisionAt) || String(a.symbol).localeCompare(String(b.symbol)));
  for (const event of ordered) {
    const t = timestamp(event.decisionAt), date = sessionOf(event.decisionAt);
    if (event.sessionDate !== date || !/^[0-9A-Z]{4}\.T$/.test(event.symbol)) throw new Error('INVALID_EVENT_ID');
    const key = `${date}|${new Date(t).toISOString()}|${event.symbol}`;
    if (seen.has(key)) throw new Error('DUPLICATE_SELECTION_EVENT');
    seen.add(key);
    if (!['ENTER', 'ABSTAIN', 'BLOCKED'].includes(event.p21Status)) throw new Error('P21_STATUS_REQUIRED');
    if (event.p21Status === 'ENTER' && !['LONG', 'SHORT'].includes(event.direction)) throw new Error('P21_DIRECTION_REQUIRED');
    if (event.p21Status !== 'ENTER' && event.direction != null) throw new Error('NON_ENTRY_DIRECTION');
    const stateKey = `${date}|${event.symbol}`;
    const state = states.get(stateKey) ?? { firstSelectedAt: event.decisionAt, firstEligibleAt: null, previousCount: 0, signals: { LONG: 0, SHORT: 0 }, prior: null };
    const enter = event.p21Status === 'ENTER', alreadyEntered = state.firstEligibleAt !== null;
    if (enter && !alreadyEntered) state.firstEligibleAt = event.decisionAt;
    const row = { ...structuredClone(event), eventId: key, symbolSessionId: stateKey,
      firstSelectedAt: state.firstSelectedAt, firstEligibleAt: state.firstEligibleAt,
      previousSelectionCount: state.previousCount, alreadyEntered,
      firstEnterOpportunity: enter && !alreadyEntered,
      repeatedSameDirectionSignal: enter && state.signals[event.direction] > 0,
      entryDelayMinutes: enter ? (timestamp(state.firstEligibleAt) - timestamp(state.firstSelectedAt)) / 60000 : null,
      previousEventId: state.prior?.eventId ?? null,
      selectedAtNextFiveMinutes: null, nextSelectionDelayMinutes: null,
      timeBucket: timeBucket(event.decisionAt) };
    if (state.prior) {
      const delta = (t - timestamp(state.prior.decisionAt)) / 60000;
      state.prior.nextSelectionDelayMinutes = delta;
      state.prior.selectedAtNextFiveMinutes = delta === 5;
    }
    state.previousCount += 1;
    if (enter) state.signals[event.direction] += 1;
    state.prior = row; states.set(stateKey, state); ledger.push(row);
  }
  return { ledger, counts: {
    selectionEvents: ledger.length, uniqueSymbols: new Set(ledger.map(x => x.symbol)).size,
    uniqueSymbolSessions: states.size, repeatedSelections: ledger.filter(x => x.previousSelectionCount > 0).length,
    p21Eligible: ledger.filter(x => x.p21Status === 'ENTER').length,
    p21Abstain: ledger.filter(x => x.p21Status === 'ABSTAIN').length,
    p21Blocked: ledger.filter(x => x.p21Status === 'BLOCKED').length,
    firstEnterOpportunities: ledger.filter(x => x.firstEnterOpportunity).length,
    repeatedSameDirectionSignals: ledger.filter(x => x.repeatedSameDirectionSignal).length,
    long: ledger.filter(x => x.direction === 'LONG').length, short: ledger.filter(x => x.direction === 'SHORT').length,
    coverage: ledger.length ? ledger.filter(x => x.p21Status === 'ENTER').length / ledger.length : null,
  }, statePolicy: 'FIRST_ENTER_PER_SYMBOL_SESSION_NO_RESET_NO_SIMULATED_FILLS', safety: SAFETY };
}

export function freezeFeatureRecord({ decisionAt, symbol, bars, features = {} }) {
  const t = timestamp(decisionAt), date = sessionOf(decisionAt);
  const forbidden = /^(outcome|labels?|targets?|future.*|netReturn.*|actualReturn.*)$/i;
  function check(value) { for (const [key, child] of Object.entries(value ?? {})) { if (forbidden.test(key)) throw new Error('FUTURE_FIELD_IN_FEATURES'); if (child && typeof child === 'object') check(child); } }
  check(features);
  if (!bars.length) throw new Error('EMPTY_PREFIX');
  let prior = -Infinity;
  for (const bar of bars) {
    const start = timestamp(bar.timestamp);
    if (start <= prior || sessionOf(bar.timestamp) !== date || start + FIVE_MINUTES > t || timestamp(bar.availableAt) > t || timestamp(bar.availableAt) < start + FIVE_MINUTES) throw new Error('INVALID_COMPLETED_PREFIX');
    if (!['open','high','low','close','volume'].every(k => finite(bar[k])) || Math.min(bar.open, bar.low, bar.close) <= 0 || bar.volume < 0 || bar.high < Math.max(bar.open, bar.close, bar.low) || bar.low > Math.min(bar.open, bar.close)) throw new Error('INVALID_OHLCV');
    prior = start;
  }
  const core = { decisionAt, symbol, sessionDate: date, anchorPrice: bars.at(-1).close, features: structuredClone(features), prefixSha256: sha(bars) };
  return { ...core, featureSha256: sha(core) };
}

// Labels are a distinct output. Missing time-grid slots censor the horizon, never shift it.
export function buildFutureLabels(frozen, futureBars, roundTripCostBps) {
  const { featureSha256, ...core } = frozen;
  if (sha(core) !== featureSha256) throw new Error('FEATURE_FREEZE_CHANGED');
  if (!finite(roundTripCostBps) || roundTripCostBps < 0) throw new Error('EXPLICIT_COST_REQUIRED');
  const t = timestamp(frozen.decisionAt), date = frozen.sessionDate, anchor = frozen.anchorPrice;
  const byStart = new Map();
  for (const bar of futureBars) {
    const start = timestamp(bar.timestamp);
    if (start < t || sessionOf(bar.timestamp) !== date) throw new Error('INVALID_FUTURE_SESSION');
    if (byStart.has(start)) throw new Error('DUPLICATE_FUTURE_BAR');
    if (timestamp(bar.availableAt) !== start + FIVE_MINUTES || !['high','low','close'].every(k=>finite(bar[k]) && bar[k]>0) || bar.high < bar.close || bar.low > bar.close || bar.low > bar.high) throw new Error('INVALID_FUTURE_BAR');
    byStart.set(start, bar);
  }
  const result = {};
  for (const horizon of HORIZONS) {
    const path = expectedStarts(frozen.decisionAt, horizon).map(start => byStart.get(start));
    if (path.some(x => !x)) { result[horizon] = { complete: false, reason: 'MISSING_GRID_SLOT_OR_SESSION_BOUNDARY', LONG: null, SHORT: null }; continue; }
    const up = Math.max(0, ...path.map(b => (b.high / anchor - 1) * 10000));
    const down = Math.max(0, ...path.map(b => (1 - b.low / anchor) * 10000));
    const gross = (path.at(-1).close / anchor - 1) * 10000;
    const firstUp = path.findIndex(b => (b.high / anchor - 1) * 10000 === up);
    const firstDown = path.findIndex(b => (1 - b.low / anchor) * 10000 === down);
    const upTime = up === 0 ? 0 : (timestamp(path[firstUp].availableAt)-t)/60000, downTime = down === 0 ? 0 : (timestamp(path[firstDown].availableAt)-t)/60000;
    result[horizon] = { complete: true, upExcursionBps: up, downExcursionBps: down,
      LONG: { grossReturnBps: gross, netReturnBps: gross-roundTripCostBps, hit: gross>0, costAdjustedPositive: gross-roundTripCostBps>0, mfeBps: up, maeBps: down, timeToMfeMinutes: upTime, timeToMaeMinutes: downTime },
      SHORT: { grossReturnBps: -gross, netReturnBps: -gross-roundTripCostBps, hit: -gross>0, costAdjustedPositive: -gross-roundTripCostBps>0, mfeBps: down, maeBps: up, timeToMfeMinutes: downTime, timeToMaeMinutes: upTime } };
  }
  return { featureSha256, roundTripCostBps, horizons: result, timeSemantics: 'FIRST_EXTREMUM_BAR_CLOSE_NOT_TICK_TIME', executableProfit: false };
}

export function summarizeDirectional(rows, horizon) {
  const eligible = rows.filter(x => x.p21Status === 'ENTER');
  const values = eligible.flatMap(x => x.labels?.horizons?.[horizon]?.complete ? [x.labels.horizons[horizon][x.direction]] : []);
  return { eligible: eligible.length, labeled: values.length, censored: eligible.length-values.length,
    hitRate: mean(values.map(x => Number(x.hit))), costAdjustedPositiveRate: mean(values.map(x => Number(x.costAdjustedPositive))),
    meanGrossReturnBps: mean(values.map(x => x.grossReturnBps)), medianGrossReturnBps: median(values.map(x => x.grossReturnBps)),
    meanNetReturnBps: mean(values.map(x => x.netReturnBps)), medianNetReturnBps: median(values.map(x => x.netReturnBps)),
    meanMfeBps: mean(values.map(x => x.mfeBps)), meanMaeBps: mean(values.map(x => x.maeBps)),
    meanTimeToMfeMinutes: mean(values.map(x => x.timeToMfeMinutes)), meanTimeToMaeMinutes: mean(values.map(x => x.timeToMaeMinutes)),
    mfeMaeRatio: mean(values.map(x=>x.maeBps)) > 0 ? mean(values.map(x=>x.mfeBps))/mean(values.map(x=>x.maeBps)) : null };
}
