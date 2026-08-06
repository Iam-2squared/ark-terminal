import assert from "node:assert/strict";
import test from "node:test";

import { buildSegmentPerformanceV1 } from "../analysis/segment-performance-v1.js";
import { buildLivePerformanceKpisV1 } from "../analysis/live-performance-kpis-v1.js";
import {
  buildFailureReviewV2Payload,
  selectFailureReviewExamples,
  validateFailureReviewV2Advice,
} from "../learning/openai-failure-review-v2.js";

function resolved(overrides = {}) {
  return {
    id: crypto.randomUUID(),
    symbol: "7203.T",
    industry: "Transport Equipment",
    marketSection: "PRIME",
    marketCap: 40_000_000_000_000,
    entryPrice: 2500,
    volume: 2_000_000,
    signal: "BUY",
    status: "resolved",
    directionHit: true,
    costAdjustedReturn: 2,
    confidence: 0.85,
    marketRegime: "BULL",
    ...overrides,
  };
}

test("Part5 segments performance by symbol, industry, market section, market cap, price and volume", () => {
  const report = buildSegmentPerformanceV1({
    rows: [
      resolved(),
      resolved({ id: "two" }),
      resolved({ id: "three", symbol: "6758.T", industry: "Electric Appliances", marketSection: "PRIME", marketCap: 15_000_000_000_000, entryPrice: 12000, volume: 4_000_000 }),
    ],
    options: { minimumSample: 2, generatedAt: "2026-08-06T00:00:00.000Z" },
  });

  assert.equal(report.bySymbol["7203.T"].sampleCount, 2);
  assert.equal(report.byIndustry["Transport Equipment"].sampleCount, 2);
  assert.equal(report.byMarketSection.PRIME.sampleCount, 3);
  assert.equal(report.byMarketCap.OVER_1T.sampleCount, 3);
  assert.equal(report.byPrice["1000_3000"].sampleCount, 2);
  assert.equal(report.byVolume.HIGH.sampleCount, 3);
  assert.equal(report.rankings.symbols[0].key, "7203.T");
  assert.equal(report.safety.liveTradingAllowed, false);
});

test("Part5 warns on insufficient samples", () => {
  const report = buildSegmentPerformanceV1({ rows: [resolved()], options: { minimumSample: 3 } });
  assert.deepEqual(report.warnings.symbol, [{ key: "7203.T", sampleCount: 1, required: 3 }]);
});

test("Part6 separates prediction accuracy from trading profitability and costs", () => {
  const kpis = buildLivePerformanceKpisV1({
    rows: [
      resolved({ grossReturn: 3, netReturn: 2.5, fees: 0.2, slippage: 0.3, exposure: 0.5, turnover: 1, directionHit: true }),
      resolved({ id: "loss", grossReturn: -1, netReturn: -1.2, fees: 0.1, slippage: 0.1, exposure: 0.3, turnover: 2, directionHit: false }),
    ],
  });

  assert.equal(kpis.sampleCount, 2);
  assert.equal(kpis.predictionAccuracy, 0.5);
  assert.equal(kpis.tradeWinRate, 0.5);
  assert.equal(kpis.grossReturn, 2);
  assert.equal(kpis.netReturn, 1.3);
  assert.equal(kpis.transactionCost, 0.30000000000000004);
  assert.equal(kpis.slippage, 0.4);
  assert.equal(kpis.turnover, 3);
  assert.equal(kpis.safety.executionAllowed, false);
});

test("Part7 only includes resolved directional failures and preserves safety constraints", () => {
  const examples = selectFailureReviewExamples([
    resolved({ id: "bad", directionHit: false, actualReturn: -2, newsSummary: "earnings miss" }),
    resolved({ id: "good", directionHit: true }),
    resolved({ id: "pending", status: "pending", directionHit: false }),
    resolved({ id: "hold", signal: "HOLD", directionHit: false }),
  ]);

  assert.equal(examples.length, 1);
  assert.equal(examples[0].id, "bad");

  const payload = buildFailureReviewV2Payload({
    failures: [resolved({ id: "bad", directionHit: false })],
    metrics: { accuracy: 0.5, profitFactor: 0.9, sampleCount: 20 },
    currentModel: { version: "champion-v1", weights: { rsi: 0.2 } },
  });

  assert.equal(payload.failures.length, 1);
  assert.equal(payload.constraints.automaticCandidatePromotionAllowed, false);
  assert.equal(payload.constraints.productionUpdateAllowed, false);
  assert.equal(payload.constraints.brokerWriteAllowed, false);
});

test("Part7 rejects unsafe OpenAI advice", () => {
  assert.throws(() => validateFailureReviewV2Advice({ safety: {
    advisoryOnly: true,
    humanApprovalRequired: true,
    productionUpdateAllowed: true,
    brokerWriteAllowed: false,
  } }), /SAFETY_CONTRACT_VIOLATION/);

  const validated = validateFailureReviewV2Advice({ safety: {
    advisoryOnly: true,
    humanApprovalRequired: true,
    productionUpdateAllowed: false,
    brokerWriteAllowed: false,
  } });

  assert.equal(validated.status, "ADVISORY_ONLY");
  assert.equal(validated.automaticPromotionAllowed, false);
});
