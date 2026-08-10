import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PHASE57_P21_4_REAL_SAFETY,
  evaluateRealNetExpectancyOos,
} from '../daytrade/phase57-real-net-expectancy-oos.js';

function replay({ n = 150, symbols = ['7203.T', '6758.T', '9984.T', '8306.T', '8035.T'], strong = true } = {}) {
  const signals = Array.from({ length: n }, (_, index) => {
    const fold = Math.floor(index / 30);
    const label = index % 2;
    const win = strong ? index % 6 !== 0 : index % 2 === 0;
    return {
      baseOuterFold: fold,
      symbol: symbols[index % symbols.length],
      sessionDate: '2026-01-05',
      featureCutoff: new Date(Date.UTC(2026, 0, 5, 0, index * 5)).toISOString(),
      horizonBars: 12,
      probability: label ? 0.72 : 0.28,
      label,
      netReturnPct: win ? 0.30 : -0.12,
    };
  });
  const netAverageReturnPct = signals.reduce((sum, row) => sum + row.netReturnPct, 0) / signals.length;
  return {
    signals,
    signalCount: signals.length,
    hitRate: strong ? 5 / 6 : 0.5,
    netAverageReturnPct,
    commonRowCount: 1000,
    outerFoldCount: 5,
    reconciliation: null,
    selectionIntegrity: {
      horizonSelectedOnInnerOnly: true,
      featureFamilySelectedOnInnerOnly: true,
      modelFamilySelectedOnInnerOnly: true,
      thresholdSelectedOnInnerOnly: true,
      outerTestNeverUsedForSelection: true,
      outerTestNeverUsedForFit: true,
      sameSessionOnly: true,
      overnightHoldingForbidden: true,
    },
  };
}

test('P21.4 evaluates the complete prior adaptive OOS signal set without ranking symbols or candidates', () => {
  const result = evaluateRealNetExpectancyOos({ scope: 'COMBINED', replayResult: replay() });
  assert.equal(result.sourceSignalCount, 150);
  assert.equal(result.sourceCommonRowCount, 1000);
  assert.equal(result.evidence.metrics.sampleCount, 150);
  assert.equal(result.evidence.metrics.symbolStability.groupCount, 5);
  assert.equal(result.noPostOosSelection, true);
  assert.equal(result.candidateRankingAllowed, false);
  assert.equal(result.diagnosticsOnly, true);
  assert.equal(result.evidence.evidenceGatePassed, true);
});

test('small OOS signal sets fail the evidence gate even when returns are positive', () => {
  const result = evaluateRealNetExpectancyOos({ scope: '9984.T', replayResult: replay({ n: 32, symbols: ['9984.T'] }) });
  assert.equal(result.evidence.evidenceGatePassed, false);
  assert.ok(result.evidence.failureReasons.includes('INSUFFICIENT_SAMPLE'));
});

test('P21.4 refuses replay evidence that does not carry strict nested OOS integrity', () => {
  const bad = replay();
  bad.selectionIntegrity = { ...bad.selectionIntegrity, outerTestNeverUsedForSelection: false };
  assert.throws(() => evaluateRealNetExpectancyOos({ replayResult: bad }), /integrity flag/);
});

test('P21.4 refuses an explicitly failed adaptive replay reconciliation', () => {
  const bad = replay();
  bad.reconciliation = { matches: false };
  assert.throws(() => evaluateRealNetExpectancyOos({ replayResult: bad }), /unreconciled/);
});

test('P21.4 refuses normalization that changes replay Net Expectancy', () => {
  const bad = replay();
  bad.netAverageReturnPct += 0.01;
  assert.throws(() => evaluateRealNetExpectancyOos({ replayResult: bad }), /does not reconcile/);
});

test('P21.4 real OOS adapter keeps all trading, write, promotion and post-OOS selection paths disabled', () => {
  for (const key of [
    'executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed', 'rssOrderFunctionAllowed',
    'liveTradingAllowed', 'paperTradingAllowed', 'automaticPromotionAllowed', 'productionUpdateAllowed',
    'oosSelectionAllowed', 'candidateRankingAllowed',
  ]) assert.equal(PHASE57_P21_4_REAL_SAFETY[key], false);
  assert.equal(PHASE57_P21_4_REAL_SAFETY.overnightHoldingAllowed, false);
});
