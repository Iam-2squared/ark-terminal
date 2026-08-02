import test from "node:test";
import assert from "node:assert/strict";

import { createMarketDataPoint } from "../market-intelligence/market-data-model.js";
import {
  MACRO_CONFIGURATION,
  MacroEngine,
  analyzeMacroEnvironment,
  classifyMacroRisk,
} from "../market-intelligence/macro-engine.js";

const TIMESTAMP = "2026-08-01T00:00:00.000Z";

function point(symbol, changePercent, { price = 100, confidence = 100 } = {}) {
  return createMarketDataPoint({
    symbol,
    price,
    change: (price * changePercent) / 100,
    changePercent,
    timestamp: TIMESTAMP,
    source: "test-provider",
    confidence,
  });
}

function supportiveMacro() {
  const changes = {
    VIX: -10,
    US10Y: -5,
    WTI: -4,
    GOLD: -2,
    USDJPY: 2,
    BITCOIN: 5,
    ETHEREUM: 6,
  };

  return MACRO_CONFIGURATION.map(({ symbol }) =>
    point(symbol, changes[symbol], { price: symbol === "VIX" ? 14 : 100 }),
  );
}

test("Macro engine combines inverted risk factors and risk-on assets", () => {
  const report = analyzeMacroEnvironment(supportiveMacro());

  assert.equal(report.score, 100);
  assert.equal(report.sentiment, "BULLISH");
  assert.equal(report.riskLevel, "LOW");
  assert.equal(report.vixLevel, 14);
  assert.equal(report.coverage, 100);
  assert.equal(report.signals.length, MACRO_CONFIGURATION.length);
});

test("Absolute VIX level drives the macro risk classification", () => {
  const report = analyzeMacroEnvironment([
    point("VIX", 10, { price: 35 }),
  ]);

  assert.equal(report.riskLevel, "HIGH");
  assert.equal(report.vixLevel, 35);
  assert.equal(report.score, 0);
  assert.equal(report.signals[0].direction, "restrictive");
});

test("Macro risk bands have stable boundaries", () => {
  assert.equal(classifyMacroRisk(null), "UNKNOWN");
  assert.equal(classifyMacroRisk(15), "LOW");
  assert.equal(classifyMacroRisk(20), "NORMAL");
  assert.equal(classifyMacroRisk(25), "ELEVATED");
  assert.equal(classifyMacroRisk(35), "HIGH");
});

test("Missing macro series lower coverage without becoming zero changes", () => {
  const report = analyzeMacroEnvironment([
    point("USDJPY", 2, { confidence: 80 }),
  ]);

  assert.equal(report.score, 100);
  assert.ok(report.coverage < 10);
  assert.ok(report.confidence < 10);
  assert.equal(report.riskLevel, "UNKNOWN");
});

test("Macro summary reuses the existing summary contract", () => {
  const report = analyzeMacroEnvironment(supportiveMacro());

  assert.deepEqual(report.summary, {
    title: "Macro Environment",
    score: 100,
    sentiment: "BULLISH",
  });
});

test("MacroEngine exposes stateless analysis", () => {
  const engine = new MacroEngine();
  assert.deepEqual(
    engine.analyze(supportiveMacro()),
    analyzeMacroEnvironment(supportiveMacro()),
  );
});
