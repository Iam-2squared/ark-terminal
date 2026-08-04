import test from "node:test";
import assert from "node:assert/strict";

import {
  AIConsensusEngineV3,
  buildAIConsensus,
  compareConsensus,
} from "../market-intelligence/ai-consensus-engine-v3.js";

const NOW =
  "2026-08-04T07:00:00.000Z";

function bullishSignals() {
  return [
    {
      id:
        "technical",

      direction:
        "BUY",

      confidence:
        82,

      reliability:
        80,

      risk:
        25,

      weight:
        1.2,

      score:
        75,
    },

    {
      id:
        "regime",

      direction:
        "BUY",

      confidence:
        78,

      reliability:
        85,

      risk:
        20,

      weight:
        1,

      score:
        70,
    },

    {
      id:
        "breadth",

      direction:
        "BUY",

      confidence:
        72,

      reliability:
        75,

      risk:
        30,

      weight:
        0.9,

      score:
        60,
    },
  ];
}

test(
  "Builds bullish AI consensus",
  () => {
    const result =
      buildAIConsensus({
        signals:
          bullishSignals(),

        timestamp:
          NOW,
      });

    assert.equal(
      result.status,
      "READY",
    );

    assert.equal(
      result.decision,
      "BUY",
    );

    assert.ok(
      result.confidence >
      55,
    );

    assert.ok(
      result.consensusScore >
      20,
    );
  },
);

test(
  "Builds bearish AI consensus",
  () => {
    const signals =
      bullishSignals().map(
        (
          signal,
        ) => ({
          ...signal,

          direction:
            "SELL",

          score:
            -Math.abs(
              signal.score,
            ),
        }),
      );

    const result =
      buildAIConsensus({
        signals,

        timestamp:
          NOW,
      });

    assert.equal(
      result.decision,
      "SELL",
    );

    assert.ok(
      result.consensusScore <
      -20,
    );
  },
);

test(
  "Blocks low agreement",
  () => {
    const result =
      buildAIConsensus({
        signals: [
          {
            direction:
              "BUY",

            confidence:
              80,

            reliability:
              80,

            risk:
              20,

            score:
              70,
          },

          {
            direction:
              "SELL",

            confidence:
              80,

            reliability:
              80,

            risk:
              20,

            score:
              -70,
          },

          {
            direction:
              "HOLD",

            confidence:
              80,

            reliability:
              80,

            risk:
              20,

            score:
              0,
          },
        ],

        timestamp:
          NOW,

        minimumAgreement:
          50,
      });

    assert.equal(
      result.decision,
      "WAIT",
    );

    assert.ok(
      result.blockers.includes(
        "LOW_AGREEMENT",
      ),
    );
  },
);

test(
  "Applies sell veto to buy consensus",
  () => {
    const result =
      buildAIConsensus({
        signals: [
          ...bullishSignals(),

          {
            id:
              "risk-control",

            direction:
              "SELL",

            confidence:
              90,

            reliability:
              95,

            risk:
              10,

            weight:
              0.2,

            score:
              -10,

            veto:
              true,
          },
        ],

        timestamp:
          NOW,

        minimumAgreement:
          40,
      });

    assert.equal(
      result.decision,
      "WAIT",
    );

    assert.ok(
      result.blockers.includes(
        "SELL_VETO",
      ),
    );
  },
);

test(
  "Blocks excessive average risk",
  () => {
    const result =
      buildAIConsensus({
        signals:
          bullishSignals().map(
            (
              signal,
            ) => ({
              ...signal,

              risk:
                95,
            }),
          ),

        timestamp:
          NOW,
      });

    assert.equal(
      result.status,
      "BLOCKED",
    );

    assert.equal(
      result.decision,
      "WAIT",
    );

    assert.ok(
      result.blockers.includes(
        "EXCESSIVE_RISK",
      ),
    );
  },
);

test(
  "Returns insufficient data safely",
  () => {
    const result =
      buildAIConsensus({
        signals: [
          {
            direction:
              "BUY",
          },
        ],

        timestamp:
          NOW,
      });

    assert.equal(
      result.status,
      "INSUFFICIENT_DATA",
    );

    assert.equal(
      result.decision,
      "WAIT",
    );
  },
);

test(
  "Compares consensus changes",
  () => {
    const comparison =
      compareConsensus({
        previous: {
          decision:
            "BUY",

          confidence:
            70,

          consensusScore:
            45,
        },

        current: {
          decision:
            "SELL",

          confidence:
            60,

          consensusScore:
            -35,
        },
      });

    assert.equal(
      comparison.changed,
      true,
    );

    assert.equal(
      comparison
        .decisionChanged,
      true,
    );

    assert.equal(
      comparison
        .currentDecision,
      "SELL",
    );
  },
);

test(
  "Consensus engine stores history",
  () => {
    const engine =
      new AIConsensusEngineV3();

    engine.evaluate({
      signals:
        bullishSignals(),

      timestamp:
        NOW,
    });

    assert.equal(
      engine
        .getHistory()
        .length,
      1,
    );

    assert.equal(
      engine.latest()
        .decision,
      "BUY",
    );

    engine.reset();

    assert.equal(
      engine
        .getHistory()
        .length,
      0,
    );
  },
);

test(
  "Validates timestamp",
  () => {
    assert.throws(
      () =>
        buildAIConsensus({
          signals:
            bullishSignals(),

          timestamp:
            "invalid-date",
        }),

      /timestamp is invalid/,
    );
  },
);