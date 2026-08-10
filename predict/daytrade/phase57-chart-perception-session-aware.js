import {
  PHASE57_CHART_PERCEPTION_SAFETY,
  perceiveSingleTimeframe,
} from './phase57-chart-perception-2.js';

const JST_FORMATTER = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'Asia/Tokyo',
  year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
});

function finite(value) {
  return Number.isFinite(Number(value));
}

function normalizeBars(input = []) {
  return (Array.isArray(input) ? input : [])
    .map(bar => ({
      timestamp: new Date(bar.timestamp ?? bar.time).toISOString(),
      open: Number(bar.open),
      high: Number(bar.high),
      low: Number(bar.low),
      close: Number(bar.close),
      volume: finite(bar.volume) ? Number(bar.volume) : 0,
    }))
    .filter(bar => [bar.open, bar.high, bar.low, bar.close].every(Number.isFinite) && bar.high >= bar.low)
    .sort((a, b) => a.timestamp.localeCompare(b.timestamp));
}

function jstParts(timestamp) {
  const parts = Object.fromEntries(JST_FORMATTER.formatToParts(new Date(timestamp)).map(part => [part.type, part.value]));
  const hour = Number(parts.hour);
  const minute = Number(parts.minute);
  return {
    date: `${parts.year}-${parts.month}-${parts.day}`,
    hour,
    minute,
    minutes: hour * 60 + minute,
  };
}

function cashSegment(timestamp) {
  const p = jstParts(timestamp);
  if (p.minutes >= 9 * 60 && p.minutes < 11 * 60 + 30) {
    return { ...p, segment: 'AM', anchorMinutes: 9 * 60 };
  }
  if (p.minutes >= 12 * 60 + 30 && p.minutes < 15 * 60 + 30) {
    return { ...p, segment: 'PM', anchorMinutes: 12 * 60 + 30 };
  }
  return null;
}

function consecutiveFiveMinuteBars(chunk) {
  for (let index = 1; index < chunk.length; index += 1) {
    if (new Date(chunk[index].timestamp).getTime() - new Date(chunk[index - 1].timestamp).getTime() !== 5 * 60 * 1000) return false;
  }
  return true;
}

function aggregateChunk(chunk, metadata = {}) {
  return Object.freeze({
    timestamp: chunk.at(-1).timestamp,
    open: chunk[0].open,
    high: Math.max(...chunk.map(row => row.high)),
    low: Math.min(...chunk.map(row => row.low)),
    close: chunk.at(-1).close,
    volume: chunk.reduce((sum, row) => sum + row.volume, 0),
    completedSourceBars: chunk.length,
    sourceStart: chunk[0].timestamp,
    sourceEnd: chunk.at(-1).timestamp,
    ...metadata,
  });
}

export function resampleTokyoCashSession(input = [], timeframeMinutes = 15) {
  const bars = normalizeBars(input);
  const minutes = Number(timeframeMinutes);
  if (!Number.isInteger(minutes) || minutes < 5 || minutes % 5 !== 0) throw new Error('timeframeMinutes must be a positive multiple of 5');
  const requiredBars = minutes / 5;
  const buckets = new Map();

  for (const bar of bars) {
    const session = cashSegment(bar.timestamp);
    if (!session) continue;
    const offset = session.minutes - session.anchorMinutes;
    const bucketIndex = Math.floor(offset / minutes);
    const key = `${session.date}|${session.segment}|${bucketIndex}`;
    if (!buckets.has(key)) buckets.set(key, { session, bucketIndex, bars: [] });
    buckets.get(key).bars.push(bar);
  }

  const out = [];
  for (const { session, bucketIndex, bars: chunk } of buckets.values()) {
    chunk.sort((a, b) => a.timestamp.localeCompare(b.timestamp));
    if (chunk.length !== requiredBars || !consecutiveFiveMinuteBars(chunk)) continue;
    out.push(aggregateChunk(chunk, {
      sessionDate: session.date,
      sessionSegment: session.segment,
      timeframeMinutes: minutes,
      bucketIndex,
      fullyCompletedBucket: true,
      crossesLunchBreak: false,
      crossesSessionDate: false,
    }));
  }
  return Object.freeze(out.sort((a, b) => a.timestamp.localeCompare(b.timestamp)));
}

export function resampleCompletedTokyoDaily(input = []) {
  const bars = normalizeBars(input);
  const groups = new Map();
  for (const bar of bars) {
    const session = cashSegment(bar.timestamp);
    if (!session) continue;
    if (!groups.has(session.date)) groups.set(session.date, []);
    groups.get(session.date).push(bar);
  }

  // Point-in-time rule: the latest session in the prefix is still developing.
  // Drop it unconditionally rather than guessing completeness from a vendor's
  // bar timestamp convention. Earlier dates are fully in the past at cutoff.
  const dates = [...groups.keys()].sort();
  const activeSessionDate = dates.at(-1) ?? null;
  const out = [];
  for (const [sessionDate, chunk] of groups) {
    if (sessionDate === activeSessionDate) continue;
    chunk.sort((a, b) => a.timestamp.localeCompare(b.timestamp));
    if (!chunk.length) continue;
    out.push(aggregateChunk(chunk, {
      sessionDate,
      timeframeMinutes: 24 * 60,
      fullyCompletedBucket: true,
      currentPartialSessionExcluded: true,
      vendorTimestampConventionIndependent: true,
    }));
  }
  return Object.freeze(out.sort((a, b) => a.timestamp.localeCompare(b.timestamp)));
}

