import test from "node:test";
import assert from "node:assert/strict";

import {
  ModelRollbackManagerV2,
  createRollbackSnapshot,
  evaluateModelRollback,
  executeModelRollback,
} from "../learning/model-rollback-manager-v2.js";

function models() {
  return {
    activeModel: {
      id:
        "ark-model",

      version:
        "3.0.0",

      family:
        "ENSEMBLE",
    },

    fallbackModel: {
      id:
        "ark-model",

      version:
        "2.9.0",

      family:
        "ENSEMBLE",
    },
  };
}

function healthyInput() {
  return {
    ...models(),

    activeMetrics: {
      accuracy:
        70,

      averageReturn:
        1.4,

      maximumDrawdown:
        8,

      profitFactor:
        1.7,

      calibrationError:
        9,

      rejectionRate:
        5,

      errorRate:
        1,

      sampleCount:
        200,
    },

    baselineMetrics: {
      accuracy:
        68,

      averageReturn:
        1.2,

      maximumDrawdown:
        9,

      profitFactor:
        1.5,

      calibrationError:
        10,

      rejectionRate:
        6,

      errorRate:
        1,

      sampleCount:
        500,
    },

    drift: {
      ready:
        true,

      driftDetected:
        false,

      driftScore:
        10,

      driftLevel:
        "LOW",

      recommendation: {
        action:
          "CONTINUE",
      },
    },
  };
}

test(
  "Rollback manager continues healthy model",
  () => {
    const result =
      evaluateModelRollback(
        healthyInput(),
      );

    assert.equal(
      result.version,
      "model-rollback-manager-v2",
    );

    assert.equal(
      result.ready,
      true,
    );

    assert.equal(
      result.action,
      "CONTINUE",
    );

    assert.equal(
      result.rollbackRequired,
      false,
    );

    assert.deepEqual(
      result.blockers,
      [],
    );
  },
);

test(
  "Rollback manager rolls back critical accuracy failure",
  () => {
    const input =
      healthyInput();

    input.activeMetrics.accuracy =
      35;

    const result =
      evaluateModelRollback(
        input,
      );

    assert.equal(
      result.action,
      "ROLLBACK",
    );

    assert.equal(
      result.automatic,
      true,
    );

    assert.equal(
      result.rollbackRequired,
      true,
    );

    assert.ok(
      result.blockers.includes(
        "ABSOLUTE_ACCURACY_FAILURE",
      ),
    );
  },
);

test(
  "Rollback manager rolls back critical drift",
  () => {
    const input =
      healthyInput();

    input.drift = {
      ready:
        true,

      driftDetected:
        true,

      driftScore:
        90,

      driftLevel:
        "CRITICAL",

      recommendation: {
        action:
          "RETRAIN",
      },
    };

    const result =
      evaluateModelRollback(
        input,
      );

    assert.equal(
      result.action,
      "ROLLBACK",
    );

    assert.ok(
      result.blockers.includes(
        "CRITICAL_CONCEPT_DRIFT",
      ),
    );
  },
);

test(
  "Rollback manager freezes moderate degradation",
  () => {
    const input =
      healthyInput();

    input.activeMetrics.profitFactor =
      0.6;

    const result =
      evaluateModelRollback({
        ...input,

        automaticRollbackThreshold:
          90,

        freezeThreshold:
          20,
      });

    assert.equal(
      result.action,
      "FREEZE",
    );

    assert.equal(
      result.reviewRequired,
      true,
    );
  },
);

test(
  "Rollback manager detects drawdown spike",
  () => {
    const input =
      healthyInput();

    input.activeMetrics.maximumDrawdown =
      25;

    const result =
      evaluateModelRollback(
        input,
      );

    assert.equal(
      result.action,
      "ROLLBACK",
    );

    assert.ok(
      result.blockers.includes(
        "DRAWDOWN_INCREASE",
      ),
    );
  },
);

test(
  "Rollback execution restores fallback model",
  () => {
    const input =
      healthyInput();

    input.activeMetrics.accuracy =
      30;

    const evaluation =
      evaluateModelRollback(
        input,
      );

    const rollback =
      executeModelRollback({
        evaluation,

        executedBy:
          "human-reviewer",

        note:
          "Critical production degradation.",
      });

    assert.equal(
      rollback.executed,
      true,
    );

    assert.equal(
      rollback.restoredModel.version,
      "2.9.0",
    );

    assert.equal(
      rollback.previousModel.version,
      "3.0.0",
    );

    assert.equal(
      rollback.registryPatch
        .retired.status,
      "ROLLED_BACK",
    );
  },
);

test(
  "Rollback execution rejects healthy model",
  () => {
    const evaluation =
      evaluateModelRollback(
        healthyInput(),
      );

    const rollback =
      executeModelRollback({
        evaluation,

        executedBy:
          "reviewer",
      });

    assert.equal(
      rollback.executed,
      false,
    );

    assert.equal(
      rollback.reason,
      "ROLLBACK_NOT_REQUIRED",
    );
  },
);

test(
  "Rollback execution requires approver",
  () => {
    const input =
      healthyInput();

    input.activeMetrics.accuracy =
      20;

    const evaluation =
      evaluateModelRollback(
        input,
      );

    assert.throws(
      () =>
        executeModelRollback({
          evaluation,
        }),

      /requires executedBy/,
    );
  },
);

test(
  "Rollback snapshot preserves registry",
  () => {
    const snapshot =
      createRollbackSnapshot({
        ...models(),

        registry: {
          champion:
            "ark-model@3.0.0",

          history: [
            "ark-model@2.9.0",
          ],
        },
      });

    assert.equal(
      snapshot.activeModel.version,
      "3.0.0",
    );

    assert.equal(
      snapshot.fallbackModel.version,
      "2.9.0",
    );

    assert.deepEqual(
      snapshot.registry.history,
      [
        "ark-model@2.9.0",
      ],
    );
  },
);

test(
  "Rollback manager rejects identical models",
  () => {
    assert.throws(
      () =>
        evaluateModelRollback({
          activeModel: {
            id:
              "same",

            version:
              "1",
          },

          fallbackModel: {
            id:
              "same",

            version:
              "1",
          },
        }),

      /must be different/,
    );
  },
);

test(
  "Rollback manager class evaluates deterministically",
  () => {
    const manager =
      new ModelRollbackManagerV2();

    const first =
      manager.evaluate(
        healthyInput(),
      );

    const second =
      manager.evaluate(
        healthyInput(),
      );

    assert.equal(
      first.action,
      second.action,
    );

    assert.equal(
      first.riskScore,
      second.riskScore,
    );

    assert.deepEqual(
      first.blockers,
      second.blockers,
    );
  },
);