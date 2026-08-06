import test from "node:test";
import assert from "node:assert/strict";

import {
  LEARNING_CLOUD_COLLECTIONS,
  buildCandidateArchiveRecord,
  buildForwardValidationArchiveRecord,
  buildModelVersionArchiveRecord,
  loadLearningArchiveFromCloud,
} from "../cloud/learning-cloud-repository.js";

import {
  LearningCloudAutoSyncController,
} from "../cloud/learning-cloud-auto-sync.js";

import {
  ContinuousLearningOrchestratorV1,
} from "../learning/continuous-learning-v1.js";

import {
  PHASE20_FORWARD_VALIDATION_VERSION,
  recordCandidateForwardValidation,
} from "../learning/phase20-forward-validation.js";

function createEventTarget() {
  const listeners = new Map();
  const dispatched = [];

  return {
    dispatched,
    addEventListener(name, listener) {
      const values = listeners.get(name) ?? [];
      values.push(listener);
      listeners.set(name, values);
    },
    removeEventListener(name, listener) {
      const values = listeners.get(name) ?? [];
      listeners.set(
        name,
        values.filter((value) => value !== listener),
      );
    },
    dispatchEvent(event) {
      dispatched.push(event);
      for (const listener of listeners.get(event.type) ?? []) {
        listener(event);
      }
      return true;
    },
  };
}

function safeCandidate(overrides = {}) {
  return {
    id: "candidate-1",
    version: "model-v2-candidate",
    status: "CANDIDATE",
    createdAt: "2026-08-06T00:00:00.000Z",
    sourceTradeCount: 120,
    weights: { trend: 0.5, momentum: 0.5 },
    humanApprovalRequired: true,
    productionUpdateAllowed: false,
    metadata: {
      humanApprovalRequired: true,
      productionUpdateAllowed: false,
      brokerWriteAllowed: false,
    },
    ...overrides,
  };
}

function safeForwardResult(overrides = {}) {
  return {
    version: PHASE20_FORWARD_VALIDATION_VERSION,
    generatedAt: "2026-08-06T01:00:00.000Z",
    status: "READY_FOR_HUMAN_REVIEW",
    candidate: {
      proposalId: "candidate-1",
      version: "model-v2-candidate",
    },
    championModel: { version: "model-v1" },
    validationContext: {
      outOfSample: true,
      paperOnly: true,
      futureLeakChecked: true,
      sameSymbolSessionJoin: true,
    },
    diagnostics: { pairedDirectionalSamples: 120 },
    evaluation: {
      challenger: {
        accuracy: 62,
        profitFactor: 1.4,
        maximumDrawdown: 10,
        averageReturn: 0.8,
      },
    },
    blockers: [],
    safety: {
      paperOnly: true,
      liveBrokerAllowed: false,
      automaticPromotionAllowed: false,
      productionUpdateAllowed: false,
      brokerWriteAllowed: false,
      humanApprovalRequired: true,
      approved: false,
    },
    ...overrides,
  };
}

function safeArchive() {
  return {
    version: "learning-cloud-archive-v1",
    restoredAt: "2026-08-06T02:00:00.000Z",
    readOnly: true,
    appliedToRuntime: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    brokerWriteAllowed: false,
    candidates: [],
    forwardTests: [],
    modelVersions: [],
  };
}

test("Part5 archives only human-gated non-executable Candidates", () => {
  const record = buildCandidateArchiveRecord({
    candidate: safeCandidate(),
    action: "CANDIDATE_CREATED",
  });

  assert.equal(record.collection, LEARNING_CLOUD_COLLECTIONS.candidates);
  assert.equal(record.id, "candidate-1");
  assert.equal(record.data.safety.humanApprovalRequired, true);
  assert.equal(record.data.safety.automaticPromotionAllowed, false);
  assert.equal(record.data.safety.runtimeActivationAllowed, false);
  assert.equal(record.data.safety.productionUpdateAllowed, false);
  assert.equal(record.data.safety.brokerWriteAllowed, false);

  assert.throws(
    () => buildCandidateArchiveRecord({
      candidate: safeCandidate({ productionUpdateAllowed: true }),
    }),
    /LEARNING_ARCHIVE_EXECUTION_PERMISSION_REJECTED/,
  );

  assert.throws(
    () => buildCandidateArchiveRecord({
      candidate: safeCandidate({
        humanApprovalRequired: false,
        metadata: {},
      }),
    }),
    /CANDIDATE_HUMAN_APPROVAL_REQUIRED/,
  );
});

