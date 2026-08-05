import assert from "node:assert/strict";
import test from "node:test";

import {
  buildWalkForwardSeries,
  evaluateWalkForwardPrediction,
  runWalkForwardAudit,
  summarizeWalkForwardAudit,
} from "../analysis/walk-forward-accuracy-audit.js";

function rowsFor(symbol, closes) {
  return closes.map((close, index) => ({
    symbol,
    date: new Date(Date.UTC(2026, 0, index + 1)).toISOString().slice(0, 10),
    close,
    features: { index },
  }));
}

test("mixed symbols are evaluated only against the same symbol", async () => {
  const aaa = rowsFor("AAA", [100, 101, 102, 103]);
  const bbb = rowsFor("BBB", [200, 199, 198, 197]);
  const mixed = aaa.flatMap((row, index) => [row, bbb[index]]);

  const result = await runWalkForwardAudit({
    rows: mixed,
    horizon: 1,
    minimumHistory: 2,
    predictor: async ({ symbol, history }) => {
      assert.ok(history.every((row) => row.symbol === symbol));
      return { action: "BUY", confidence: 70 };
    },
  });

  assert.equal(result.version, "walk-forward-accuracy-audit-v2");
  assert.equal(result.crossSymbolJoinBlocked, true);
  assert.equal(result.horizonUnit, "TRADING_SESSIONS");
  assert.equal(result.predictions.length, 4);
  assert.ok(result.predictions.every((item) => ["AAA", "BBB"].includes(item.symbol)));
  assert.equal(result.summary.total, 4);
  assert.equal(result.summary.correct, 2);
});

test("duplicate symbol and date rows use the last input row", () => {
  const prepared = buildWalkForwardSeries([
    { symbol: "AAA", date: "2026-01-01", close: 100 },
    { symbol: "AAA", date: "2026-01-01", close: 101 },
    { symbol: "AAA", date: "2026-01-02", close: 102 },
  ]);

  assert.equal(prepared.diagnostics.duplicateRows, 1);
  assert.equal(prepared.diagnostics.normalizedRows, 2);
  assert.equal(prepared.seriesBySymbol.get("AAA")[0].close, 101);
  assert.equal(prepared.joinPolicy.crossSymbolFallbackAllowed, false);
});

test("HOLD and NO_TRADE remain visible but are excluded from Accuracy", () => {
  const summary = summarizeWalkForwardAudit([
    {
      action: "HOLD",
      accuracyEligible: false,
      correct: null,
      strategyReturn: null,
      resolutionStatus: "RESOLVED",
    },
    {
      action: "NO_TRADE",
      accuracyEligible: false,
      correct: null,
      strategyReturn: null,
      resolutionStatus: "RESOLVED",
    },
    {
      action: "BUY",
      accuracyEligible: true,
      correct: true,
      actualDirection: "UP",
      confidence: 80,
      returnPercent: 2,
      strategyReturn: 2,
      resolutionStatus: "RESOLVED",
    },
  ]);

  assert.equal(summary.sourceTotal, 3);
  assert.equal(summary.total, 1);
  assert.equal(summary.correct, 1);
  assert.equal(summary.accuracy, 100);
  assert.equal(summary.excluded.hold, 1);
  assert.equal(summary.excluded.noTrade, 1);
});

test("explicit symbol mismatch fails closed", () => {
  assert.throws(
    () =>
      evaluateWalkForwardPrediction({
        prediction: { action: "BUY" },
        entryRow: { symbol: "AAA", date: "2026-01-01", close: 100 },
        exitRow: { symbol: "BBB", date: "2026-01-02", close: 101 },
      }),
    /WALK_FORWARD_SYMBOL_MISMATCH/,
  );
});

test("horizon counts trading rows rather than calendar days", async () => {
  const result = await runWalkForwardAudit({
    rows: [
      { symbol: "AAA", date: "2026-01-09", close: 100 },
      { symbol: "AAA", date: "2026-01-12", close: 101 },
      { symbol: "AAA", date: "2026-01-13", close: 102 },
    ],
    horizon: 1,
    minimumHistory: 1,
    predictor: async () => ({ action: "BUY", confidence: 70 }),
  });

  assert.equal(result.predictions[0].entryDate, "2026-01-09");
  assert.equal(result.predictions[0].exitDate, "2026-01-12");
  assert.equal(result.predictions[0].horizonUnit, "TRADING_SESSIONS");
});
