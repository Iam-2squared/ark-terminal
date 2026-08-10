import {
  PHASE57_CHART_PERCEPTION_SAFETY,
} from './phase57-chart-perception-2.js';
import {
  buildSessionAwareMultiTimeframePerception,
} from './phase57-chart-perception-session-aware.js';

const JST_DATE = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit',
});

function finite(value) {
  return Number.isFinite(Number(value));
}

function normalizeBars(input = []) {
  return (Array.isArray(input) ? input : [])
    .map(bar => ({
      timestamp: new Date(bar.timestamp ?? bar.time).toISOString(),
      open: Number(bar.open), high: Number(bar.high), low: Number(bar.low), close: Number(bar.close),
      volume: finite(bar.volume) ? Number(bar.volume) : 0,
    }))
    .filter(bar => [bar.open, bar.high, bar.low, bar.close].every(Number.isFinite) && bar.high >= bar.low)
    .sort((a, b) => a.timestamp.localeCompare(b.timestamp));
}

function jstDate(timestamp) {
  return JST_DATE.format(new Date(timestamp));
}

function regimeSign(regime) {
  if (regime === 'UPTREND') return 1;
  if (regime === 'DOWNTREND') return -1;
  return 0;
}

function ready(row) {
  return row?.status === 'CHART_PERCEPTION_READY';
}

export function classifyHumanStyleSetup(perception = {}) {
  const tf5 = perception.timeframes?.['5m'];
  const tf15 = perception.timeframes?.['15m'];
  const tf60 = perception.timeframes?.['60m'];
  const tf1d = perception.timeframes?.['1d'];
  if (![tf5, tf15, tf60, tf1d].every(ready)) {
    return Object.freeze({ setup: 'OBSERVE_INCOMPLETE_CONTEXT', directionSign: 0, evidence: [] });
  }

  const r15 = regimeSign(tf15.structure.regime);
  const r60 = regimeSign(tf60.structure.regime);
  const r1d = regimeSign(tf1d.structure.regime);
  const higherUpHostile = r60 < 0 && r1d < 0;
  const higherDownHostile = r60 > 0 && r1d > 0;
  const evidence = [];

  if (tf5.breakout.state === 'RETEST_HOLD_UP' && !higherUpHostile) {
    evidence.push('5M_RETEST_HOLD_UP', `15M_${tf15.structure.regime}`, `60M_${tf60.structure.regime}`, `1D_${tf1d.structure.regime}`);
    return Object.freeze({ setup: 'RETEST_CONTINUATION_UP', directionSign: 1, evidence });
  }
  if (tf5.breakout.state === 'RETEST_HOLD_DOWN' && !higherDownHostile) {
    evidence.push('5M_RETEST_HOLD_DOWN', `15M_${tf15.structure.regime}`, `60M_${tf60.structure.regime}`, `1D_${tf1d.structure.regime}`);
    return Object.freeze({ setup: 'RETEST_CONTINUATION_DOWN', directionSign: -1, evidence });
  }
  if (tf5.breakout.state === 'FAILED_BREAKOUT_UP') {
    evidence.push('5M_FAILED_BREAKOUT_UP', `15M_${tf15.structure.regime}`);
    return Object.freeze({ setup: 'FAILED_BREAKOUT_REVERSAL_DOWN', directionSign: -1, evidence });
  }
  if (tf5.breakout.state === 'FAILED_BREAKOUT_DOWN') {
    evidence.push('5M_FAILED_BREAKOUT_DOWN', `15M_${tf15.structure.regime}`);
    return Object.freeze({ setup: 'FAILED_BREAKOUT_REVERSAL_UP', directionSign: 1, evidence });
  }

  const pullbackUp = tf5.phase.phase === 'UPTREND_PULLBACK'
    && r15 >= 0 && r60 >= 0 && !higherUpHostile;
  if (pullbackUp) {
    evidence.push('5M_UPTREND_PULLBACK', `15M_${tf15.structure.regime}`, `60M_${tf60.structure.regime}`, `1D_${tf1d.structure.regime}`);
    return Object.freeze({ setup: 'TREND_PULLBACK_UP', directionSign: 1, evidence });
  }
  const pullbackDown = tf5.phase.phase === 'DOWNTREND_PULLBACK'
    && r15 <= 0 && r60 <= 0 && !higherDownHostile;
  if (pullbackDown) {
    evidence.push('5M_DOWNTREND_PULLBACK', `15M_${tf15.structure.regime}`, `60M_${tf60.structure.regime}`, `1D_${tf1d.structure.regime}`);
    return Object.freeze({ setup: 'TREND_PULLBACK_DOWN', directionSign: -1, evidence });
  }

  const breakoutUp = tf5.breakout.state === 'BREAKOUT_UP' && r15 >= 0 && !higherUpHostile;
  if (breakoutUp) {
    evidence.push('5M_BREAKOUT_UP', `15M_${tf15.structure.regime}`, `60M_${tf60.structure.regime}`);
    return Object.freeze({ setup: 'BREAKOUT_CONTINUATION_UP', directionSign: 1, evidence });
  }
  const breakoutDown = tf5.breakout.state === 'BREAKOUT_DOWN' && r15 <= 0 && !higherDownHostile;
  if (breakoutDown) {
    evidence.push('5M_BREAKOUT_DOWN', `15M_${tf15.structure.regime}`, `60M_${tf60.structure.regime}`);
    return Object.freeze({ setup: 'BREAKOUT_CONTINUATION_DOWN', directionSign: -1, evidence });
  }

  const impulseUp = tf5.phase.phase === 'UPTREND_IMPULSE' && r15 > 0 && r60 >= 0 && !higherUpHostile;
  if (impulseUp) {
    evidence.push('5M_UPTREND_IMPULSE', '15M_UPTREND', `60M_${tf60.structure.regime}`);
    return Object.freeze({ setup: 'MOMENTUM_CONTINUATION_UP', directionSign: 1, evidence });
  }
  const impulseDown = tf5.phase.phase === 'DOWNTREND_IMPULSE' && r15 < 0 && r60 <= 0 && !higherDownHostile;
  if (impulseDown) {
    evidence.push('5M_DOWNTREND_IMPULSE', '15M_DOWNTREND', `60M_${tf60.structure.regime}`);
    return Object.freeze({ setup: 'MOMENTUM_CONTINUATION_DOWN', directionSign: -1, evidence });
  }

  return Object.freeze({ setup: 'NO_CLEAR_SETUP', directionSign: 0, evidence: Object.freeze([
    `5M_${tf5.structure.regime}`,
    `15M_${tf15.structure.regime}`,
    `60M_${tf60.structure.regime}`,
    `1D_${tf1d.structure.regime}`,
  ]) });
}

