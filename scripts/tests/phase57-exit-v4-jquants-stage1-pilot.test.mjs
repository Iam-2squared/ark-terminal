import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  classifyMinuteAbsence,
  classifyTickBulkScope,
  compareTimestampHypotheses,
  parseCsvLine,
  tierFromQuality,
} from "../lib/phase57-jquants-stage1-quality.mjs";
import { aggregateJquantsMinutesToFiveMinuteBars } from "../lib/phase57-selector-jquants-minute.mjs";

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

test("monthly Tick transport is detected before any raw download", () => {
  const result = classifyTickBulkScope([{ Key: "equities/trades/historical/2025/equities_trades_202508.csv.gz", Size: 10 }], "2025-08-27");
  assert.equal(result.scope, "MONTH");
});

function minute(Time, O) {
  return { Date: "2025-08-27", Time, Code: "86970", O, H: O + 1, L: O - 1, C: O, Vo: 10, Va: O * 10 };
}

test("5m aggregation is causal, no-fill, and lunch-separated", () => {
  const contract = { sourceMinuteTimestampMeaning: "BAR_START_HALF_OPEN_INCLUDING_TERMINAL_AUCTION_MINUTES" };
  const prefix = [minute("09:00", 100), minute("09:01", 101), minute("09:03", 103), minute("09:04", 104)];
  const beforeFuture = aggregateJquantsMinutesToFiveMinuteBars(prefix, contract)[0];
  const afterFuture = aggregateJquantsMinutesToFiveMinuteBars([...prefix, minute("09:05", 999)], contract)[0];
  assert.deepEqual(beforeFuture, afterFuture);
  assert.equal(beforeFuture.observedMinuteCount, 4);
  assert.equal(beforeFuture.missingNoTradeMinuteCount, 1);
  assert.equal(beforeFuture.fabricatedMinuteCount, 0);

  const lunch = aggregateJquantsMinutesToFiveMinuteBars([minute("11:29", 110), minute("12:30", 120)], contract);
  assert.equal(lunch.length, 2);
  assert.notEqual(lunch[0].sessionSegment, lunch[1].sessionSegment);
  assert.equal(lunch[1].timestamp, "2025-08-27T03:30:00.000Z");
});

test("precommit stays outcome blind and uses exposed PURGE sessions only", () => {
  const manifest = JSON.parse(fs.readFileSync("predict/research/phase57-exit-v4-jquants-stage1-precommit-v1.json", "utf8"));
  assert.deepEqual(manifest.sessions, ["2025-08-27", "2025-10-09", "2025-11-25"]);
  assert.equal(manifest.sessionClassification, "ALREADY_EXPOSED_PURGE_QUALITY_EVIDENCE");
  for (const forbidden of ["EXIT_PERFORMANCE", "MFE_MAE", "FUTURE_LABELS", "PROTECTED_180_TO_282", "FRESH_OOS"]) assert.ok(manifest.prohibited.includes(forbidden));
  assert.ok(Object.values(manifest.safety).every((value) => value === false));
});

test("final result stops with all protected, outcome, and safety guards closed", () => {
  const result = JSON.parse(fs.readFileSync("predict/research/phase57-exit-v4-jquants-stage1-result-v1.json", "utf8"));
  assert.equal(result.stage1Gate, "STOP_DATA_SOURCE_NOT_READY");
  assert.equal(result.evidence.bulkGetCalled, false);
  assert.equal(result.evidence.tickRawDownloadStarted, false);
  assert.equal(result.accessLedger.newSealedSessionsOpened, 0);
  assert.equal(result.accessLedger.exitOutcomeAccess, 0);
  assert.equal(result.accessLedger.futureLabelAccess, 0);
  assert.equal(result.accessLedger.protected180To282Opened, 0);
  assert.equal(result.accessLedger.freshValidationOpened, 0);
  assert.equal(result.accessLedger.freshOosOpened, 0);
  assert.equal(result.datasetEligibility.FULL_REPLAY_ELIGIBLE.sessions, 0);
  assert.ok(result.pilotClassification.every((row) => row.tier === "BLOCKED"));
  assert.ok(Object.values(result.safety).every((value) => value === false));
});

test("Hybrid and all ten MSH features remain explicit and unfitted", () => {
  const result = JSON.parse(fs.readFileSync("predict/research/phase57-exit-v4-jquants-stage1-result-v1.json", "utf8"));
  assert.equal(result.hybridReplay.verdict, "PARTIAL");
  assert.equal(result.mshEntryReplay.verdict, "PARTIAL");
  assert.equal(result.mshEntryReplay.threshold, "STRICTLY_GREATER_THAN_0.60");
  assert.deepEqual(result.mshEntryReplay.features.map((row) => row.feature), [
    "directionalReturnFromOpenPct", "directionalVwapDistancePct", "directionalMomentum3Pct",
    "directionalMomentumAccelerationPct", "directionalPullback6Pct", "relativeVolume5",
    "minutesSinceFirstSelection", "hybridReciprocalRank", "priorSelectionCount", "direction",
  ]);
  assert.ok(result.mshEntryReplay.features.every((row) => row.goldenParity === "0_OF_3_NOT_RUN"));
});

test("adjustment and unknown absence fail closed", () => {
  const result = JSON.parse(fs.readFileSync("predict/research/phase57-exit-v4-jquants-stage1-result-v1.json", "utf8"));
  assert.match(result.quality.adjustment, /^FAIL/);
  const unknown = result.missingSparseSemantics.find((row) => row.condition === "UNKNOWN");
  assert.equal(unknown.detectable, "YES");
  assert.match(unknown.replayTreatment, /NO_OBSERVATION/);
  assert.match(unknown.replayTreatment, /NO_STATE_ADVANCEMENT/);
  assert.equal(aggregateJquantsMinutesToFiveMinuteBars([], { sourceMinuteTimestampMeaning: "BAR_START_HALF_OPEN_INCLUDING_TERMINAL_AUCTION_MINUTES" }).length, 0);
});
