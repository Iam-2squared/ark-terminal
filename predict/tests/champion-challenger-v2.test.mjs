import test from "node:test";
import assert from "node:assert/strict";

import {
  ChampionChallengerV2,
  approveChallengerPromotion,
  evaluateChampionChallenger,
} from "../learning/champion-challenger-v2.js";

function createModels() {
  return {
    champion: {
      id:
        "ark-short-term",

      version:
        "2.0.0",

      family:
        "ENSEMBLE",
    },

    challenger: {
      id:
        "ark-short-term",

      version:
        "3.0.0",

      family:
        "ENSEMBLE",
    },
  };
}

function createWinningRecords(
  count = 200,
) {
  return Array.from(
    {
      length:
        count,
    },
    (
      _,
      index,
    ) => {
      const actualReturn =
        index % 10 < 7
          ? 1.5
          : -1;

      const actualDirection =
        actualReturn > 0
          ? "BUY"
          : "SELL";

      return {
        id:
          `record-${index}`,

        timestamp:
          new Date(
            Date.parse(
              "2026-01-01T00:00:00.000Z",
            ) +
            index *
            86400000,
          ).toISOString(),

        actualReturn,

        champion: {
          direction:
            index % 10 < 6
              ? actualDirection
              : actualDirection === "BUY"
                ? "SELL"
                : "BUY",

          confidence:
            68,
        },

        challenger: {
          direction:
            index % 10 < 8
              ? actualDirection
              : actualDirection === "BUY"
                ? "SELL"
                : "BUY",

          confidence:
            75,
        },
      };
    },
  );
}

test(
  "Champion challenger promotes superior challenger",
  () => {
    const models =
      createModels();

    const result =
      evaluateChampionChallenger({
        ...models,

        records:
          createWinningRecords(),

        minimumSamples:
          100,

        minimumAccuracyImprovement:
          1,

        minimumWinProbability:
          60,

        minimumPromotionScore:
          80,

        requireHumanApproval:
          false,
      });

    assert.equal(
      result.version,
      "champion-challenger-v2",
    );

    assert.equal(
      result.ready,
      true,
    );

    assert.equal(
      result.decision,
      "PROMOTE_CHALLENGER",
    );

    assert.equal(
      result.approved,
      true,
    );

    assert.deepEqual(
      result.blockers,
      [],
    );
  },
);

test(
  "Champion challenger requires human approval by default",
  () => {
    const result =
      evaluateChampionChallenger({
        ...createModels(),

        records:
          createWinningRecords(),

        minimumWinProbability:
          60,

        minimumPromotionScore:
          80,
      });

    assert.equal(
      result.decision,
      "PROMOTE_CHALLENGER",
    );

    assert.equal(
      result.humanApprovalRequired,
      true,
    );

    assert.equal(
      result.approved,
      false,
    );
  },
);

test(
  "Champion challenger continues shadow with too few records",
  () => {
    const result =
      evaluateChampionChallenger({
        ...createModels(),

        records:
          createWinningRecords(
            20,
          ),

        minimumSamples:
          100,
      });

    assert.equal(
      result.decision,
      "CONTINUE_SHADOW",
    );

    assert.ok(
      result.blockers.includes(
        "MINIMUM_SAMPLES",
      ),
    );
  },
);

test(
  "Champion challenger rejects risky challenger",
  () => {
    const records =
      createWinningRecords();

    for (
      let index = 160;
      index < 200;
      index += 1
    ) {
      records[index] = {
        ...records[index],

        actualReturn:
          -8,

        champion: {
          direction:
            "SELL",

          confidence:
            70,
        },

        challenger: {
          direction:
            "BUY",

          confidence:
            95,
        },
      };
    }

    const result =
      evaluateChampionChallenger({
        ...createModels(),

        records,

        minimumAccuracyImprovement:
          -100,

        minimumReturnImprovement:
          -100,

        maximumDrawdownRegression:
          2,

        minimumWinProbability:
          0,
      });

    assert.equal(
      result.decision,
      "REJECT_CHALLENGER",
    );

    assert.ok(
      result.blockers.includes(
        "DRAWDOWN_REGRESSION",
      ),
    );
  },
);

test(
  "Champion challenger bootstrap is deterministic",
  () => {
    const input = {
      ...createModels(),

      records:
        createWinningRecords(),

      bootstrapIterations:
        500,

      bootstrapSeed:
        123,

      minimumWinProbability:
        60,
    };

    const first =
      evaluateChampionChallenger(
        input,
      );

    const second =
      evaluateChampionChallenger(
        input,
      );

    assert.deepEqual(
      first.bootstrap,
      second.bootstrap,
    );
  },
);

test(
  "Champion challenger handles no records",
  () => {
    const result =
      evaluateChampionChallenger({
        ...createModels(),

        records:
          [],
      });

    assert.equal(
      result.ready,
      false,
    );

    assert.equal(
      result.reason,
      "NO_COMPARISON_RECORDS",
    );
  },
);

test(
  "Champion challenger rejects identical model version",
  () => {
    assert.throws(
      () =>
        evaluateChampionChallenger({
          champion: {
            id:
              "same",

            version:
              "1",
          },

          challenger: {
            id:
              "same",

            version:
              "1",
          },
        }),

      /must be different models/,
    );
  },
);

test(
  "Challenger promotion records approver",
  () => {
    const evaluation =
      evaluateChampionChallenger({
        ...createModels(),

        records:
          createWinningRecords(),

        minimumWinProbability:
          60,

        minimumPromotionScore:
          80,
      });

    const approval =
      approveChallengerPromotion({
        evaluation,

        approvedBy:
          "human-reviewer",

        note:
          "Shadow validation complete.",
      });

    assert.equal(
      approval.promoted,
      true,
    );

    assert.equal(
      approval.newChampion.version,
      "3.0.0",
    );

    assert.equal(
      approval.approvedBy,
      "human-reviewer",
    );
  },
);

test(
  "Challenger promotion rejects non-promotable result",
  () => {
    const evaluation =
      evaluateChampionChallenger({
        ...createModels(),

        records:
          createWinningRecords(
            10,
          ),

        minimumSamples:
          100,
      });

    const approval =
      approveChallengerPromotion({
        evaluation,

        approvedBy:
          "reviewer",
      });

    assert.equal(
      approval.promoted,
      false,
    );

    assert.equal(
      approval.reason,
      "CHALLENGER_NOT_PROMOTABLE",
    );
  },
);

test(
  "Champion challenger class is deterministic",
  () => {
    const engine =
      new ChampionChallengerV2({
        minimumWinProbability:
          60,

        minimumPromotionScore:
          80,

        requireHumanApproval:
          false,
      });

    const input = {
      ...createModels(),

      records:
        createWinningRecords(),
    };

    const first =
      engine.evaluate(
        input,
      );

    const second =
      engine.evaluate(
        input,
      );

    assert.equal(
      first.decision,
      second.decision,
    );

    assert.equal(
      first.comparisonScore,
      second.comparisonScore,
    );

    assert.deepEqual(
      first.bootstrap,
      second.bootstrap,
    );
  },
);