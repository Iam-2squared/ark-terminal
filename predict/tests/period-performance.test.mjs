import test from "node:test";
import assert from "node:assert/strict";

import {
  aggregatePeriodPerformance,
} from "../analysis/period-performance.js";

const rows = [
  {
    timestamp: "2026-08-01T01:00:00.000Z",
    symbol: "7203.T",
    signal: "BUY",
    confidence: 0.8,
    correct: true,
    profit: 10,
    walkForwardWindow: "window-1",
  },
  {
    timestamp: "2026-08-02T01:00:00.000Z",
    symbol: "7203.T",
    signal: "SELL",
    confidence: 0.5,
    correct: false,
    profit: -3,
    walkForwardWindow: "window-1",
  },
  {
    timestamp: "2026-09-01T01:00:00.000Z",
    symbol: "9984.T",
    signal: "BUY",
    confidence: 0.9,
    correct: true,
    profit: 5,
    walkForwardWindow: "window-2",
  },
];

test("Period performance groups dashboard rows", () => {
  const result = aggregatePeriodPerformance(rows);

  assert.equal(result.overall.total, 3);
  assert.equal(
    result.bySymbol["7203.T"].total,
    2,
  );
  assert.equal(result.bySignal.BUY.total, 2);
  assert.equal(
    result.byWalkForwardWindow["window-1"].total,
    2,
  );
  assert.equal(result.metadata.datedRows, 3);
});

test("Period performance creates daily and monthly groups", () => {
  const result = aggregatePeriodPerformance(rows);

  assert.equal(
    result.daily["2026-08-01"].total,
    1,
  );
  assert.equal(
    result.monthly["2026-08"].total,
    2,
  );
  assert.equal(
    result.monthly["2026-09"].total,
    1,
  );
});

test("Period performance tracks undated rows", () => {
  const result = aggregatePeriodPerformance([
    { symbol: "A", profit: 1 },
  ]);

  assert.equal(result.metadata.totalRows, 1);
  assert.equal(result.metadata.datedRows, 0);
  assert.equal(result.metadata.undatedRows, 1);
});

test("Period performance validates rows", () => {
  assert.throws(
    () => aggregatePeriodPerformance(null),
    {
      name: "TypeError",
    },
  );
});
