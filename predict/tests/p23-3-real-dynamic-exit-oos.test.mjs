import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PHASE57_P23_3_SAFETY,
  P23_3_FROZEN_DYNAMIC_CONFIG,
  evaluateRealDynamicExitOos,
} from '../daytrade/phase57-real-dynamic-exit-oos.js';

const BASE_TS = Date.parse('2026-08-10T00:00:00.000Z');
const ts = index => new Date(BASE_TS + index * 5 * 60 * 1000).toISOString();
const bar = (index, open, high, low, close, volume = 1000) => ({ timestamp: ts(index), open, high, low, close, volume });

const context = [
  bar(0, 99.0, 99.6, 98.8, 99.4),
  bar(1, 99.4, 100.1, 99.2, 99.9),
  bar(2, 99.9, 100.5, 99.7, 100.3),
];

function researchRow(overrides = {}) {
  return {
    id: 'row-1',
    symbol: '7203.T',
    sessionDate: '2026-08-10',
    featureCutoff: ts(2),
    entryPrice: 100.3,
    signalDirection: 1,
    baseHorizonBars: 3,
    baseOuterFold: 2,
    signalPointInTimeValid: true,
    pointInTimeValid: true,
    contextBars: context,
    futureBars: [
      bar(3, 100.3, 100.8, 100.2, 100.7),
      bar(4, 100.7, 101.2, 100.6, 101.1),
      bar(5, 101.1, 101.6, 101.0, 101.5),
      bar(6, 101.5, 102.0, 101.4, 101.9),
      bar(7, 101.9, 102.4, 101.8, 102.3),
      bar(8, 102.3, 102.8, 102.2, 102.7),
    ],
    ...overrides,
  };
}

test('P23.3 safety stays strictly fail-closed', () => {
  for (const key of [
    'executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed', 'rssOrderFunctionAllowed',
    'liveTradingAllowed', 'paperTradingAllowed', 'automaticPromotionAllowed', 'productionUpdateAllowed',
    'overnightHoldingAllowed',
  ]) assert.equal(PHASE57_P23_3_SAFETY[key], false);
  assert.equal(PHASE57_P23_3_SAFETY.humanApprovalRequired, true);
  assert.equal(P23_3_FROZEN_DYNAMIC_CONFIG.maxHoldBars, 1000);
});

test('healthy chart can stay open beyond the matched fixed horizon', () => {
  const result = evaluateRealDynamicExitOos([researchRow()], {
    dynamicConfig: { profitProtectActivationAtr: 100 },
  });
  assert.equal(result.pairedSignalCount, 1);
  assert.equal(result.dynamic.signalCount, 1);
  assert.equal(result.matchedFixedBaseline.signalCount, 1);
  assert.equal(result.dynamic.averageHoldingBars, 6);
  assert.equal(result.matchedFixedBaseline.averageHoldingBars, 3);
  assert.ok(result.deltaAverageHoldingBars > 0);
  assert.equal(result.selectionIntegrity.sessionPathEndsHealthyTrendInsteadOfElapsedTime, true);
  assert.equal(result.interpretation.fixedElapsedTimeIsBaselineOnly, true);
});

test('clear deterioration exits dynamically before a long fixed-horizon baseline', () => {
  const futureBars = [
    bar(3, 100.3, 101.0, 100.2, 100.8),
    bar(4, 100.8, 101.3, 100.7, 101.1),
    bar(5, 101.1, 101.15, 99.7, 99.9, 2200),
    bar(6, 99.9, 100.0, 98.9, 99.1, 2500),
    bar(7, 99.1, 99.2, 98.0, 98.2, 2600),
    bar(8, 98.2, 98.3, 97.2, 97.4, 2600),
    bar(9, 97.4, 97.5, 96.5, 96.8, 2600),
    bar(10, 96.8, 97.0, 96.0, 96.2, 2600),
    bar(11, 96.2, 96.4, 95.5, 95.8, 2600),
    bar(12, 95.8, 96.0, 95.0, 95.2, 2600),
    bar(13, 95.2, 95.3, 94.6, 94.8, 2600),
    bar(14, 94.8, 95.0, 94.0, 94.2, 2600),
  ];
  const result = evaluateRealDynamicExitOos([researchRow({ baseHorizonBars: 12, futureBars })], {
    dynamicConfig: { hardStopAtr: 100, profitProtectActivationAtr: 100 },
  });
  assert.equal(result.pairedSignalCount, 1);
  assert.ok(result.dynamic.averageHoldingBars < result.matchedFixedBaseline.averageHoldingBars);
  assert.ok(result.deltaMatchedNetAverageReturnPct > 0);
});

