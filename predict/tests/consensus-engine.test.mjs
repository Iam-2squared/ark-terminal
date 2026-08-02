import assert from "node:assert/strict";
import test from "node:test";

import {
  buildConsensus,
  buildConsensusReport,
} from "../analysis/consensus-engine.js";

test(
  "Strong buy consensus",
  () => {
    const result =
      buildConsensus({
        engines: [
          {
            name: "technical",
            result: {
              action: "STRONG BUY",
              score: 92,
              confidence: 90,
            },
          },
          {
            name: "macro",
            result: {
              action: "BUY",
              score: 82,
              confidence: 80,
            },
          },
          {
            name: "learning",
            result: {
              action: "STRONG BUY",
              score: 90,
              confidence: 88,
            },
          },
        ],
      });

    assert.equal(
      result.ready,
      true,
    );

    assert.equal(
      result.action,
      "STRONG BUY",
    );

    assert.ok(
      result.confidence > 70,
    );

    assert.equal(
      result.engineCount,
      3,
    );
  },
);

test(
  "Engine weights affect consensus score",
  () => {
    const result =
      buildConsensus({
        engines: [
          {
            name: "strong",
            weight: 3,
            result: {
              action: "BUY",
              score: 85,
              confidence: 90,
            },
          },
          {
            name: "weak",
            weight: 1,
            result: {
              action: "SELL",
              score: 10,
              confidence: 70,
            },
          },
        ],
      });

    assert.ok(
      result.score > 60,
    );

    assert.ok(
      [
        "BUY",
        "WATCH",
      ].includes(
        result.action,
      ),
    );
  },
);

test(
  "Insufficient engines are rejected",
  () => {
    const result =
      buildConsensus({
        engines: [
          {
            name: "technical",
            result: {
              score: 80,
            },
          },
        ],

        minimumEngines: 2,
      });

    assert.equal(
      result.ready,
      false,
    );

    assert.equal(
      result.reason,
      "insufficient_engines",
    );
  },
);

test(
  "Consensus report includes symbol and summary",
  () => {
    const report =
      buildConsensusReport({
        symbol: "7203.T",

        engines: [
          {
            name: "technical",
            result: {
              action: "BUY",
              score: 80,
              confidence: 85,
            },
          },
        ],
      });

    assert.equal(
      report.symbol,
      "7203.T",
    );

    assert.equal(
      report.version,
      "consensus-engine-v1",
    );

    assert.ok(
      report.summary.includes(
        "BUY",
      ),
    );
  },
);