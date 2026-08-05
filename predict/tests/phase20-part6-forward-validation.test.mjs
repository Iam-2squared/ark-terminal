import assert from "node:assert/strict";
import test from "node:test";

import {
  buildPairedForwardRecords,
  runCandidateForwardValidation,
} from "../learning/phase20-forward-validation.js";

function createRows(count = 180) {
  const rows = [];
  let close = 100;
  const start = Date.parse("2026-01-01T00:00:00.000Z");

  for (let index = 0; index < count; index += 1) {
    const expectedNext = index % 5 === 0 ? -1 : 1;
    rows.push({
      symbol: "TEST.T",
      date: new Date(start + index * 86400000).toISOString(),
      close,
      features: {
        expectedNext,
        index,
      },
    });
    close *= 1 + expectedNext / 100;
  }

  return rows;
}

const candidateProposal = {
  id: "candidate-forward-test",
  candidateVersion: "20.5.0-candidate",
  status: "PROPOSED_FOR_VALIDATION",
  safety: {
    executable: false,
    productionUpdateAllowed: false,
    brokerWriteAllowed: false,
    automaticPromotionAllowed: false,
  },
};

async function candidatePredictor(input) {
  return {
    action: input.features.expectedNext > 0 ? "BUY" : "SELL",
    confidence: 80,
    score: 75,
  };
}

async function championPredictor(input) {
  const correctAction = input.features.expectedNext > 0 ? "BUY" : "SELL";
  const wrongAction = correctAction === "BUY" ? "SELL" : "BUY";
  return {
    action: input.features.index % 4 === 0 ? wrongAction : correctAction,
    confidence: 65,
    score: 60,
  };
}

function evaluationOptions() {
  return {
    minimumSamples: 100,
    minimumAccuracyImprovement: 1,
    minimumReturnImprovement: 0,
    maximumDrawdownRegression: 10,
    maximumCalibrationRegression: 10,
    minimumWinProbability: 0,
    minimumPromotionScore: 0,
    bootstrapIterations: 200,
    bootstrapSeed: 123,
  };
}

test("未使用Paperデータ上でCandidateを現行モデルと対比較する", async () => {
  const result = await runCandidateForwardValidation({
    rows: createRows(),
    championPredictor,
    candidatePredictor,
    championModel: {
      id: "ark-model",
      version: "20.4.0",
      family: "ENSEMBLE",
    },
    candidateProposal,
    horizon: 1,
    minimumHistory: 10,
    neutralThreshold: 0.1,
    validationContext: {
      datasetId: "unseen-window-2026-q1",
      datasetWindow: "2026-01-01/2026-06-30",
      outOfSample: true,
      paperOnly: true,
    },
    evaluationOptions: evaluationOptions(),
  });

  assert.equal(result.status, "READY_FOR_HUMAN_REVIEW");
  assert.equal(result.evaluation.decision, "PROMOTE_CHALLENGER");
  assert.equal(result.evaluation.humanApprovalRequired, true);
  assert.equal(result.evaluation.approved, false);
  assert.equal(result.validationContext.outOfSample, true);
  assert.equal(result.validationContext.futureLeakChecked, true);
  assert.equal(result.validationContext.sameSymbolSessionJoin, true);
  assert.ok(result.diagnostics.pairedDirectionalSamples >= 100);
  assert.equal(result.safety.automaticPromotionAllowed, false);
  assert.equal(result.safety.productionUpdateAllowed, false);
  assert.equal(result.safety.brokerWriteAllowed, false);
  assert.equal(result.safety.liveBrokerAllowed, false);
});

test("Out-of-sample指定がなければ成績が良くても昇格候補にしない", async () => {
  const result = await runCandidateForwardValidation({
    rows: createRows(),
    championPredictor,
    candidatePredictor,
    championModel: {
      id: "ark-model",
      version: "20.4.0",
    },
    candidateProposal,
    horizon: 1,
    minimumHistory: 10,
    neutralThreshold: 0.1,
    validationContext: {
      outOfSample: false,
      paperOnly: true,
    },
    evaluationOptions: evaluationOptions(),
  });

  assert.equal(result.status, "BLOCKED_NOT_OUT_OF_SAMPLE");
  assert.equal(result.blockers.includes("OUT_OF_SAMPLE_REQUIRED"), true);
  assert.equal(result.safety.approved, false);
});

test("Paper-only指定がなければ実運用候補にしない", async () => {
  const result = await runCandidateForwardValidation({
    rows: createRows(),
    championPredictor,
    candidatePredictor,
    championModel: {
      id: "ark-model",
      version: "20.4.0",
    },
    candidateProposal,
    horizon: 1,
    minimumHistory: 10,
    neutralThreshold: 0.1,
    validationContext: {
      outOfSample: true,
      paperOnly: false,
    },
    evaluationOptions: evaluationOptions(),
  });

  assert.equal(result.status, "BLOCKED_NOT_PAPER_ONLY");
  assert.equal(result.blockers.includes("PAPER_ONLY_REQUIRED"), true);
});

test("両モデルが方向予測した同一サンプルだけを比較する", () => {
  const championPredictions = [
    {
      symbol: "AAA.T",
      entryDate: "2026-01-01",
      exitDate: "2026-01-02",
      horizon: 1,
      action: "BUY",
      confidence: 70,
      returnPercent: 1,
    },
    {
      symbol: "AAA.T",
      entryDate: "2026-01-02",
      exitDate: "2026-01-03",
      horizon: 1,
      action: "HOLD",
      confidence: 50,
      returnPercent: -1,
    },
  ];

  const challengerPredictions = [
    {
      symbol: "AAA.T",
      entryDate: "2026-01-01",
      exitDate: "2026-01-02",
      horizon: 1,
      action: "BUY",
      confidence: 80,
      returnPercent: 1,
    },
    {
      symbol: "AAA.T",
      entryDate: "2026-01-02",
      exitDate: "2026-01-03",
      horizon: 1,
      action: "SELL",
      confidence: 75,
      returnPercent: -1,
    },
  ];

  const paired = buildPairedForwardRecords({
    championPredictions,
    challengerPredictions,
  });

  assert.equal(paired.records.length, 1);
  assert.equal(paired.diagnostics.commonSamples, 2);
  assert.equal(paired.diagnostics.nonDirectionalChampion, 1);
});

test("安全契約を満たさないCandidateは検証できない", async () => {
  await assert.rejects(
    () =>
      runCandidateForwardValidation({
        rows: createRows(),
        championPredictor,
        candidatePredictor,
        championModel: {
          id: "ark-model",
          version: "20.4.0",
        },
        candidateProposal: {
          ...candidateProposal,
          safety: {
            productionUpdateAllowed: true,
            brokerWriteAllowed: false,
          },
        },
      }),
    /SAFE_CANDIDATE_PROPOSAL_REQUIRED/,
  );
});