test("Part6 archives Forward results without promotion permission", () => {
  const record = buildForwardValidationArchiveRecord({
    result: safeForwardResult(),
    candidateId: "candidate-1",
  });

  assert.equal(record.collection, LEARNING_CLOUD_COLLECTIONS.forwardTests);
  assert.equal(record.data.status, "READY_FOR_HUMAN_REVIEW");
  assert.equal(record.data.validationContext.outOfSample, true);
  assert.equal(record.data.safety.automaticPromotionAllowed, false);
  assert.equal(record.data.safety.runtimeActivationAllowed, false);
  assert.equal(record.data.safety.brokerWriteAllowed, false);

  assert.throws(
    () => buildForwardValidationArchiveRecord({
      result: safeForwardResult({
        safety: {
          ...safeForwardResult().safety,
          automaticPromotionAllowed: true,
        },
      }),
      candidateId: "candidate-1",
    }),
    /LEARNING_ARCHIVE_EXECUTION_PERMISSION_REJECTED/,
  );
});

test("Part7 model-version archive is audit-only and requires a human actor", () => {
  const record = buildModelVersionArchiveRecord({
    action: "HUMAN_APPROVED",
    model: {
      version: "model-v2",
      status: "PRODUCTION",
      approvedBy: "Iam-2squared",
      productionUpdateAllowed: false,
      weights: { trend: 0.6, momentum: 0.4 },
    },
    candidateId: "candidate-1",
    approvedBy: "Iam-2squared",
  });

  assert.equal(record.collection, LEARNING_CLOUD_COLLECTIONS.modelVersions);
  assert.equal(record.data.approvedBy, "Iam-2squared");
  assert.equal(record.data.safety.runtimeActivationAllowed, false);
  assert.equal(record.data.safety.productionUpdateAllowed, false);

  assert.throws(
    () => buildModelVersionArchiveRecord({
      action: "ROLLBACK",
      model: {
        version: "model-v1",
        productionUpdateAllowed: false,
      },
    }),
    /MODEL_VERSION_HUMAN_ACTOR_REQUIRED/,
  );
});

test("Part7 restores three learning collections as a read-only archive", async () => {
  const calls = [];
  const archive = await loadLearningArchiveFromCloud({
    listProvider: async ({ collection }) => {
      calls.push(collection);
      return {
        records: [
          {
            id: `${collection}-1`,
            createdAt: "2026-08-06T00:00:00.000Z",
            updatedAt: "2026-08-06T01:00:00.000Z",
            data: { id: `${collection}-1` },
          },
        ],
      };
    },
  });

  assert.deepEqual(
    new Set(calls),
    new Set(Object.values(LEARNING_CLOUD_COLLECTIONS)),
  );
  assert.equal(archive.readOnly, true);
  assert.equal(archive.appliedToRuntime, false);
  assert.equal(archive.automaticPromotionAllowed, false);
  assert.equal(archive.productionUpdateAllowed, false);
  assert.equal(archive.brokerWriteAllowed, false);
  assert.equal(archive.candidates.length, 1);
  assert.equal(archive.forwardTests.length, 1);
  assert.equal(archive.modelVersions.length, 1);
});

test("Part7 auto sync restores archive without applying it to runtime", async () => {
  const eventTarget = createEventTarget();
  let runtimeWrites = 0;

  const controller = new LearningCloudAutoSyncController({
    statusProvider: async () => ({
      configured: true,
      storageConfigured: true,
      authenticated: true,
    }),
    archiveLoader: async () => safeArchive(),
    candidateWriter: async () => ({ saved: true }),
    forwardWriter: async () => ({ saved: true }),
    modelWriter: async () => ({ saved: true }),
    eventTarget,
  });

  const result = await controller.start().ready;

  assert.equal(result.restored, true);
  assert.equal(result.appliedToRuntime, false);
  assert.equal(runtimeWrites, 0);
  assert.equal(controller.getArchive().appliedToRuntime, false);
  assert.ok(
    eventTarget.dispatched.some(
      (event) => event.type === "ark:learning-cloud-archive-restored",
    ),
  );
});

test("Part7 rejects a restore payload that claims runtime application", async () => {
  const controller = new LearningCloudAutoSyncController({
    statusProvider: async () => ({
      configured: true,
      storageConfigured: true,
      authenticated: true,
    }),
    archiveLoader: async () => ({
      ...safeArchive(),
      appliedToRuntime: true,
    }),
    candidateWriter: async () => ({ saved: true }),
    forwardWriter: async () => ({ saved: true }),
    modelWriter: async () => ({ saved: true }),
    eventTarget: createEventTarget(),
  });

  const result = await controller.start().ready;
  assert.equal(result.restored, false);
  assert.equal(result.reason, "learning_cloud_restore_failed");
  assert.equal(result.appliedToRuntime, false);
  assert.equal(controller.getArchive(), null);
});

