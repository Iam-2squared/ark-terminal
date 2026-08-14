import assert from 'node:assert/strict';
import { EXPANDED_UNIVERSE } from '../daytrade/phase57-expanded-universe.js';
import { CHART_QUALITY_HOLDOUT_UNIVERSE } from '../daytrade/phase57-chart-quality-holdout-universe.js';
import { CHART_ECONOMIC_HOLDOUT_UNIVERSE, CHART_ECONOMIC_HOLDOUT_POLICY } from '../daytrade/phase57-chart-economic-holdout-universe.js';
import {
  P23_10F_ECONOMIC_POLICY,
  PHASE57_P23_10F_SAFETY,
  frozenQualityBand,
  isFrozenQ4Candidate,
  summarizeEconomicTrades,
  maxSequentialDrawdownPctPoints,
} from '../daytrade/phase57-chart-economic-validation.js';

assert.equal(CHART_ECONOMIC_HOLDOUT_UNIVERSE.length,30);
assert.equal(new Set(CHART_ECONOMIC_HOLDOUT_UNIVERSE).size,30);
const prior=new Set([...EXPANDED_UNIVERSE,...CHART_QUALITY_HOLDOUT_UNIVERSE]);
assert.deepEqual(CHART_ECONOMIC_HOLDOUT_UNIVERSE.filter(symbol=>prior.has(symbol)),[]);
assert.equal(CHART_ECONOMIC_HOLDOUT_POLICY.frozenBeforeOutcomeMeasurement,true);
assert.equal(CHART_ECONOMIC_HOLDOUT_POLICY.qualityScoreRetuningAllowed,false);
assert.equal(CHART_ECONOMIC_HOLDOUT_POLICY.exitRetuningAllowed,false);

assert.equal(P23_10F_ECONOMIC_POLICY.q4MinScore,0.70);
assert.equal(P23_10F_ECONOMIC_POLICY.entryAtNextFiveMinuteBarOpen,true);
assert.equal(P23_10F_ECONOMIC_POLICY.oneActiveTradePerSymbol,true);
assert.equal(P23_10F_ECONOMIC_POLICY.setupRuleRetuningAllowed,false);
assert.equal(P23_10F_ECONOMIC_POLICY.qualityRuleRetuningAllowed,false);
assert.equal(P23_10F_ECONOMIC_POLICY.exitRetuningAllowed,false);
assert.equal(P23_10F_ECONOMIC_POLICY.exitConfigId,'STATE_MONOTONIC_RATCHET_V1');
assert.equal(frozenQualityBand(0.399),'Q1_LOW');
assert.equal(frozenQualityBand(0.40),'Q2');
assert.equal(frozenQualityBand(0.55),'Q3');
assert.equal(frozenQualityBand(0.70),'Q4_HIGH');
assert.equal(isFrozenQ4Candidate(0.6999),false);
assert.equal(isFrozenQ4Candidate(0.70),true);

for (const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed','transmitted']) {
  assert.equal(PHASE57_P23_10F_SAFETY[key],false,`${key} must remain false`);
}

const trades=[
  {symbol:'A',entryTimestamp:'2026-01-01T00:00:00Z',netReturnPct:0.20,grossReturnPct:0.25,mfePct:0.30,maePct:-0.10,profitGivebackPctPoints:0.05,captureRatio:0.8,barsHeld:4},
  {symbol:'B',entryTimestamp:'2026-01-01T01:00:00Z',netReturnPct:-0.10,grossReturnPct:-0.05,mfePct:0.05,maePct:-0.20,profitGivebackPctPoints:0.10,captureRatio:-1,barsHeld:3},
  {symbol:'A',entryTimestamp:'2026-01-01T02:00:00Z',netReturnPct:0.05,grossReturnPct:0.10,mfePct:0.15,maePct:-0.03,profitGivebackPctPoints:0.05,captureRatio:2/3,barsHeld:2},
];
const summary=summarizeEconomicTrades(trades);
assert.equal(summary.tradeCount,3);
assert.equal(summary.uniqueSymbols,2);
assert.ok(Math.abs(summary.averageNetReturnPct-0.05)<1e-12);
assert.ok(Math.abs(summary.profitFactor-2.5)<1e-12);
assert.ok(Math.abs(summary.maxSingleSymbolShare-2/3)<1e-12);
assert.ok(Math.abs(maxSequentialDrawdownPctPoints(trades)-0.10)<1e-12);

console.log('P23.10F frozen economic validation tests passed');
