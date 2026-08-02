import { buildMacroSummary } from "../market-context/macro-engine.js";
import { scoreMarketSeries, scoreToSentiment } from "./market-score.js";

export const MACRO_CONFIGURATION = Object.freeze([
  Object.freeze({ symbol: "VIX", weight: 2.5, scale: 10, invert: true }),
  Object.freeze({ symbol: "US10Y", weight: 1.8, scale: 5, invert: true }),
  Object.freeze({ symbol: "WTI", weight: 1.2, scale: 4, invert: true }),
  Object.freeze({ symbol: "GOLD", weight: 0.6, scale: 2, invert: true }),
  Object.freeze({ symbol: "USDJPY", weight: 0.5, scale: 2 }),
  Object.freeze({ symbol: "BITCOIN", weight: 0.8, scale: 5 }),
  Object.freeze({ symbol: "ETHEREUM", weight: 0.6, scale: 6 }),
]);

function finiteOrNull(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

export function classifyMacroRisk(vix) {
  const value = finiteOrNull(vix);

  if (value === null) return "UNKNOWN";
  if (value >= 35) return "HIGH";
  if (value >= 25) return "ELEVATED";
  if (value <= 15) return "LOW";
  return "NORMAL";
}

function buildSignals(items) {
  return items
    .filter((item) => item.available && (item.score >= 65 || item.score <= 35))
    .map((item) => ({
      symbol: item.symbol,
      direction: item.score >= 65 ? "supportive" : "restrictive",
      score: item.score,
      changePercent: item.changePercent,
    }));
}

export function analyzeMacroEnvironment(points = []) {
  const report = scoreMarketSeries(points, MACRO_CONFIGURATION);
  const vix = report.items.find((item) => item.symbol === "VIX");
  const vixLevel = vix?.available ? finiteOrNull(vix.price) : null;
  const sentiment = scoreToSentiment(report.score);
  const summary = buildMacroSummary({
    macro: {
      score: report.score,
      sentiment,
    },
  });

  return {
    score: report.score,
    confidence: report.confidence,
    coverage: report.coverage,
    availableCount: report.availableCount,
    requestedCount: report.requestedCount,
    vixLevel,
    sentiment,
    riskLevel: classifyMacroRisk(vixLevel),
    summary,
    signals: buildSignals(report.items),
    items: report.items,
  };
}

export class MacroEngine {
  analyze(points = []) {
    return analyzeMacroEnvironment(points);
  }
}

export const macroEngine = new MacroEngine();

export default analyzeMacroEnvironment;