test("Part6 auto sync mirrors Candidate, Forward, and model audit events", async () => {
  const eventTarget = createEventTarget();
  const saved = {
    candidates: 0,
    forward: 0,
    models: 0,
  };

  const controller = new LearningCloudAutoSyncController({
    statusProvider: async () => ({
      configured: true,
      storageConfigured: true,
      authenticated: true,
    }),
    archiveLoader: async () => safeArchive(),
    candidateWriter: async () => {
      saved.candidates += 1;
      return { saved: true };
    },
    forwardWriter: async () => {
      saved.forward += 1;
      return { saved: true };
    },
    modelWriter: async () => {
      saved.models += 1;
      return { saved: true };
    },
    eventTarget,
  });

  await controller.start().ready;

  eventTarget.dispatchEvent({
    type: "ark:candidate-state-changed",
    detail: {
      action: "CANDIDATE_CREATED",
      candidate: safeCandidate(),
    },
  });
  eventTarget.dispatchEvent({
    type: "ark:forward-validation-recorded",
    detail: {
      candidateId: "candidate-1",
      result: safeForwardResult(),
    },
  });
  eventTarget.dispatchEvent({
    type: "ark:model-version-audit",
    detail: {
      action: "HUMAN_APPROVED",
      model: {
        version: "model-v2",
        approvedBy: "Iam-2squared",
        productionUpdateAllowed: false,
      },
      candidateId: "candidate-1",
      approvedBy: "Iam-2squared",
    },
  });

  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.deepEqual(saved, {
    candidates: 1,
    forward: 1,
    models: 1,
  });

  controller.stop();
});

test("Part6 orchestrator emits human-gated Candidate and model audit events", () => {
  const eventTarget = createEventTarget();
  const orchestrator = new ContinuousLearningOrchestratorV1({ eventTarget });
  const candidate = orchestrator.createCandidate({
    sourceTradeCount: 120,
    weights: { trend: 0.5, momentum: 0.5 },
    metadata: { version: "model-v2-candidate" },
  });

  orchestrator.recordWalkForward(candidate.id, {
    outOfSample: true,
    futureLeakChecked: true,
    passed: true,
    metrics: {
      accuracy: 62,
      profitFactor: 1.4,
      sharpe: 1.1,
      maxDrawdown: 10,
      averageReturn: 0.8,
    },
  });
  orchestrator.compareToProduction(candidate.id);
  orchestrator.approveCandidate(candidate.id, {
    approvedBy: "Iam-2squared",
  });

  const candidateEvents = eventTarget.dispatched.filter(
    (event) => event.type === "ark:candidate-state-changed",
  );
  const modelEvents = eventTarget.dispatched.filter(
    (event) => event.type === "ark:model-version-audit",
  );

  assert.ok(candidateEvents.length >= 4);
  assert.equal(
    candidateEvents.at(-1).detail.candidate.productionUpdateAllowed,
    false,
  );
  assert.equal(modelEvents.length, 1);
  assert.equal(modelEvents[0].detail.action, "HUMAN_APPROVED");
  assert.equal(modelEvents[0].detail.approvedBy, "Iam-2squared");
  assert.equal(modelEvents[0].detail.runtimeActivationAllowed, false);
});

test("Part6 forward recorder emits the full safe validation result", () => {
  const eventTarget = createEventTarget();
  const result = safeForwardResult();
  const recordedCandidate = {
    ...safeCandidate(),
    status: "VALIDATED",
  };

  const returned = recordCandidateForwardValidation({
    result,
    candidateId: "candidate-1",
    orchestrator: {
      recordWalkForward(candidateId, payload) {
        assert.equal(candidateId, "candidate-1");
        assert.equal(payload.outOfSample, true);
        assert.equal(payload.futureLeakChecked, true);
        return recordedCandidate;
      },
    },
    eventTarget,
  });

  assert.equal(returned.status, "VALIDATED");
  const event = eventTarget.dispatched.find(
    (value) => value.type === "ark:forward-validation-recorded",
  );
  assert.equal(event.detail.candidateId, "candidate-1");
  assert.equal(event.detail.result.status, "READY_FOR_HUMAN_REVIEW");
  assert.equal(event.detail.automaticPromotionAllowed, false);
  assert.equal(event.detail.productionUpdateAllowed, false);
  assert.equal(event.detail.brokerWriteAllowed, false);
});
