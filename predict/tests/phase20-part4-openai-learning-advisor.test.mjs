import assert from "node:assert/strict";
import test from "node:test";

import { AiLearningAdvisorInternals } from "../../api/ai-learning-advisor.js";
import {
  buildLearningAdvisorPayload,
  selectLearningFailureExamples,
  validateLearningAdvisorAdvice,
} from "../learning/openai-learning-advisor.js";

function sampleAudit() {
  return {
    version: "walk-forward-accuracy-audit-v2",
    generatedAt: "2026-08-06T00:00:00.000Z",
    horizon: 5,
    horizonUnit: "TRADING_SESSIONS",
    neutralThreshold: 0.5,
    futureLeakChecked: true,
    crossSymbolJoinBlocked: true,
    labelPolicy: { version: "directional-label-policy-v2" },
    joinPolicy: { version: "symbol-session-join-v2" },
    diagnostics: {
      sourceRows: 120,
      normalizedRows: 118,
      invalidRows: 1,
      duplicateRows: 1,
      symbols: 3,
    },
    summary: {
      sourceTotal: 20,
      total: 12,
      correct: 7,
      accuracy: 58.33,
      buySignals: 8,
      buyPrecision: 62.5,
      sellSignals: 4,
      sellPrecision: 50,
      averageStrategyReturn: 0.4,
      profitFactor: 1.2,
      maximumDrawdown: 8,
      calibrationError: 0.18,
      excluded: {
        total: 8,
        hold: 4,
        noTrade: 3,
        unknown: 1,
        unresolved: 0,
      },
    },
    predictions: [
      {
        symbol: "AAA",
        entryDate: "2026-08-01",
        exitDate: "2026-08-06",
        horizon: 5,
        horizonUnit: "TRADING_SESSIONS",
        action: "BUY",
        predictedDirection: "UP",
        actualDirection: "DOWN",
        correct: false,
        resolutionStatus: "RESOLVED",
        score: 74,
        confidence: 80,
        returnPercent: -3,
        strategyReturn: -3,
        features: { rsi: 75, macd: 1.2, note: "ignored" },
      },
      {
        symbol: "BBB",
        action: "HOLD",
        correct: false,
        resolutionStatus: "RESOLVED",
      },
      {
        symbol: "CCC",
        action: "SELL",
        correct: false,
        resolutionStatus: "PENDING",
      },
      {
        symbol: "DDD",
        action: "SELL",
        correct: true,
        resolutionStatus: "RESOLVED",
      },
    ],
  };
}

function safeAdvice() {
  return {
    summary: "失敗例はまだ少数です。",
    dataWarnings: ["サンプル数が少ない"],
    failurePatterns: [],
    candidateHypothesis: {
      shouldCreateCandidate: false,
      rationale: "追加データが必要です。",
      weightChanges: [],
      thresholdChanges: [],
      exclusionRules: [],
    },
    validationPlan: [
      {
        test: "walk-forward",
        successMetric: "profit factor improves",
        minimumSample: 50,
        reason: "過学習を避けるため",
      },
    ],
    safety: {
      advisoryOnly: true,
      humanApprovalRequired: true,
      productionUpdateAllowed: false,
      brokerWriteAllowed: false,
    },
  };
}

test("learning payload contains only resolved directional failures", () => {
  const payload = buildLearningAdvisorPayload({
    audit: sampleAudit(),
    currentModel: {
      version: "production-v1",
      weights: { rsi: 0.2, macd: 0.3, label: "ignored" },
    },
  });

  assert.equal(payload.failureExamples.length, 1);
  assert.equal(payload.failureExamples[0].symbol, "AAA");
  assert.deepEqual(payload.failureExamples[0].features, { rsi: 75, macd: 1.2 });
  assert.equal(payload.constraints.advisoryOnly, true);
  assert.equal(payload.constraints.productionUpdateAllowed, false);
  assert.equal(payload.constraints.brokerWriteAllowed, false);
  assert.equal(payload.audit.futureLeakChecked, true);
  assert.equal(payload.audit.crossSymbolJoinBlocked, true);
});

test("failure selector excludes wins, non-directional actions, and unresolved rows", () => {
  const selected = selectLearningFailureExamples(sampleAudit().predictions);
  assert.equal(selected.length, 1);
  assert.equal(selected[0].action, "BUY");
});

test("advisor safety contract rejects production or broker write permission", () => {
  const valid = validateLearningAdvisorAdvice(safeAdvice());
  assert.equal(valid.status, "ADVISORY_ONLY");
  assert.equal(valid.candidateCreationAllowed, false);

  const unsafe = safeAdvice();
  unsafe.safety.productionUpdateAllowed = true;
  assert.throws(
    () => validateLearningAdvisorAdvice(unsafe),
    /LEARNING_ADVISOR_SAFETY_CONTRACT_VIOLATION/,
  );
});

test("API request uses a strict schema and supplied model", () => {
  const payload = AiLearningAdvisorInternals.validateRequestBody({
    audit: sampleAudit(),
    currentModel: { version: "production-v1" },
  });
  const request = AiLearningAdvisorInternals.buildOpenAiRequest(payload, "test-model");

  assert.equal(request.model, "test-model");
  assert.equal(request.text.format.type, "json_schema");
  assert.equal(request.text.format.strict, true);
  assert.equal(request.text.format.schema.additionalProperties, false);
  assert.equal(
    request.text.format.schema.properties.safety.properties.productionUpdateAllowed.const,
    false,
  );
});

test("API request validation requires deterministic audit summary", () => {
  assert.throws(
    () => AiLearningAdvisorInternals.validateRequestBody({ audit: {} }),
    /audit.summary must be an object/,
  );
});

test("parsed OpenAI advice remains advisory only", () => {
  const review = AiLearningAdvisorInternals.parseAdvice({
    output_text: JSON.stringify(safeAdvice()),
  });

  assert.equal(review.status, "ADVISORY_ONLY");
  assert.equal(review.productionUpdateAllowed, false);
  assert.equal(review.brokerWriteAllowed, false);
});
