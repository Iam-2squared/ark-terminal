import assert from "node:assert/strict";
import test from "node:test";

import {
  createTradeCandidateKey,
  createTradeMemoryRecord,
  saveTradeMemoryRecord,
  summarizeTradeMemory,
} from "../trading/trade-memory.js";

function memoryStorage() {
  const values =
    new Map();

  return {
    getItem(key) {
      return values.has(key)
        ? values.get(key)
        : null;
    },

    setItem(key, value) {
      values.set(
        key,
        String(value),
      );
    },

    removeItem(key) {
      values.delete(key);
    },

    clear() {
      values.clear();
    },
  };
}

function sampleState() {
  return {
    symbol: "2410.T",
    companyName: "テスト会社",

    analysis: {
      totalScore: 72,
      technicalScore: 75,
      verdict: "強気",
    },

    prediction: {
      direction: "上向き優勢",
      confidence: 70,
    },

    indicators: {
      currentPrice: 2_918,
      rsi: 61,

      movingAverages: {
        ma25: 2_880,
        ma75: 2_650,
      },

      macd: {
        histogram: 12,
      },

      adx: 30,
    },

    marketEnvironment: {
      regime: "neutral",
    },
  };
}

function sampleDecision() {
  return {
    symbol: "2410.T",
    setupLabel: "押し目反発",

    analysis: {
      setup: "pullback_long",
      latestBarTime: 1_700_000_000,
      currentPrice: 2_918,
      vwap: 2_900,
      atr: 18,
      volumeRatio: 1.9,
      setupStrengthScore: 82,
      dataQualityScore: 96,
      dataAgeSeconds: 60,
    },

    plan: {
      entryPrice: 2_918,
      stopPrice: 2_882,
      firstTargetPrice: 2_954,
      secondTargetPrice: 2_990,
      riskReward: 2,
      quantity: 100,
    },
  };
}

function sampleGate() {
  return {
    gate: {
      decision: "approve",
      confidence: 81,
      summary: "条件は概ね整合しています。",
      reasons: ["日足と15分足が整合"],
      riskFlags: ["none"],
      conditionsToApprove: [],
      disclaimer: "Paper審査です。",
    },

    meta: {
      model: "test-model",
      responseId: "resp_test",
      generatedAt:
        "2026-08-01T12:00:00.000Z",
    },
  };
}

test("候補キーは同じシグナルを安定して識別する", () => {
  const first =
    createTradeCandidateKey({
      symbol: "2410.t",
      setup: "pullback_long",
      entryPrice: 2_918,
      signalTime: 1_700_000_000,
    });

  const second =
    createTradeCandidateKey({
      symbol: "2410.T",
      setup: "pullback_long",
      entryPrice: 2_918,
      signalTime: 1_700_000_000,
    });

  assert.equal(first, second);
});

test("OpenAI審査結果からTrade Memoryを作成する", () => {
  const record =
    createTradeMemoryRecord({
      state: sampleState(),
      decision: sampleDecision(),
      gateResult: sampleGate(),
    });

  assert.equal(
    record.symbol,
    "2410.T",
  );

  assert.equal(
    record.decision,
    "approve",
  );

  assert.equal(
    record.status,
    "pending",
  );

  assert.equal(
    record.intraday
      .volumeRatio,
    1.9,
  );

  assert.equal(
    record.daily
      .indicators
      .rsi,
    61,
  );
});

test("同一候補・同一AI判定を重複保存しない", () => {
  globalThis.localStorage =
    memoryStorage();

  const record =
    createTradeMemoryRecord({
      state: sampleState(),
      decision: sampleDecision(),
      gateResult: sampleGate(),
    });

  const first =
    saveTradeMemoryRecord(
      record,
    );

  const second =
    saveTradeMemoryRecord({
      ...record,
      id: "different-id",
    });

  assert.equal(
    first.saved,
    true,
  );

  assert.equal(
    second.saved,
    false,
  );

  assert.equal(
    second.duplicate,
    true,
  );
});

test("Trade Memoryの判定件数を集計する", () => {
  const summary =
    summarizeTradeMemory([
      {
        decision: "approve",
        status: "pending",
      },

      {
        decision: "wait",
        status: "pending",
      },

      {
        decision: "reject",
        status: "pending",
      },

      {
        decision: "approve",
        status: "resolved",

        evaluation: {
          hit: true,
        },
      },
    ]);

  assert.equal(
    summary.totalCount,
    4,
  );

  assert.equal(
    summary.approveCount,
    2,
  );

  assert.equal(
    summary.waitCount,
    1,
  );

  assert.equal(
    summary.rejectCount,
    1,
  );

  assert.equal(
    summary.approvalWinRate,
    100,
  );
});