test('outer OOS can never be used to tune dynamic exit configuration', () => {
  assert.throws(() => evaluateRealDynamicExitOos([researchRow()], {
    allowOuterOosConfigSelection: true,
  }), /forbids outer-OOS exit configuration selection/);
});

test('cross-session paths are rejected instead of creating overnight holding', () => {
  const nextDay = { ...bar(3, 100.3, 101, 100, 100.8), timestamp: '2026-08-11T00:00:00.000Z' };
  const result = evaluateRealDynamicExitOos([researchRow({ futureBars: [nextDay] })]);
  assert.equal(result.validResearchRowCount, 0);
  assert.equal(result.pairedSignalCount, 0);
  assert.equal(result.overnightHoldingAllowed, false);
});

test('bars after a causal dynamic exit cannot alter the earlier decision', () => {
  const prefix = [
    bar(3, 100.3, 101.0, 100.2, 100.8),
    bar(4, 100.8, 101.2, 100.5, 101.0),
    bar(5, 101.0, 101.1, 99.4, 99.6, 2400),
    bar(6, 99.6, 99.7, 98.8, 99.0, 2600),
  ];
  const options = { dynamicConfig: { hardStopAtr: 100, profitProtectActivationAtr: 100 } };
  const first = evaluateRealDynamicExitOos([researchRow({ baseHorizonBars: 12, futureBars: [...prefix, bar(7, 99, 99.2, 98, 98.2)] })], options);
  const second = evaluateRealDynamicExitOos([researchRow({ baseHorizonBars: 12, futureBars: [...prefix, bar(7, 99, 150, 98, 149)] })], options);
  assert.equal(first.foldResults[0].dynamic.averageHoldingBars, second.foldResults[0].dynamic.averageHoldingBars);
  assert.equal(first.dynamic.netAverageReturnPct, second.dynamic.netAverageReturnPct);
});

test('full-path MFE is evaluation-only and reports post-exit opportunity without changing the exit', () => {
  const futureBars = [
    bar(3, 100.3, 101.0, 100.2, 100.8),
    bar(4, 100.8, 101.1, 99.5, 99.7, 2200),
    bar(5, 99.7, 105.0, 99.6, 104.5, 2200),
  ];
  const result = evaluateRealDynamicExitOos([researchRow({ baseHorizonBars: 3, futureBars })], {
    dynamicConfig: { hardStopAtr: 100, profitProtectActivationAtr: 100 },
  });
  assert.equal(result.selectionIntegrity.fullPathMfeUsedForEvaluationOnly, true);
  assert.equal(result.selectionIntegrity.outerOosUsedForDynamicExitConfigSelection, false);
  assert.equal(result.edgeClaimAllowed, false);
  assert.equal(result.recommendationAllowed, false);
});

test('fold diagnostics compare dynamic and fixed exits on exactly matched prior-OOS signal rows', () => {
  const rows = [
    researchRow({ id: 'a', baseOuterFold: 1 }),
    researchRow({ id: 'b', symbol: '6758.T', baseOuterFold: 2 }),
  ];
  const result = evaluateRealDynamicExitOos(rows, { dynamicConfig: { profitProtectActivationAtr: 100 } });
  assert.equal(result.pairedSignalCount, 2);
  assert.equal(result.foldResults.length, 2);
  assert.equal(result.selectionIntegrity.entrySignalsArePriorOuterOos, true);
  assert.equal(result.selectionIntegrity.matchedBaselineUsesExactSameSignalRows, true);
  assert.equal(result.selectionIntegrity.postSelectionAcrossExitVariantsAllowed, false);
  assert.equal(result.executionAllowed, false);
  assert.equal(result.paperTradingAllowed, false);
});
