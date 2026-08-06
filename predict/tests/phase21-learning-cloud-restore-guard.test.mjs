import test from "node:test";
import assert from "node:assert/strict";

import {
  buildCandidateArchiveRecord,
} from "../cloud/learning-cloud-repository.js";

import {
  LearningCloudAutoSyncController,
} from "../cloud/learning-cloud-auto-sync.js";

function eventTarget() {
  const listeners = new Map();
  return {
    addEventListener(name, listener) {
      listeners.set(name, [...(listeners.get(name) ?? []), listener]);
    },
    removeEventListener(name, listener) {
      listeners.set(
        name,
        (listeners.get(name) ?? []).filter((value) => value !== listener),
      );
    },
    dispatchEvent(event) {
      for (const listener of listeners.get(event.type) ?? []) listener(event);
      return true;
    },
  };
}

function safeArchive(overrides = {}) {
  return {
    version: "learning-cloud-archive-v1",
    readOnly: true,
    appliedToRuntime: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    brokerWriteAllowed: false,
    candidates: [],
    forwardTests: [],
    modelVersions: [],
    ...overrides,
  };
}

test("Learning archive restore rejects an unsafe nested record", async () => {
  const controller = new LearningCloudAutoSyncController({
    statusProvider: async () => ({
      configured: true,
      storageConfigured: true,
      authenticated: true,
    }),
    archiveLoader: async () => safeArchive({
      candidates: [
        {
          id: "candidate-unsafe",
          data: {
            id: "candidate-unsafe",
            safety: {
              automaticPromotionAllowed: true,
            },
          },
        },
      ],
    }),
    candidateWriter: async () => ({ saved: true }),
    forwardWriter: async () => ({ saved: true }),
    modelWriter: async () => ({ saved: true }),
    eventTarget: eventTarget(),
  });

  const result = await controller.start().ready;
  assert.equal(result.restored, false);
  assert.equal(result.reason, "learning_cloud_restore_failed");
  assert.equal(result.appliedToRuntime, false);
  assert.equal(controller.getArchive(), null);
});

test("Learning archive save refreshes cloud status during startup", async () => {
  let statusCalls = 0;
  let candidateWrites = 0;

  const controller = new LearningCloudAutoSyncController({
    statusProvider: async () => {
      statusCalls += 1;
      return {
        configured: true,
        storageConfigured: true,
        authenticated: true,
      };
    },
    archiveLoader: async () => safeArchive(),
    candidateWriter: async () => {
      candidateWrites += 1;
      return { saved: true };
    },
    forwardWriter: async () => ({ saved: true }),
    modelWriter: async () => ({ saved: true }),
    eventTarget: eventTarget(),
  });

  const result = await controller.mirrorCandidate({
    action: "CANDIDATE_CREATED",
    candidate: {
      id: "candidate-startup",
      version: "candidate-v1",
      humanApprovalRequired: true,
      productionUpdateAllowed: false,
    },
  });

  assert.equal(result.saved, true);
  assert.equal(candidateWrites, 1);
  assert.equal(statusCalls, 1);
});

test("Candidate archive requires an explicit candidate id", () => {
  assert.throws(
    () => buildCandidateArchiveRecord({
      candidate: {
        version: "candidate-v1",
        humanApprovalRequired: true,
        productionUpdateAllowed: false,
      },
    }),
    /CANDIDATE_ID_AND_VERSION_REQUIRED/,
  );
});
