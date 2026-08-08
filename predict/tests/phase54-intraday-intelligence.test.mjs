import test from 'node:test';
import assert from 'node:assert/strict';
import {
  analyzeIntradaySessionStructure,
  analyzePhase54IntradayIntelligence,
  PHASE54_SAFETY,
} from '../trading/phase54-intraday-intelligence.js';

const START = 1_785_000_000;

function buildTimeframe(minutes, direction = 'bull') {
  const rows = [];
  let index = 0;
  const push = (sessionDate, count, current = false) => {
    for (let slot = 0; slot < count; slot += 1) {
      const base = current ? 101 + slot * 0.03 : 100 + slot * 0.01;
      rows.push({
        time: START + index * minutes * 60,
        open: base - 0.05,
        high: base + 0.2,
        low: base - 0.2,
        close: base,
        volume: 100,
        sessionDate,
        isClosed: true,
      });
      index += 1;
    }
  };

  push('2026-08-06', 40, false);
  push('2026-08-07', 8, true);
  const latest = rows.at(-1);
  if (direction === 'bull') {
    latest.open = 102.5;
    latest.low = 102.4;
    latest.high = 106;
    latest.close = 105.5;
  } else {
    latest.open = 98;
    latest.high = 98.1;
    latest.low = 95;
    latest.close = 95.5;
  }
  latest.volume = 500;
  return rows;
}

test('Phase54 extracts gap, opening range and VWAP session structure', () => {
  const rows = buildTimeframe(15, 'bull');
  const result = analyzeIntradaySessionStructure(rows, { openingRangeBars: 2 });
  assert.equal(result.ready, true);
  assert.equal(result.sessionDate, '2026-08-07');
  assert.equal(result.openingRangeBars, 2);
  assert.ok(Number.isFinite(result.gapPercent));
  assert.ok(Number.isFinite(result.vwap));
  assert.equal(result.openingRangeBreakout, 'up');
  assert.equal(result.aboveVwap, true);
});

test('Phase54 combines 5m, 15m and 60m intelligence without enabling execution', () => {
  const candlesByTimeframe = {
    5: buildTimeframe(5, 'bull'),
    15: buildTimeframe(15, 'bull'),
    60: buildTimeframe(60, 'bull'),
  };
  const latest60 = candlesByTimeframe[60].at(-1);
  const result = analyzePhase54IntradayIntelligence(candlesByTimeframe, {
    nowSeconds: latest60.time + 60 * 60 + 60,
    policy: {
      marketPolicy: {
        5: { maximumBarAgeSeconds: 5 * 60 * 60 },
        15: { maximumBarAgeSeconds: 5 * 60 * 60 },
        60: { maximumBarAgeSeconds: 5 * 60 * 60 },
      },
    },
  });

  assert.equal(result.phase, '54');
  assert.equal(result.status, 'INTRADAY_INTELLIGENCE_READY');
  assert.deepEqual(result.usableTimeframes, [5, 15, 60]);
  assert.equal(result.bias, '強気');
  assert.equal(result.executionAllowed, false);
  assert.equal(result.liveTradingAllowed, false);
  assert.equal(result.transmitted, false);
  assert.ok(result.featureSet.includes('opening_range'));
  assert.ok(result.featureSet.includes('overnight_gap'));
});

test('Phase54 exposes conflict instead of pretending multi-timeframe agreement', () => {
  const candlesByTimeframe = {
    5: buildTimeframe(5, 'bull'),
    15: buildTimeframe(15, 'bear'),
    60: buildTimeframe(60, 'bull'),
  };
  const latest60 = candlesByTimeframe[60].at(-1);
  const result = analyzePhase54IntradayIntelligence(candlesByTimeframe, {
    nowSeconds: latest60.time + 60 * 60 + 60,
    policy: {
      marketPolicy: {
        5: { maximumBarAgeSeconds: 5 * 60 * 60 },
        15: { maximumBarAgeSeconds: 5 * 60 * 60 },
        60: { maximumBarAgeSeconds: 5 * 60 * 60 },
      },
    },
  });
  assert.ok(result.blockers.includes('TIMEFRAME_CONFLICT'));
  assert.equal(result.automaticPromotionAllowed, false);
});

test('Phase54 safety boundary remains read-only', () => {
  assert.deepEqual(PHASE54_SAFETY, {
    mode: 'INTRADAY_INTELLIGENCE_READ_ONLY',
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    automaticPromotionAllowed: false,
    humanApprovalRequired: true,
  });
});
