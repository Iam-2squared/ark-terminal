import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PHASE57_P23_2_SAFETY,
  simulateDynamicTradeManagement,
  evaluateDynamicTradeManagement,
} from '../daytrade/phase57-dynamic-trade-management.js';

const ts = index => `2026-08-10T00:${String(index * 5).padStart(2, '0')}:00.000Z`;
const bar = (index, open, high, low, close, volume = 1000) => ({ timestamp: ts(index), open, high, low, close, volume });
const context = [
  bar(0, 99.0, 99.6, 98.8, 99.4),
  bar(1, 99.4, 100.1, 99.2, 99.9),
  bar(2, 99.9, 100.5, 99.7, 100.3),
];

const baseConfig = {
  fastBars: 2,
  slowBars: 4,
  momentumBars: 2,
  swingBars: 2,
  atrBars: 4,
  hardStopAtr: 4,
  profitProtectActivationAtr: 3,
  profitProtectGivebackAtr: 1,
  minBreakdownVotes: 2,
  minBarsBeforeSoftExit: 2,
  maxHoldBars: 60,
  roundTripCostPct: 0.05,
};

test('P23.2 safety remains strictly fail-closed research only', () => {
  for (const key of [
    'executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed', 'rssOrderFunctionAllowed',
    'liveTradingAllowed', 'paperTradingAllowed', 'automaticPromotionAllowed', 'productionUpdateAllowed',
    'overnightHoldingAllowed',
  ]) assert.equal(PHASE57_P23_2_SAFETY[key], false);
  assert.equal(PHASE57_P23_2_SAFETY.humanApprovalRequired, true);
});

test('healthy rising chart is held beyond arbitrary 5/15/30 minute buckets until data/session end', () => {
  const futureBars = Array.from({ length: 10 }, (_, i) => {
    const open = 100.3 + i * 0.3;
    return bar(i + 3, open, open + 0.45, open - 0.12, open + 0.3, 1000 + i * 25);
  });
  const result = simulateDynamicTradeManagement({
    sessionDate: '2026-08-10', entryPrice: 100.3, signalDirection: 1, contextBars: context, futureBars,
  }, { ...baseConfig, profitProtectActivationAtr: 100 });
  assert.equal(result.exitReason, 'SESSION_OR_DATA_END');
  assert.equal(result.barsHeld, 10);
  assert.ok(result.decisions.filter(row => row.action === 'HOLD').length >= 10);
  assert.equal(result.timeExitIsPrimary, false);
  assert.equal(result.chartAware, true);
});

test('clear chart structure/momentum deterioration exits before max hold', () => {
  const futureBars = [
    bar(3, 100.3, 101.0, 100.2, 100.8),
    bar(4, 100.8, 101.4, 100.6, 101.2),
    bar(5, 101.2, 101.25, 99.7, 99.9, 2400),
    bar(6, 99.9, 100.0, 98.8, 99.0, 2600),
    ...Array.from({ length: 20 }, (_, i) => bar(i + 7, 99 - i * 0.1, 99.1 - i * 0.1, 98.6 - i * 0.1, 98.8 - i * 0.1)),
  ];
  const result = simulateDynamicTradeManagement({
    sessionDate: '2026-08-10', entryPrice: 100.3, signalDirection: 1, contextBars: context, futureBars,
  }, { ...baseConfig, hardStopAtr: 100, profitProtectActivationAtr: 100 });
  assert.ok(['STRUCTURE_BREAK', 'VWAP_MOMENTUM_LOSS', 'TREND_DECAY', 'CHART_BREAKDOWN'].includes(result.exitReason));
  assert.ok(result.barsHeld < futureBars.length);
  assert.notEqual(result.exitReason, 'MAX_HOLD_SAFETY_GUARD');
});

test('profit protection uses only PRIOR favorable extreme, never current-bar high/low ordering', () => {
  const futureBars = [
    bar(3, 100.3, 102.0, 100.2, 101.8),
    // If the current high 110 were illegitimately used first, a same-bar trailing stop could be created above 104.
    // Prior peak is only 102, so this bar must not trigger PRIOR_PEAK_PROFIT_PROTECTION.
    bar(4, 101.8, 110.0, 104.0, 109.0),
    bar(5, 109.0, 109.4, 108.5, 109.2),
  ];
  const result = simulateDynamicTradeManagement({
    sessionDate: '2026-08-10', entryPrice: 100.3, signalDirection: 1, contextBars: context, futureBars,
  }, {
    ...baseConfig,
    hardStopAtr: 100,
    profitProtectActivationAtr: 0.1,
    profitProtectGivebackAtr: 1,
    minBreakdownVotes: 5,
  });
  const bar4Exit = result.decisions.find(row => row.timestamp === ts(4) && row.action === 'EXIT');
  assert.equal(bar4Exit?.reason === 'PRIOR_PEAK_PROFIT_PROTECTION', false);
  assert.notEqual(result.exitReason, 'PRIOR_PEAK_PROFIT_PROTECTION');
});

