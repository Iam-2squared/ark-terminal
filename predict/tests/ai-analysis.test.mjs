import assert from "node:assert/strict";
import test from "node:test";

import { AiAnalysisInternals } from "../../api/ai-analysis.js";
import {
  AiAnalysisUiInternals,
  buildAiAnalysisPayload,
} from "../ai-analysis.js";

function sampleState() {
  return {
    symbol: "285A.T",
    companyName: "キオクシア",
    period: 5,
    quote: { price: 3_200, changePercent: 1.25 },
    analysis: {
      totalScore: 67,
      technicalScore: 63,
      verdict: "やや強気",
      categoryScores: { trend: 18 },
      factors: [
        {
          key: "rsi",
          label: "RSI",
          score: 4,
          maximum: 6,
          available: true,
          reason: "RSIは中立圏です。",
        },
      ],
    },
    prediction: {
      direction: "上向き優勢",
      confidence: 64,
      expectedMoveRange: "±4.2%",
      downsideRisk: "中",
    },
    indicators: {
      currentPrice: 3_200,
      rsi: 57,
      movingAverages: { ma5: 3_160, ma25: 3_020 },
      rawCandles: Array.from({ length: 200 }, (_, index) => index),
    },
    quality: { status: "passed", qualityScore: 98, issues: [] },
    marketEnvironment: { regime: "リスクオン", score: 70 },
    context: {
      company: { name: "キオクシア", industry: "Semiconductors" },
      news: [
        {
          headline: "メモリー需要が回復",
          summary: "需要の回復が報じられました。",
          source: "Example",
          publishedAt: "2026-08-01T00:00:00Z",
        },
      ],
    },
  };
}

test("AI payload contains calculated outputs and limits large arrays", () => {
  const payload = buildAiAnalysisPayload(sampleState());

  assert.equal(payload.symbol, "285A.T");
  assert.equal(payload.analysis.totalScore, 67);
  assert.equal(payload.analysis.factors.length, 1);
  assert.ok(payload.indicators.rawCandles.length <= 12);
  assert.equal(payload.news[0].source, "Example");
});

test("request validation requires a normalized symbol and calculated data", () => {
  const valid = AiAnalysisInternals.validateRequestBody({
    symbol: "285a.t",
    analysis: { totalScore: 60 },
    prediction: { direction: "neutral" },
  });

  assert.equal(valid.symbol, "285A.T");
  assert.throws(
    () =>
      AiAnalysisInternals.validateRequestBody({
        symbol: "<script>",
        analysis: {},
        prediction: {},
      }),
    /銘柄コードが不正/,
  );
});

test("OpenAI request uses strict JSON schema and supplied model", () => {
  const request = AiAnalysisInternals.buildOpenAiRequest(
    {
      symbol: "285A.T",
      analysis: {},
      prediction: {},
    },
    "test-model",
  );

  assert.equal(request.model, "test-model");
  assert.equal(request.text.format.type, "json_schema");
  assert.equal(request.text.format.strict, true);
  assert.equal(request.text.format.schema.additionalProperties, false);
});

test("response text extraction supports Responses API output content", () => {
  const text = AiAnalysisInternals.extractResponseText({
    output: [
      {
        content: [
          {
            type: "output_text",
            text: '{"stance":"中立"}',
          },
        ],
      },
    ],
  });

  assert.equal(text, '{"stance":"中立"}');
});

test("stance class maps strong and weak assessments", () => {
  assert.equal(AiAnalysisUiInternals.stanceClass("強気"), "positive");
  assert.equal(AiAnalysisUiInternals.stanceClass("弱気"), "negative");
  assert.equal(AiAnalysisUiInternals.stanceClass("中立"), "neutral");
});