function alignment(perceptions) {
  const usable = perceptions.filter(row => row?.status === 'CHART_PERCEPTION_READY');
  const votes = usable.map(row => row.structure.regime === 'UPTREND' ? 1 : row.structure.regime === 'DOWNTREND' ? -1 : 0);
  const total = votes.reduce((sum, value) => sum + value, 0);
  const nonZero = votes.filter(Boolean);
  return Object.freeze({
    direction: total > 0 ? 'UP' : total < 0 ? 'DOWN' : 'MIXED',
    score: usable.length ? Math.abs(total) / usable.length : 0,
    directionalConflict: new Set(nonZero.map(value => Math.sign(value))).size > 1,
    usableTimeframes: usable.length,
  });
}

export function buildSessionAwareMultiTimeframePerception({ bars5m = [] } = {}) {
  const clean = normalizeBars(bars5m);
  const bars15m = resampleTokyoCashSession(clean, 15);
  const bars60m = resampleTokyoCashSession(clean, 60);
  const bars1d = resampleCompletedTokyoDaily(clean);

  const tf5 = perceiveSingleTimeframe({ bars: clean, timeframe: '5m' });
  const tf15 = perceiveSingleTimeframe({ bars: bars15m, timeframe: '15m' });
  const tf60 = perceiveSingleTimeframe({ bars: bars60m, timeframe: '60m' });
  const tf1d = perceiveSingleTimeframe({ bars: bars1d, timeframe: '1d' });
  const timeframes = Object.freeze({ '5m': tf5, '15m': tf15, '60m': tf60, '1d': tf1d });

  return Object.freeze({
    phase: '57.p23.10a',
    status: 'SESSION_AWARE_MULTI_TIMEFRAME_PERCEPTION_READY',
    architecture: 'PERCEPTION_THEN_UNDERSTANDING_THEN_EVIDENCE',
    timeframes,
    alignment: alignment([tf5, tf15, tf60, tf1d]),
    sourceCounts: Object.freeze({
      bars5m: clean.length,
      bars15m: bars15m.length,
      bars60m: bars60m.length,
      bars1d: bars1d.length,
    }),
    causalCutoff: clean.at(-1)?.timestamp ?? null,
    sessionAwareAggregation: true,
    lunchBreakCrossingForbidden: true,
    sessionDateCrossingForbidden: true,
    partialHigherTimeframeBarsExcluded: true,
    completedBarsOnly: true,
    futureBarsUsed: false,
    outcomeUsed: false,
    recommendationAllowed: false,
    transmitted: false,
    ...PHASE57_CHART_PERCEPTION_SAFETY,
    safety: PHASE57_CHART_PERCEPTION_SAFETY,
  });
}

export function buildHumanStyleChartReasoningPacket({ symbol, bars5m = [] } = {}) {
  const perception = buildSessionAwareMultiTimeframePerception({ bars5m });
  const compact = Object.fromEntries(Object.entries(perception.timeframes).map(([timeframe, row]) => [timeframe, {
    status: row.status,
    structure: row.structure ?? null,
    phase: row.phase ?? null,
    breakout: row.breakout ?? null,
    trendQuality: row.trendQuality ?? null,
    volatility: row.volatility ?? null,
    volume: row.volume ?? null,
    scenario: row.scenario ?? null,
    narrative: row.narrative ?? null,
    dataCutoff: row.dataCutoff ?? null,
  }]));

  return Object.freeze({
    schema: 'ARK_CHART_REASONING_PACKET_V2',
    symbol: String(symbol ?? ''),
    purpose: 'HUMAN_STYLE_CHART_PERCEPTION_RESEARCH',
    perception: compact,
    alignment: perception.alignment,
    causalCutoff: perception.causalCutoff,
    reasoningOrder: Object.freeze([
      'READ_HIGHER_TIMEFRAME_CONTEXT',
      'READ_SWING_STRUCTURE',
      'LOCATE_IMPULSE_OR_PULLBACK',
      'READ_BREAKOUT_RETEST_OR_FAILURE',
      'CHECK_VOLUME_AND_VOLATILITY_CONFIRMATION',
      'STATE_PRIMARY_AND_ALTERNATIVE_SCENARIOS',
      'STATE_STRUCTURAL_INVALIDATION',
      'ONLY_THEN_COMPARE_HISTORICAL_EVIDENCE',
    ]),
    instructionsForReasoner: Object.freeze([
      'Describe what the chart is doing before estimating any future distribution.',
      'Use 1d and 60m as context; use 15m and 5m for local structure.',
      'Treat RSI/MACD-like indicators only as secondary evidence if supplied elsewhere.',
      'Distinguish trend pullback, impulse, breakout, retest, failed breakout and range transition.',
      'State what evidence would invalidate the primary scenario.',
      'Do not use data after causalCutoff.',
      'Do not output an executable order or personalized recommendation.',
    ]),
    futureDataIncluded: false,
    executableTradingInstructionAllowed: false,
    recommendationAllowed: false,
    transmitted: false,
    ...PHASE57_CHART_PERCEPTION_SAFETY,
  });
}

export default {
  resampleTokyoCashSession,
  resampleCompletedTokyoDaily,
  buildSessionAwareMultiTimeframePerception,
  buildHumanStyleChartReasoningPacket,
};
