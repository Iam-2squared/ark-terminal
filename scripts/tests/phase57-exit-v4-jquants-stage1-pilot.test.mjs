import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  classifyMinuteAbsence,
  compareTimestampHypotheses,
  parseCsvLine,
  tierFromQuality,
} from "../lib/phase57-jquants-stage1-quality.mjs";

test("CSV parser preserves quoted commas", () => {
  assert.deepEqual(parseCsvLine('a,"b,c","d""e"'), ["a", "b,c", 'd"e']);
});

test("tick OHLCV proves same-label bar-start hypothesis", () => {
  const minuteRows = [
    { Time: "09:00", O: 100, H: 102, L: 99, C: 101, Vo: 6 },
    { Time: "09:01", O: 103, H: 103, L: 103, C: 103, Vo: 2 },
    { Time: "09:02", O: 98, H: 98, L: 98, C: 98, Vo: 3 },
  ];
  const tickRows = [
    { Time: "09:00:01.000000", Price: 100, TradingVolume: 1 },
    { Time: "09:00:20.000000", Price: 102, TradingVolume: 2 },
    { Time: "09:00:59.999999", Price: 99, TradingVolume: 1 },
    { Time: "09:00:59.999999", Price: 101, TradingVolume: 2 },
    { Time: "09:01:10.000000", Price: 103, TradingVolume: 2 },
    { Time: "09:02:10.000000", Price: 98, TradingVolume: 3 },
  ];
  const result = compareTimestampHypotheses(minuteRows, tickRows, ["09:00", "09:01", "09:02"]);
  assert.equal(result.conclusion, "BAR_START_HALF_OPEN");
  assert.equal(result.sameMatches, 3);
});

test("ambiguous missing minute remains UNKNOWN class", () => {
  assert.equal(classifyMinuteAbsence({ listedAtSession: true, dailyRowPresent: true, dailyHasTrade: true, tickObserved: false, minuteObserved: false }), "NO_TRADE_OR_PROVIDER_MISSING_UNKNOWN");
  assert.equal(classifyMinuteAbsence({ listedAtSession: true, dailyRowPresent: true, dailyHasTrade: true, tickObserved: true, minuteObserved: false }), "MISSING_PROVIDER_MINUTE");
});

test("provider historical availableAt failure blocks Tier 1", () => {
  const audit = { timestamp: "PASS", fiveMinuteAggregation: "PASS", historicalProviderAvailableAt: "FAIL", universe: "PASS", adjustment: "PASS", missing: "PASS", hybridParity: "PASS", entryParity: "PASS", pitViolations: 0 };
  assert.equal(tierFromQuality(audit), "TIER_2_RECONSTRUCTED_REPLAY_CANDIDATE");
});

test("precommit stays outcome blind and uses exposed PURGE sessions only", () => {
  const manifest = JSON.parse(fs.readFileSync("predict/research/phase57-exit-v4-jquants-stage1-precommit-v1.json", "utf8"));
  assert.deepEqual(manifest.sessions, ["2025-08-27", "2025-10-09", "2025-11-25"]);
  assert.equal(manifest.sessionClassification, "ALREADY_EXPOSED_PURGE_QUALITY_EVIDENCE");
  for (const forbidden of ["EXIT_PERFORMANCE", "MFE_MAE", "FUTURE_LABELS", "PROTECTED_180_TO_282", "FRESH_OOS"]) assert.ok(manifest.prohibited.includes(forbidden));
  assert.ok(Object.values(manifest.safety).every((value) => value === false));
});
