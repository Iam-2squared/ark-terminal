import test from "node:test";
import assert from "node:assert/strict";
import { buildPhase48EvaluationPayload, auditPhase48Payload, classifyModelHealth, PHASE48_SAFETY } from "./phase48-evaluation-payload.js";
import { buildPhase48DashboardView } from "./phase48-dashboard-view.js";

const candidate = {
  modelId: "m-1",
  modelType: "GRADIENT_BOOSTING",
  status: "CANDIDATE_REVIEW_ONLY",
  trainingPeriod: { start: "2024-01-01", end: "2025-12-31" },
  testPeriod: { start: "2026-01-01", end: "2026-06-30" },
  foldCount: 6,
  sampleCount: 420,
  lineageChecksum: "abc",
  metrics: {
    accuracy: 0.61,
    precision: 0.6,
    recall: 0.58,
    auc: 0.62,
    brierScore: 0.2,
    profitFactor: 1.31,
    sharpe: 1.05,
    maximumDrawdown: 0.12,
    cagr: 0.18,
    netReturn: 0.24,
    tradeCount: 120,
  },
  audit: { blockers: [], futureLeakDetected: false },
};

test("classifies healthy model", () => {
  assert.equal(classifyModelHealth(candidate.metrics, candidate.audit), "HEALTHY");
});

test("builds deterministic evaluation payload", () => {
  const input = { candidate, prediction: { symbol: "7203.T", sessionDate: "2026-08-06", aiScore: 68, expectedReturn: 0.03, confidence: 0.71, direction: "UP" }, featureReasons: ["RSI recovery"], risks: ["high volatility"] };
  const a = buildPhase48EvaluationPayload(input);
  const b = buildPhase48EvaluationPayload(input);
  assert.equal(a.checksum, b.checksum);
  assert.equal(a.status, "EVALUATION_ONLY");
  assert.equal(a.safety.liveTradingAllowed, false);
});

test("blocks tampered payload", () => {
  const payload = buildPhase48EvaluationPayload({ candidate, prediction: {} });
  const tampered = { ...payload, metrics: { ...payload.metrics, auc: 0.99 } };
  assert.equal(auditPhase48Payload(tampered).status, "BLOCKED");
});

test("builds UI-ready dashboard payload", () => {
  const payload = buildPhase48EvaluationPayload({ candidate, prediction: { aiScore: 70, confidence: 0.7 } });
  const view = buildPhase48DashboardView(payload);
  assert.equal(view.status, "READY_FOR_UI");
  assert.equal(view.headline.adoptedModel, "GRADIENT_BOOSTING");
  assert.equal(view.reviewRequired, true);
});

test("keeps all execution paths disabled", () => {
  assert.deepEqual(PHASE48_SAFETY, {
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    humanApprovalRequired: true,
  });
});