test('dynamic trade management is symmetric for a deteriorating short', () => {
  const shortContext = [
    bar(0, 101.5, 101.7, 101.0, 101.1),
    bar(1, 101.1, 101.2, 100.5, 100.7),
    bar(2, 100.7, 100.8, 100.1, 100.3),
  ];
  const futureBars = [
    bar(3, 100.3, 100.4, 99.7, 99.9),
    bar(4, 99.9, 100.0, 99.2, 99.4),
    bar(5, 99.4, 101.0, 99.3, 100.8, 2400),
    bar(6, 100.8, 101.8, 100.7, 101.5, 2500),
  ];
  const result = simulateDynamicTradeManagement({ entryPrice: 100.3, signalDirection: 0, contextBars: shortContext, futureBars }, {
    ...baseConfig, hardStopAtr: 100, profitProtectActivationAtr: 100,
  });
  assert.equal(result.direction, 'SHORT');
  assert.ok(result.barsHeld < futureBars.length || result.exitReason !== 'SESSION_OR_DATA_END');
  assert.ok(['STRUCTURE_BREAK', 'VWAP_MOMENTUM_LOSS', 'TREND_DECAY', 'CHART_BREAKDOWN'].includes(result.exitReason));
});

test('bars after a causal chart exit cannot change the already-made exit decision', () => {
  const prefix = [
    bar(3, 100.3, 101.0, 100.2, 100.8),
    bar(4, 100.8, 101.2, 100.5, 101.0),
    bar(5, 101.0, 101.1, 99.4, 99.6, 2400),
    bar(6, 99.6, 99.7, 98.8, 99.0, 2600),
  ];
  const options = { ...baseConfig, hardStopAtr: 100, profitProtectActivationAtr: 100 };
  const first = simulateDynamicTradeManagement({ entryPrice: 100.3, signalDirection: 1, contextBars: context, futureBars: [...prefix, bar(7, 99, 99.2, 98, 98.2)] }, options);
  const second = simulateDynamicTradeManagement({ entryPrice: 100.3, signalDirection: 1, contextBars: context, futureBars: [...prefix, bar(7, 99, 150, 98, 149)] }, options);
  assert.equal(first.outcomeAt, second.outcomeAt);
  assert.equal(first.exitReason, second.exitReason);
  assert.equal(first.exitPrice, second.exitPrice);
  assert.equal(first.futureBarsUsedBeforeDecision, false);
});

test('max hold is a safety guard only, not the primary sell rule', () => {
  const futureBars = Array.from({ length: 8 }, (_, i) => {
    const open = 100.3 + i * 0.2;
    return bar(i + 3, open, open + 0.35, open - 0.1, open + 0.2);
  });
  const result = simulateDynamicTradeManagement({ entryPrice: 100.3, signalDirection: 1, contextBars: context, futureBars }, {
    ...baseConfig, maxHoldBars: 4, profitProtectActivationAtr: 100,
  });
  assert.equal(result.exitReason, 'MAX_HOLD_SAFETY_GUARD');
  assert.equal(result.barsHeld, 4);
  assert.equal(result.timeExitIsPrimary, false);
});

test('aggregate evaluator reports chart-aware dynamic outcomes without enabling recommendations or execution', () => {
  const futureBars = Array.from({ length: 6 }, (_, i) => {
    const open = 100.3 + i * 0.2;
    return bar(i + 3, open, open + 0.3, open - 0.1, open + 0.2);
  });
  const result = evaluateDynamicTradeManagement([
    { entryPrice: 100.3, signalDirection: 1, contextBars: context, futureBars },
  ], { ...baseConfig, profitProtectActivationAtr: 100 });
  assert.equal(result.signalCount, 1);
  assert.equal(result.fixedTimeExitPrimary, false);
  assert.equal(result.maxHoldOnlySafetyGuard, true);
  assert.equal(result.chartAware, true);
  assert.equal(result.edgeClaimAllowed, false);
  assert.equal(result.recommendationAllowed, false);
  assert.equal(result.executionAllowed, false);
  assert.equal(result.transmitted, false);
});
