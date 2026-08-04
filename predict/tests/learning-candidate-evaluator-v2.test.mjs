import test from "node:test";
import assert from "node:assert/strict";

import {
  LearningCandidateEvaluatorV2,
  approveLearningCandidate,
  evaluateLearningCandidate,
} from "../learning/learning-candidate-evaluator-v2.js";

function state({
  revision,
  accuracy,
  averageReturn,
  maximumDrawdown,
  calibrationError,
  profitFactor,
  sampleCount = 100,
  currentLossStreak = 0,
} = {}) {
  return {
    modelId:
      "ark-learning",

    modelVersion:
      `v${revision}`,

    revision,

    metrics: {
      ready:
        true,

      sampleCount,

      accuracy,

      weightedAccuracy:
        accuracy,

      averageReturn,

      medianReturn:
        averageReturn,

      maximumDrawdown,

      calibrationError,

      profitFactor,

      volatility:
        2,

      streaks: {
        currentLossStreak,
      },
    },
  };
}

function currentState() {
  return state({
    revision:
      1,

    accuracy:
      55,

    averageReturn:
      1,

    maximumDrawdown:
      10,

    calibrationError:
      20,

    profitFactor:
      1.2,
  });
}

function improvedCandidate() {
  return state({
    revision:
      2,

    accuracy:
      62,

    averageReturn:
      1.8,

    maximumDrawdown:
      8,

    calibrationError:
      15,

    profitFactor:
      1.6,
  });
}

test(
  "Candidate evaluator requires human approval for improved model",
  () => {
    const result =
      evaluateLearningCandidate({
        currentState:
          currentState(),

        candidateState:
          improvedCandidate(),

        minimumCandidateSamples:
          20,

        minimumEvaluationScore:
          55,

        requireHumanApproval:
          true,
      });

    assert.equal(
      result.decision,
      "REQUIRE_HUMAN_APPROVAL",
    );

    assert.equal(
      result.approved,
      false,
    );

    assert.equal(
      result.blockers.length,
      0,
    );

    assert.ok(
      result.evaluationScore >=
      55,
    );
  },
);

test(
  "Candidate evaluator promotes without approval requirement",
  () => {
    const result =
      evaluateLearningCandidate({
        currentState:
          currentState(),

        candidateState:
          improvedCandidate(),

        minimumEvaluationScore:
          55,

        requireHumanApproval:
          false,
      });

    assert.equal(
      result.decision,
      "PROMOTE",
    );

    assert.equal(
      result.approved,
      true,
    );
  },
);

test(
  "Candidate evaluator rejects low accuracy",
  () => {
    const result =
      evaluateLearningCandidate({
        currentState:
          currentState(),

        candidateState:
          state({
            revision:
              2,

            accuracy:
              30,

            averageReturn:
              1,

            maximumDrawdown:
              10,

            calibrationError:
              20,

            profitFactor:
              1.2,
          }),

        minimumAccuracy:
          45,
      });

    assert.equal(
      result.decision,
      "REJECT",
    );

    assert.ok(
      result.blockers.includes(
        "ACCURACY_BELOW_MINIMUM",
      ),
    );
  },
);

test(
  "Candidate evaluator rejects drawdown regression",
  () => {
    const result =
      evaluateLearningCandidate({
        currentState:
          currentState(),

        candidateState:
          state({
            revision:
              2,

            accuracy:
              60,

            averageReturn:
              1.5,

            maximumDrawdown:
              20,

            calibrationError:
              18,

            profitFactor:
              1.4,
          }),

        maximumDrawdownIncrease:
          3,
      });

    assert.equal(
      result.decision,
      "REJECT",
    );

    assert.ok(
      result.blockers.includes(
        "DRAWDOWN_REGRESSION",
      ),
    );
  },
);

test(
  "Candidate evaluator rejects stale revision",
  () => {
    const candidate =
      improvedCandidate();

    candidate.revision =
      1;

    const result =
      evaluateLearningCandidate({
        currentState:
          currentState(),

        candidateState:
          candidate,
      });

    assert.equal(
      result.decision,
      "REJECT",
    );

    assert.ok(
      result.blockers.includes(
        "REVISION_NOT_ADVANCED",
      ),
    );
  },
);

test(
  "Candidate evaluator holds insufficient sample candidate",
  () => {
    const candidate =
      improvedCandidate();

    candidate.metrics.sampleCount =
      5;

    const result =
      evaluateLearningCandidate({
        currentState:
          currentState(),

        candidateState:
          candidate,

        minimumCandidateSamples:
          20,

        requireHumanApproval:
          false,
      });

    assert.equal(
      result.decision,
      "HOLD",
    );

    assert.ok(
      result.warnings.includes(
        "INSUFFICIENT_CANDIDATE_SAMPLES",
      ),
    );
  },
);

test(
  "Human approval converts candidate to promotion",
  () => {
    const evaluation =
      evaluateLearningCandidate({
        currentState:
          currentState(),

        candidateState:
          improvedCandidate(),

        minimumEvaluationScore:
          55,

        requireHumanApproval:
          true,
      });

    const approved =
      approveLearningCandidate({
        evaluation,

        approvedBy:
          "human-reviewer",

        approvedAt:
          "2026-08-04T00:00:00.000Z",
      });

    assert.equal(
      approved.decision,
      "PROMOTE",
    );

    assert.equal(
      approved.approved,
      true,
    );

    assert.equal(
      approved.approval
        .approvedBy,
      "human-reviewer",
    );

    assert.equal(
      approved.recommendation
        .allowRegistryChange,
      true,
    );
  },
);

test(
  "Human approval rejects invalid evaluation state",
  () => {
    const evaluation =
      evaluateLearningCandidate({
        currentState:
          currentState(),

        candidateState:
          improvedCandidate(),

        requireHumanApproval:
          false,

        minimumEvaluationScore:
          55,
      });

    assert.throws(
      () =>
        approveLearningCandidate({
          evaluation,

          approvedBy:
            "human-reviewer",
        }),

      /not awaiting human approval/,
    );
  },
);

test(
  "Candidate evaluator class stores history",
  () => {
    const evaluator =
      new LearningCandidateEvaluatorV2({
        minimumEvaluationScore:
          55,

        requireHumanApproval:
          true,
      });

    const result =
      evaluator.evaluate({
        currentState:
          currentState(),

        candidateState:
          improvedCandidate(),
      });

    assert.equal(
      result.decision,
      "REQUIRE_HUMAN_APPROVAL",
    );

    assert.equal(
      evaluator
        .getHistory()
        .length,
      1,
    );

    evaluator.resetHistory();

    assert.equal(
      evaluator
        .getHistory()
        .length,
      0,
    );
  },
);

test(
  "Candidate evaluator validates states",
  () => {
    assert.throws(
      () =>
        evaluateLearningCandidate({
          currentState:
            null,

          candidateState:
            improvedCandidate(),
        }),

      /Current learning state is required/,
    );

    assert.throws(
      () =>
        evaluateLearningCandidate({
          currentState:
            currentState(),

          candidateState:
            null,
        }),

      /Candidate learning state is required/,
    );
  },
);