export function deriveSameSessionOutcome({ entryBar, futureBars = [], directionSign, horizonBars } = {}) {
  const sign = Number(directionSign);
  if (![1, -1].includes(sign)) return null;
  const entry = Number(entryBar?.close);
  if (!finite(entry) || entry <= 0) return null;
  const horizon = Number(horizonBars);
  const future = normalizeBars(futureBars).slice(0, horizon);
  if (future.length !== horizon) return null;
  const date = jstDate(entryBar.timestamp);
  if (future.some(bar => jstDate(bar.timestamp) !== date)) return null;

  const endpoint = future.at(-1).close;
  const directionalReturnPct = (endpoint / entry - 1) * 100 * sign;
  const favorablePrice = sign === 1
    ? Math.max(entry, ...future.map(bar => bar.high))
    : Math.min(entry, ...future.map(bar => bar.low));
  const adversePrice = sign === 1
    ? Math.min(entry, ...future.map(bar => bar.low))
    : Math.max(entry, ...future.map(bar => bar.high));
  const mfePct = Math.max(0, (favorablePrice / entry - 1) * 100 * sign);
  const maePct = Math.min(0, (adversePrice / entry - 1) * 100 * sign);
  return Object.freeze({
    horizonBars: horizon,
    horizonMinutes: horizon * 5,
    directionalReturnPct,
    hit: directionalReturnPct > 0,
    mfePct,
    maePct,
    outcomeAt: future.at(-1).timestamp,
    evaluationOnly: true,
    usedByPerception: false,
  });
}

function mean(values) {
  return values.length ? values.reduce((sum, value) => sum + Number(value), 0) / values.length : null;
}

function summarize(rows, horizonKey) {
  const valid = rows.filter(row => row[horizonKey]);
  return Object.freeze({
    count: valid.length,
    hitRate: valid.length ? valid.filter(row => row[horizonKey].hit).length / valid.length : null,
    averageDirectionalReturnPct: valid.length ? mean(valid.map(row => row[horizonKey].directionalReturnPct)) : null,
    averageMfePct: valid.length ? mean(valid.map(row => row[horizonKey].mfePct)) : null,
    averageMaePct: valid.length ? mean(valid.map(row => row[horizonKey].maePct)) : null,
  });
}

