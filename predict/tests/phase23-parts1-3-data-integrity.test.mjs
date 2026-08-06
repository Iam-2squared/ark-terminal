import assert from "node:assert/strict";
import test from "node:test";

import { buildTradingCalendar } from "../data-integrity/trading-calendar.js";
import { buildCorporateActionLedger } from "../data-integrity/corporate-actions.js";
import { assertPointInTimeSafe, selectPointInTimeRecords } from "../data-integrity/point-in-time.js";

test("trading calendar handles weekends holidays closures and half days", () => {
  const calendar = buildTradingCalendar({
    holidays: ["2026-01-01"],
    specialClosures: ["2026-01-02"],
    halfDays: ["2026-01-05"],
  });

  assert.equal(calendar.isTradingDay("2026-01-03"), false);
  assert.equal(calendar.isTradingDay("2026-01-01"), false);
  assert.equal(calendar.isTradingDay("2026-01-02"), false);
  assert.equal(calendar.sessionType("2026-01-05"), "HALF_DAY");
  assert.equal(calendar.nextTradingDay("2026-01-01"), "2026-01-05");
});

test("corporate action ledger adjusts split prices and audits mismatches", () => {
  const ledger = buildCorporateActionLedger([
    { type: "SPLIT", effectiveDate: "2026-06-01", ratio: 2 },
  ]);

  assert.equal(
    ledger.adjustPrice({ symbol: "7203", price: 1000, date: "2026-05-29", throughDate: "2026-06-02" }),
    500,
  );
  assert.equal(
    ledger.auditRow({ symbol: "7203", date: "2026-05-29", close: 1000, adjustedClose: 500 }, "2026-06-02").valid,
    true,
  );
  assert.deepEqual(
    ledger.auditRow({ symbol: "7203", date: "2026-05-29", close: 1000, adjustedClose: 700 }, "2026-06-02").issues,
    ["ADJUSTED_CLOSE_MISMATCH"],
  );
});

test("point-in-time selector rejects future records and blocks evaluation", () => {
  const result = selectPointInTimeRecords([
    {
      key: "sector:7203",
      symbol: "7203",
      field: "sector",
      value: "Automobiles",
      effectiveAt: "2026-01-01T00:00:00Z",
      availableAt: "2026-01-02T00:00:00Z",
    },
    {
      key: "sector:7203",
      symbol: "7203",
      field: "sector",
      value: "Mobility",
      effectiveAt: "2026-01-01T00:00:00Z",
      availableAt: "2026-02-01T00:00:00Z",
    },
  ], "2026-01-15T00:00:00Z");

  assert.equal(result.rows.length, 1);
  assert.equal(result.rows[0].value, "Automobiles");
  assert.equal(result.futureLeakDetected, true);
  assert.equal(result.safety.evaluationAllowed, false);
  assert.throws(() => assertPointInTimeSafe(result), /POINT_IN_TIME_FUTURE_LEAK_DETECTED/);
});

test("point-in-time selector passes when all records were available", () => {
  const result = selectPointInTimeRecords([
    {
      key: "market-cap:7203",
      symbol: "7203",
      field: "marketCap",
      value: 1,
      effectiveAt: "2026-01-01T00:00:00Z",
      availableAt: "2026-01-01T09:00:00Z",
    },
  ], "2026-01-02T00:00:00Z");

  assert.equal(result.futureLeakDetected, false);
  assert.equal(result.safety.evaluationAllowed, true);
  assert.equal(assertPointInTimeSafe(result), true);
  assert.equal(result.safety.brokerWriteAllowed, false);
});
