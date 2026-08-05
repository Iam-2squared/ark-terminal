import assert from "node:assert/strict";
import test from "node:test";

import {
  createCandidateProposalFromAdvice,
  registerCandidateProposal,
} from "../learning/phase20-candidate-proposal.js";

function safeReview({ shouldCreateCandidate = true } = {}) {
  return {
    status: "ADVISORY_ONLY",
    candidateCreationAllowed: false,
    productionUpdateAllowed: false,
    brokerWriteAllowed: false,
    humanApprovalRequired: true,
    advice: {
      summary: "テスト用の改善仮説",
      candidateHypothesis: {
        shouldCreateCandidate,
        rationale: "モメンタムを少し増やして検証する。",
        weightChanges: [
          {
            feature: "momentum",
            direction: "INCREASE",
            delta: 0.1,
            reason: "失敗例で過小評価されていた。",
          },
          {
            feature: "inventedFeature",
            direction: "INCREASE",
            delta: 0.2,
            reason: "存在しない特徴量。",
          },
        ],
        thresholdChanges: [
          {
            name: "minimumConfidence",
            currentValue: "0.60",
            proposedValue: "0.75",
            reason: "低信頼シグナルを減らす。",
          },
          {
            name: "unknownThreshold",
            currentValue: "1",
            proposedValue: "2",
            reason: "未許可。",
          },
        ],
        exclusionRules: ["決算翌日は候補から除外する"],
      },
      safety: {
        advisoryOnly: true,
        humanApprovalRequired: true,
        productionUpdateAllowed: false,
        brokerWriteAllowed: false,
      },
    },
  };
}

const currentModel = {
  id: "ark-model",
  version: "20.4.0",
  weights: {
    trend: 0.4,
    momentum: 0.3,
    volume: 0.3,
  },
  thresholds: {
    minimumConfidence: 0.6,
  },
};

const thresholdPolicy = {
  minimumConfidence: {
    minimum: 0.5,
    maximum: 0.9,
    maximumDelta: 0.05,
  },
};

test("OpenAI助言を既存キーだけの非実行Candidateへ変換する", () => {
  const proposal = createCandidateProposalFromAdvice({
    review: safeReview(),
    currentModel,
    audit: { summary: { total: 120 } },
    requestedBy: "human-reviewer",
    thresholdPolicy,
    candidateId: "candidate-test-1",
    now: () => new Date("2026-08-06T00:00:00.000Z"),
  });

  assert.equal(proposal.id, "candidate-test-1");
  assert.equal(proposal.status, "PROPOSED_FOR_VALIDATION");
  assert.equal(proposal.safety.executable, false);
  assert.equal(proposal.safety.productionUpdateAllowed, false);
  assert.equal(proposal.safety.brokerWriteAllowed, false);
  assert.equal(proposal.safety.automaticPromotionAllowed, false);
  assert.equal(Object.hasOwn(proposal.weights, "inventedFeature"), false);
  assert.equal(
    proposal.rejectedChanges.some(
      (item) => item.reason === "UNKNOWN_FEATURE_KEY",
    ),
    true,
  );
  assert.equal(proposal.thresholds.minimumConfidence, 0.65);
  assert.equal(
    proposal.rejectedChanges.some(
      (item) => item.reason === "THRESHOLD_NOT_ALLOWLISTED",
    ),
    true,
  );

  const total = Object.values(proposal.weights).reduce(
    (sum, value) => sum + value,
    0,
  );
  assert.ok(Math.abs(total - 1) < 0.000001);
});

test("人間名がなければCandidateを作れない", () => {
  assert.throws(
    () =>
      createCandidateProposalFromAdvice({
        review: safeReview(),
        currentModel,
        audit: { summary: { total: 120 } },
        thresholdPolicy,
      }),
    /HUMAN_REQUESTER_REQUIRED/,
  );
});

test("OpenAIがCandidate不要と判断した場合は作らない", () => {
  assert.throws(
    () =>
      createCandidateProposalFromAdvice({
        review: safeReview({ shouldCreateCandidate: false }),
        currentModel,
        audit: { summary: { total: 120 } },
        requestedBy: "reviewer",
        thresholdPolicy,
      }),
    /OPENAI_DID_NOT_RECOMMEND_CANDIDATE/,
  );
});

test("サンプル不足ではCandidateを作らない", () => {
  assert.throws(
    () =>
      createCandidateProposalFromAdvice({
        review: safeReview(),
        currentModel,
        audit: { summary: { total: 20 } },
        requestedBy: "reviewer",
        thresholdPolicy,
        minimumDirectionalSamples: 50,
      }),
    /INSUFFICIENT_DIRECTIONAL_SAMPLES_FOR_CANDIDATE/,
  );
});

test("Candidate登録も明示的人間操作を要求する", () => {
  const proposal = createCandidateProposalFromAdvice({
    review: safeReview(),
    currentModel,
    audit: { summary: { total: 120 } },
    requestedBy: "proposal-reviewer",
    thresholdPolicy,
    candidateId: "candidate-register-test",
  });

  let captured = null;
  const orchestrator = {
    createCandidate(payload) {
      captured = payload;
      return {
        id: "registered-candidate",
        status: "CANDIDATE",
        ...payload,
      };
    },
  };

  assert.throws(
    () => registerCandidateProposal({ proposal, orchestrator }),
    /HUMAN_REGISTRAR_REQUIRED/,
  );

  const registered = registerCandidateProposal({
    proposal,
    orchestrator,
    registeredBy: "human-registrar",
  });

  assert.equal(registered.status, "CANDIDATE");
  assert.equal(captured.metadata.productionUpdateAllowed, false);
  assert.equal(captured.metadata.brokerWriteAllowed, false);
  assert.equal(captured.metadata.registeredBy, "human-registrar");
});
