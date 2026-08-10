import assert from 'node:assert/strict';
import {
  resampleTokyoCashSession,
  resampleCompletedTokyoDaily,
  buildSessionAwareMultiTimeframePerception,
  buildHumanStyleChartReasoningPacket,
} from '../daytrade/phase57-chart-perception-session-aware.js';
import {
  classifyHumanStyleSetup,
  deriveSameSessionOutcome,
} from '../daytrade/phase57-chart-perception-measurement.js';
import { PHASE57_CHART_PERCEPTION_SAFETY } from '../daytrade/phase57-chart-perception-2.js';

function barAt(localIso, close, volume = 1000) {
  const open = close - 0.1;
  return {
    timestamp: new Date(localIso).toISOString(),
    open,
    high: close + 0.2,
    low: open - 0.2,
    close,
    volume,
  };
}

function makeSession(date, base, includeClose = true) {
  const rows = [];
  let index = 0;
  const addSegment = (hour, minute, count) => {
    for (let i = 0; i < count; i += 1) {
      const total = hour * 60 + minute + i * 5;
      const hh = String(Math.floor(total / 60)).padStart(2, '0');
      const mm = String(total % 60).padStart(2, '0');
      const close = base + index * 0.03 + Math.sin(index / 4) * 0.25;
      rows.push(barAt(`${date}T${hh}:${mm}:00+09:00`, close, 1000 + index));
      index += 1;
    }
  };
  addSegment(9, 0, 30);
  addSegment(12, 30, includeClose ? 36 : 12);
  return rows;
}

{
  const rows = [
    ...makeSession('2026-07-01', 100),
    ...makeSession('2026-07-02', 102),
  ];
  const m15 = resampleTokyoCashSession(rows, 15);
  const m60 = resampleTokyoCashSession(rows, 60);
  assert.equal(m15.length, 44); // 11 full 15m buckets per complete day.
  assert.equal(m60.length, 10); // 5 full 60m buckets per complete day.
  assert.ok(m15.every(row => row.crossesLunchBreak === false));
  assert.ok(m15.every(row => row.crossesSessionDate === false));
  assert.ok(m15.every(row => row.completedSourceBars === 3));
  assert.ok(m60.every(row => row.completedSourceBars === 12));
}

{
  const rows = [
    ...makeSession('2026-07-01', 100),
    ...makeSession('2026-07-02', 102, false),
  ];
  const daily = resampleCompletedTokyoDaily(rows);
  assert.equal(daily.length, 1);
  assert.equal(daily[0].sessionDate, '2026-07-01');
  assert.equal(daily[0].currentPartialSessionExcluded, true);
}

{
  const rows = [];
  for (let day = 1; day <= 30; day += 1) {
    const date = `2026-06-${String(day).padStart(2, '0')}`;
    rows.push(...makeSession(date, 100 + day * 0.5));
  }
  const perception = buildSessionAwareMultiTimeframePerception({ bars5m: rows });
  assert.equal(perception.status, 'SESSION_AWARE_MULTI_TIMEFRAME_PERCEPTION_READY');
  assert.equal(perception.timeframes['5m'].status, 'CHART_PERCEPTION_READY');
  assert.equal(perception.timeframes['15m'].status, 'CHART_PERCEPTION_READY');
  assert.equal(perception.timeframes['60m'].status, 'CHART_PERCEPTION_READY');
  assert.equal(perception.timeframes['1d'].status, 'CHART_PERCEPTION_READY');
  assert.equal(perception.partialHigherTimeframeBarsExcluded, true);
  assert.equal(perception.futureBarsUsed, false);
  const packet = buildHumanStyleChartReasoningPacket({ symbol: 'TEST.T', bars5m: rows });
  assert.equal(packet.schema, 'ARK_CHART_REASONING_PACKET_V2');
  assert.equal(packet.futureDataIncluded, false);
  assert.equal(packet.executableTradingInstructionAllowed, false);
}

{
  const ready = (regime, phase, breakout) => ({
    status: 'CHART_PERCEPTION_READY',
    structure: { regime },
    phase: { phase },
    breakout: { state: breakout },
  });
  const setup = classifyHumanStyleSetup({
    timeframes: {
      '5m': ready('UPTREND', 'UPTREND_PULLBACK', 'NONE'),
      '15m': ready('UPTREND', 'UPTREND_IMPULSE', 'NONE'),
      '60m': ready('RANGE_OR_TRANSITION', 'BALANCED', 'NONE'),
      '1d': ready('UPTREND', 'UPTREND_IMPULSE', 'NONE'),
    },
  });
  assert.equal(setup.setup, 'TREND_PULLBACK_UP');
  assert.equal(setup.directionSign, 1);
}

{
  const entry = barAt('2026-07-01T11:25:00+09:00', 100);
  const afterLunch = [barAt('2026-07-01T12:30:00+09:00', 101)];
  assert.equal(deriveSameSessionOutcome({ entryBar: entry, futureBars: afterLunch, directionSign: 1, horizonBars: 1 })?.hit, true);
  const nextDay = [barAt('2026-07-02T09:00:00+09:00', 101)];
  assert.equal(deriveSameSessionOutcome({ entryBar: entry, futureBars: nextDay, directionSign: 1, horizonBars: 1 }), null);
}

for (const key of [
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed',
]) assert.equal(PHASE57_CHART_PERCEPTION_SAFETY[key], false, `${key} must remain false`);

console.log('P23.10 session-aware perception/measurement tests passed');