function groupSummary(records) {
  const groups = {};
  for (const row of records) {
    if (!groups[row.setup]) groups[row.setup] = [];
    groups[row.setup].push(row);
  }
  return Object.freeze(Object.fromEntries(Object.entries(groups).map(([setup, rows]) => [setup, Object.freeze({
    signalCount: rows.length,
    outcome30m: summarize(rows, 'outcome30m'),
    outcome60m: summarize(rows, 'outcome60m'),
  })])));
}

export function measureChartPerceptionHistory({
  symbol,
  bars5m = [],
  minHistoryBars = 1600,
  stepBars = 3,
  maxContextBars = 2600,
} = {}) {
  const bars = normalizeBars(bars5m);
  const records = [];
  const observationCounts = { incompleteContext: 0, noClearSetup: 0, directionalSetup: 0, crossSessionOutcomeExcluded: 0 };

  for (let index = Math.max(24, Number(minHistoryBars)); index < bars.length - 12; index += Math.max(1, Number(stepBars))) {
    const start = Math.max(0, index + 1 - Number(maxContextBars));
    const contextBars = bars.slice(start, index + 1);
    const perception = buildSessionAwareMultiTimeframePerception({ bars5m: contextBars });
    const setup = classifyHumanStyleSetup(perception);
    if (setup.setup === 'OBSERVE_INCOMPLETE_CONTEXT') {
      observationCounts.incompleteContext += 1;
      continue;
    }
    if (!setup.directionSign) {
      observationCounts.noClearSetup += 1;
      continue;
    }

    const future = bars.slice(index + 1, index + 13);
    const outcome30m = deriveSameSessionOutcome({ entryBar: bars[index], futureBars: future, directionSign: setup.directionSign, horizonBars: 6 });
    const outcome60m = deriveSameSessionOutcome({ entryBar: bars[index], futureBars: future, directionSign: setup.directionSign, horizonBars: 12 });
    if (!outcome30m && !outcome60m) {
      observationCounts.crossSessionOutcomeExcluded += 1;
      continue;
    }
    observationCounts.directionalSetup += 1;
    records.push(Object.freeze({
      symbol: String(symbol ?? ''),
      sessionDate: jstDate(bars[index].timestamp),
      featureCutoff: bars[index].timestamp,
      entryPrice: bars[index].close,
      setup: setup.setup,
      direction: setup.directionSign === 1 ? 'UP' : 'DOWN',
      evidence: setup.evidence,
      alignment: perception.alignment,
      narratives: Object.freeze(Object.fromEntries(Object.entries(perception.timeframes).map(([tf, row]) => [tf, row.narrative ?? null]))),
      outcome30m,
      outcome60m,
      perceptionUsedFutureBars: false,
      outcomeUsedByPerception: false,
    }));
  }

  const directional = records.length;
  const evaluatedCutoffs = observationCounts.incompleteContext + observationCounts.noClearSetup + observationCounts.directionalSetup + observationCounts.crossSessionOutcomeExcluded;
  return Object.freeze({
    phase: '57.p23.10b-chart-state-measurement',
    status: 'CAUSAL_HISTORICAL_CHART_STATE_MEASURED',
    symbol: String(symbol ?? ''),
    sourceBarCount: bars.length,
    evaluatedCutoffs,
    directionalSetupCount: directional,
    directionalSetupCoverage: evaluatedCutoffs ? directional / evaluatedCutoffs : 0,
    observationCounts: Object.freeze(observationCounts),
    aggregate: Object.freeze({
      outcome30m: summarize(records, 'outcome30m'),
      outcome60m: summarize(records, 'outcome60m'),
    }),
    bySetup: groupSummary(records),
    records: Object.freeze(records),
    integrity: Object.freeze({
      perceptionBuiltFromPrefixOnly: true,
      higherTimeframesUseCompletedBucketsOnly: true,
      lunchBreakCrossingForbidden: true,
      sessionDateCrossingForbidden: true,
      futureOutcomesEvaluationOnly: true,
      futureOutcomeUsedForSetupClassification: false,
      fixedRulesNotOutcomeTuned: true,
      p23_8FrozenOutcomesUsedForRuleSelection: false,
      finalUntouchedOosEdgeClaimAllowed: false,
    }),
    edgeClaimAllowed: false,
    recommendationAllowed: false,
    transmitted: false,
    ...PHASE57_CHART_PERCEPTION_SAFETY,
    safety: PHASE57_CHART_PERCEPTION_SAFETY,
  });
}

export default {
  classifyHumanStyleSetup,
  deriveSameSessionOutcome,
  measureChartPerceptionHistory,
};
