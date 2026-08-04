import test from "node:test";
import assert from "node:assert/strict";

import {
  CapacityPlannerV2,
  planTradingCapacity,
} from "../trading/capacity-planner-v2.js";

function createCandidates() {
  return [
    {
      symbol:
        "AAA",

      sector:
        "Technology",

      side:
        "BUY",

      price:
        100,

      averageDailyVolume:
        100000,

      requestedQuantity:
        100,

      score:
        90,

      confidence:
        85,

      liquidityScore:
        95,

      volatility:
        2,
    },

    {
      symbol:
        "BBB",

      sector:
        "Finance",

      side:
        "BUY",

      price:
        200,

      averageDailyVolume:
        50000,

      requestedQuantity:
        50,

      score:
        70,

      confidence:
        75,

      liquidityScore:
        80,

      volatility:
        3,
    },
  ];
}

test(
  "Capacity Planner v2 creates executable plans",
  () => {
    const result =
      planTradingCapacity({
        candidates:
          createCandidates(),

        capital:
          100000,

        maximumPositionWeight:
          0.3,

        maximumGrossExposure:
          0.8,
      });

    assert.equal(
      result.version,
      "capacity-planner-v2",
    );

    assert.equal(
      result.ready,
      true,
    );

    assert.equal(
      result.approved,
      true,
    );

    assert.equal(
      result.candidateCount,
      2,
    );

    assert.ok(
      result.approvedCount >= 1,
    );
  },
);

test(
  "Capacity Planner v2 limits each position by capital",
  () => {
    const result =
      planTradingCapacity({
        candidates: [
          {
            symbol:
              "AAA",

            price:
              100,

            averageDailyVolume:
              1000000,

            requestedQuantity:
              10000,

            score:
              90,

            confidence:
              90,
          },
        ],

        capital:
          100000,

        maximumPositionWeight:
          0.2,
      });

    assert.ok(
      result.plans[0].allocatedValue <=
      20000.000001,
    );
  },
);

test(
  "Capacity Planner v2 limits illiquid securities",
  () => {
    const result =
      planTradingCapacity({
        candidates: [
          {
            symbol:
              "LOWVOL",

            price:
              100,

            averageDailyVolume:
              1000,

            requestedQuantity:
              10000,

            liquidityScore:
              30,

            volatility:
              10,

            score:
              80,

            confidence:
              80,
          },
        ],

        capital:
          1000000,

        baseParticipationRate:
          0.1,

        holdingDays:
          1,
      });

    assert.ok(
      result.plans[0].maximumQuantity <
      1000,
    );

    assert.ok(
      result.plans[0].constraints.includes(
        "LIQUIDITY_LIMIT",
      ) ||
      result.plans[0].constraints.includes(
        "MARKET_IMPACT_LIMIT",
      ),
    );
  },
);

test(
  "Capacity Planner v2 respects gross exposure",
  () => {
    const result =
      planTradingCapacity({
        candidates:
          createCandidates(),

        capital:
          100000,

        maximumGrossExposure:
          0.25,

        maximumPositionWeight:
          0.5,
      });

    assert.ok(
      result.summary.allocatedCapital <=
      25000.000001,
    );

    assert.ok(
      result.summary.grossExposure <=
      0.250001,
    );
  },
);

test(
  "Capacity Planner v2 prioritizes higher opportunity score",
  () => {
    const result =
      planTradingCapacity({
        candidates: [
          {
            symbol:
              "HIGH",

            price:
              100,

            averageDailyVolume:
              100000,

            requestedQuantity:
              100,

            score:
              95,

            confidence:
              90,

            liquidityScore:
              90,
          },

          {
            symbol:
              "LOW",

            price:
              100,

            averageDailyVolume:
              100000,

            requestedQuantity:
              100,

            score:
              40,

            confidence:
              40,

            liquidityScore:
              90,
          },
        ],

        capital:
          10000,

        maximumGrossExposure:
          1,

        maximumPositionWeight:
          1,
      });

    assert.equal(
      result.plans[0].symbol,
      "HIGH",
    );
  },
);

test(
  "Capacity Planner v2 respects lot size",
  () => {
    const result =
      planTradingCapacity({
        candidates: [
          {
            symbol:
              "AAA",

            price:
              123,

            averageDailyVolume:
              100000,

            requestedQuantity:
              155,

            score:
              80,

            confidence:
              80,
          },
        ],

        capital:
          100000,

        lotSize:
          100,

        maximumPositionWeight:
          1,
      });

    assert.equal(
      result.plans[0].recommendedQuantity %
      100,
      0,
    );
  },
);

test(
  "Capacity Planner v2 handles empty candidates",
  () => {
    const result =
      planTradingCapacity({
        candidates:
          [],

        capital:
          100000,
      });

    assert.equal(
      result.ready,
      false,
    );

    assert.equal(
      result.approved,
      false,
    );

    assert.deepEqual(
      result.plans,
      [],
    );
  },
);

test(
  "Capacity Planner v2 rejects invalid capital",
  () => {
    assert.throws(
      () =>
        planTradingCapacity({
          capital:
            0,
        }),

      /capital must be greater than zero/,
    );
  },
);

test(
  "Capacity Planner v2 class is deterministic",
  () => {
    const engine =
      new CapacityPlannerV2({
        capital:
          100000,

        maximumPositionWeight:
          0.25,
      });

    const candidates =
      createCandidates();

    assert.deepEqual(
      engine.plan(candidates),
      engine.plan(candidates),
    );
  },
);