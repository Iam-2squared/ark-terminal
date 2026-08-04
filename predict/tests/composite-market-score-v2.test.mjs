import test from "node:test";
import assert from "node:assert/strict";

import {
  CompositeMarketScoreV2Engine,
  calculateCompositeMarketScoreV2,
} from "../market-intelligence/composite-market-score-v2.js";

const NOW =
  Date.parse(
    "2026-08-03T00:00:00.000Z",
  );

function report(
  score,
  confidence = 100,
  coverage = 100,
) {
  return {
    score,
    confidence,
    coverage,
  };
}

test(
  "Composite Market Score v2 detects risk-on conditions",
  () => {
    const result =
      calculateCompositeMarketScoreV2({
        breadth:
          report(82),

        liquidity:
          report(74),

        sectorStrength:
          report(78),

        sectorRotation:
          report(72),

        volatility:
          report(68),

        news:
          report(64),

        now:
          () => NOW,
      });

    assert.equal(
      result.version,
      "composite-market-score-v2",
    );

    assert.equal(
      result.regime,
      "RISK_ON",
    );

    assert.ok(
      result.score >= 65,
    );

    assert.equal(
      result.coverage,
      100,
    );

    assert.equal(
      result.disagreement,
      "LOW",
    );
  },
);

test(
  "Composite Market Score v2 detects risk-off conditions",
  () => {
    const result =
      calculateCompositeMarketScoreV2({
        breadth:
          report(18),

        liquidity:
          report(28),

        sectorStrength:
          report(24),

        sectorRotation:
          report(20),

        volatility:
          report(30),

        news:
          report(35),

        now:
          () => NOW,
      });

    assert.equal(
      result.regime,
      "RISK_OFF",
    );

    assert.ok(
      result.score <= 35,
    );

    assert.match(
      result.sentiment,
      /BEARISH/,
    );
  },
);

test(
  "Composite Market Score v2 lowers confidence when components disagree",
  () => {
    const result =
      calculateCompositeMarketScoreV2({
        breadth:
          report(95),

        liquidity:
          report(10),

        sectorStrength:
          report(90),

        sectorRotation:
          report(15),

        volatility:
          report(85),

        news:
          report(20),

        now:
          () => NOW,
      });

    assert.equal(
      result.regime,
      "FRAGMENTED",
    );

    assert.equal(
      result.disagreement,
      "HIGH",
    );

    assert.ok(
      result.confidence < 80,
    );

    assert.ok(
      result.dispersion >= 25,
    );
  },
);

test(
  "Composite Market Score v2 handles missing components",
  () => {
    const result =
      calculateCompositeMarketScoreV2({
        breadth:
          report(70),

        sectorStrength:
          report(60),

        now:
          () => NOW,
      });

    assert.equal(
      result.diagnostics.availableCount,
      2,
    );

    assert.equal(
      result.coverage,
      33.33,
    );

    assert.ok(
      result.confidence < 50,
    );

    assert.equal(
      result.components[1].available,
      false,
    );
  },
);

test(
  "Composite Market Score v2 returns unknown without data",
  () => {
    const result =
      calculateCompositeMarketScoreV2({
        now:
          () => NOW,
      });

    assert.equal(
      result.score,
      null,
    );

    assert.equal(
      result.sentiment,
      "UNKNOWN",
    );

    assert.equal(
      result.regime,
      "UNKNOWN",
    );

    assert.equal(
      result.confidence,
      0,
    );
  },
);

test(
  "Composite Market Score v2 engine is deterministic",
  () => {
    const engine =
      new CompositeMarketScoreV2Engine({
        now:
          () => NOW,
      });

    const input = {
      breadth:
        report(80),

      liquidity:
        report(60),

      sectorStrength:
        report(55),

      sectorRotation:
        report(50),
    };

    assert.deepEqual(
      engine.calculate(input),
      engine.calculate(input),
    );
  },
);

test(
  "Composite Market Score v2 validates clock and timestamp",
  () => {
    assert.throws(
      () =>
        calculateCompositeMarketScoreV2({
          now:
            NOW,
        }),
      /clock must be a function/,
    );

    assert.throws(
      () =>
        calculateCompositeMarketScoreV2({
          timestamp:
            "invalid",
        }),
      /timestamp is invalid/,
    );
  },
);