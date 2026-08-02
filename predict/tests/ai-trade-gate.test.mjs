import assert from "node:assert/strict";
import test from "node:test";

import {
  AiTradeGateInternals,
} from "../../api/ai-trade-gate.js";

import {
  buildAiTradeGatePayload,
  gateDecisionClass,
} from "../trading/ai-trade-gate.js";

function sampleState() {
  return {
    symbol: "2410.T",
    companyName:
      "キャリアデザインセンター",

    indicators: {
      currentPrice: 2_918,

      movingAverages: {
        ma25: 2_887,
        ma75: 2_658,
      },

      rsi: 62,
      adx: 31,
    },

    analysis: {
      totalScore: 71,
      technicalScore: 74,
      verdict: "強気",

      factors: [
        {
          key: "movingAverage",
          label: "移動平均線",
          score: 10,
          maximum: 10,
          available: true,
          reason:
            "25日線と75日線が上向きです。",
        },
      ],
    },

    prediction: {
      direction:
        "上向き優勢",

      confidence: 72,
    },

    quality: {
      status: "passed",
      qualityScore: 96,
      issues: [],
    },

    marketEnvironment: {
      regime: "neutral",
      score: 55,
    },

    context: {
      company: {
        name:
          "キャリアデザインセンター",
      },
    },
  };
}

function sampleDecision() {
  return {
    version:
      "intraday-cash-buy-integration-v2",

    symbol: "2410.T",
    available: true,
    paperCandidate: true,
    action: "enter_long",
    setupLabel: "押し目反発",

    reasons: [
      "VWAP上を維持しています。",
    ],

    warnings: [],

    analysis: {
      setup: "pullback_long",
      currentPrice: 2_918,
      vwap: 2_900,
      atr: 18,
      volumeRatio: 1.9,
      priorHigh: 2_935,
      priorLow: 2_880,
      setupStrengthScore: 82,
      dataQualityScore: 94,
      dataAgeSeconds: 60,
      aboveVwap: true,
      pullbackLong: true,
      volumeSurge: true,
      sessionBarCount: 12,
      historyBarCount: 200,
    },

    plan: {
      action: "enter_long",
      side: "long",
      entryPrice: 2_918,
      stopPrice: 2_882,
      firstTargetPrice: 2_954,
      secondTargetPrice: 2_990,
      riskReward: 2,
      quantity: 100,
      maximumHoldingBars: 12,
    },
  };
}

test("AI審査payloadは現物買い候補と日足情報だけを含む", () => {
  const payload =
    buildAiTradeGatePayload(
      sampleState(),
      sampleDecision(),
    );

  assert.equal(
    payload.symbol,
    "2410.T",
  );

  assert.equal(
    payload.policy
      .cashBuyOnly,
    true,
  );

  assert.equal(
    payload.policy
      .shortSellingEnabled,
    false,
  );

  assert.equal(
    payload.tradeDecision
      .action,
    "enter_long",
  );

  assert.equal(
    payload.dailyContext
      .indicators
      .movingAverages
      .ma25,
    2_887,
  );
});

test("買い候補でない判断はOpenAI審査へ送らない", () => {
  const decision = {
    ...sampleDecision(),
    paperCandidate: false,
    action: "wait",
  };

  assert.throws(
    () =>
      buildAiTradeGatePayload(
        sampleState(),
        decision,
      ),
    /現物買い候補/,
  );
});

test("APIは現物買い候補だけを受け付ける", () => {
  const payload =
    buildAiTradeGatePayload(
      sampleState(),
      sampleDecision(),
    );

  const validated =
    AiTradeGateInternals
      .validateRequestBody(
        payload,
      );

  assert.equal(
    validated.symbol,
    "2410.T",
  );

  assert.throws(
    () =>
      AiTradeGateInternals
        .validateRequestBody({
          ...payload,

          tradeDecision: {
            ...payload
              .tradeDecision,

            action:
              "enter_short",

            plan: {
              side: "short",
            },
          },
        }),
    /現物買い候補/,
  );
});

test("OpenAI審査はstrict JSON Schemaを使用する", () => {
  const payload =
    buildAiTradeGatePayload(
      sampleState(),
      sampleDecision(),
    );

  const request =
    AiTradeGateInternals
      .buildOpenAiRequest(
        payload,
        "test-model",
      );

  assert.equal(
    request.model,
    "test-model",
  );

  assert.equal(
    request.text
      .format
      .type,
    "json_schema",
  );

  assert.equal(
    request.text
      .format
      .strict,
    true,
  );

  assert.equal(
    gateDecisionClass(
      "reject",
    ),
    "reject",
  );
});