import test from "node:test";
import assert from "node:assert/strict";

import {
  ModelPromotionGateV2,
  approveModelPromotion,
  evaluateModelPromotion,
} from "../learning/model-promotion-gate-v2.js";

function healthyInput() {
  return {
    candidate: {
      id:
        "ark-short-term-v3",

      version:
        "3.0.0",

      family:
        "ENSEMBLE",
    },

    metrics: {
      accuracy:
        71,

      confidenceCalibrationError:
        8,

      profitFactor:
        1.65,

      maximumDrawdown:
        9,

      averageReturn:
        1.4,

      sampleCount:
        500,

      stabilityScore:
        78,

      monteCarloSuccessRate:
        74,
    },

    benchmark: {
      accuracy:
        68,

      averageReturn:
        1.1,

      maximumDrawdown:
        10,
    },

    drift: {
      ready:
        true,

      driftDetected:
        false,

      driftScore:
        12,

      driftLevel:
        "LOW",

      recommendation: {
        allowPromotion:
          true,
      },
    },

    learning: {
      ready:
        true,

      recommendation: {
        action:
          "PROMOTE",
      },

      overall: {
        performanceScore:
          76,

        sampleCount:
          500,
      },
    },
  };
}

test(
  "Model promotion gate promotes healthy candidate",
  () => {
    const result =
      evaluateModelPromotion({
        ...healthyInput(),

        requireHumanApproval:
          false,

        minimumPromotionScore:
          80,
      });

    assert.equal(
      result.version,
      "model-promotion-gate-v2",
    );

    assert.equal(
      result.decision,
      "PROMOTE",
    );

    assert.equal(
      result.approved,
      true,
    );

    assert.deepEqual(
      result.blockers,
      [],
    );

    assert.ok(
      result.promotionScore >=
      80,
    );
  },
);

test(
  "Model promotion gate requires human approval by default",
  () => {
    const result =
      evaluateModelPromotion(
        healthyInput(),
      );

    assert.equal(
      result.decision,
      "PROMOTE",
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
  "Model promotion gate blocks low accuracy",
  () => {
    const input =
      healthyInput();

    input.metrics.accuracy =
      48;

    const result =
      evaluateModelPromotion({
        ...input,

        requireHumanApproval:
          false,
      });

    assert.equal(
      result.decision,
      "HOLD",
    );

    assert.ok(
      result.blockers.includes(
        "ACCURACY",
      ),
    );
  },
);

test(
  "Model promotion gate requests retraining during drift",
  () => {
    const input =
      healthyInput();

    input.drift = {
      ready:
        true,

      driftDetected:
        true,

      driftScore:
        82,

      driftLevel:
        "CRITICAL",

      recommendation: {
        allowPromotion:
          false,
      },
    };

    const result =
      evaluateModelPromotion(
        input,
      );

    assert.equal(
      result.decision,
      "RETRAIN",
    );

    assert.equal(
      result.reason,
      "CONCEPT_DRIFT_BLOCKED_PROMOTION",
    );

    assert.ok(
      result.blockers.includes(
        "CONCEPT_DRIFT",
      ),
    );
  },
);

test(
  "Model promotion gate checks benchmark regression",
  () => {
    const input =
      healthyInput();

    input.metrics.maximumDrawdown =
      18;

    input.benchmark.maximumDrawdown =
      8;

    const result =
      evaluateModelPromotion({
        ...input,

        maximumDrawdown:
          25,

        maximumDrawdownRegression:
          5,

        requireHumanApproval:
          false,
      });

    assert.equal(
      result.decision,
      "HOLD",
    );

    assert.ok(
      result.blockers.includes(
        "DRAWDOWN_REGRESSION",
      ),
    );
  },
);

test(
  "Model promotion gate can require benchmark",
  () => {
    const input =
      healthyInput();

    input.benchmark = {};

    const result =
      evaluateModelPromotion({
        ...input,

        requireBenchmark:
          true,
      });

    assert.equal(
      result.decision,
      "HOLD",
    );

    assert.ok(
      result.blockers.includes(
        "BENCHMARK_REQUIRED",
      ),
    );
  },
);

test(
  "Model promotion approval records approver",
  () => {
    const evaluation =
      evaluateModelPromotion(
        healthyInput(),
      );

    const approval =
      approveModelPromotion({
        evaluation,

        approvedBy:
          "human-reviewer",

        note:
          "Walk-forward review complete.",
      });

    assert.equal(
      approval.approved,
      true,
    );

    assert.equal(
      approval.promoted,
      true,
    );

    assert.equal(
      approval.modelId,
      "ark-short-term-v3",
    );

    assert.equal(
      approval.approvedBy,
      "human-reviewer",
    );
  },
);

test(
  "Model promotion approval rejects non-promotable evaluation",
  () => {
    const input =
      healthyInput();

    input.metrics.accuracy =
      30;

    const evaluation =
      evaluateModelPromotion(
        input,
      );

    const approval =
      approveModelPromotion({
        evaluation,

        approvedBy:
          "human-reviewer",
      });

    assert.equal(
      approval.approved,
      false,
    );

    assert.equal(
      approval.reason,
      "EVALUATION_NOT_PROMOTABLE",
    );
  },
);

test(
  "Model promotion approval requires approver",
  () => {
    const evaluation =
      evaluateModelPromotion(
        healthyInput(),
      );

    assert.throws(
      () =>
        approveModelPromotion({
          evaluation,
        }),

      /requires approvedBy/,
    );
  },
);

test(
  "Model promotion gate rejects invalid candidate",
  () => {
    assert.throws(
      () =>
        evaluateModelPromotion({
          candidate:
            null,
        }),

      /candidate must be an object/,
    );

    assert.throws(
      () =>
        evaluateModelPromotion({
          candidate:
            {},
        }),

      /requires an id/,
    );
  },
);

test(
  "Model promotion gate class evaluates deterministically",
  () => {
    const engine =
      new ModelPromotionGateV2({
        requireHumanApproval:
          false,

        minimumPromotionScore:
          80,
      });

    const first =
      engine.evaluate(
        healthyInput(),
      );

    const second =
      engine.evaluate(
        healthyInput(),
      );

    assert.equal(
      first.decision,
      second.decision,
    );

    assert.equal(
      first.promotionScore,
      second.promotionScore,
    );

    assert.deepEqual(
      first.blockers,
      second.blockers,
    );
  },
);