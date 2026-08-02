import assert from "node:assert/strict";
import test from "node:test";

import { LearningFeedbackRepository } from "../learning/learning-feedback-repository.js";

function storage() {
  const values = new Map();
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, String(value)),
    removeItem: (key) => values.delete(key),
  };
}

function report(id) {
  return {
    id,
    version: "resolved-feedback-v1",
    generatedAt: "2026-08-03T00:00:00.000Z",
    status: "collecting",
    weightCandidate: { updated: false, applied: false },
    marketFeatureCandidate: { applied: false },
    audit: { resolvedCount: 1 },
    promotionGate: { eligible: false, promotionAllowed: false },
    executionAllowed: false,
  };
}

test("Learning feedback repository persists summaries idempotently", () => {
  const store = storage();
  const repository = new LearningFeedbackRepository({ storage: store, limit: 2 });

  assert.equal(repository.append(report("one")).inserted, true);
  assert.equal(repository.append(report("one")).inserted, false);
  repository.append(report("two"));
  repository.append(report("three"));

  assert.deepEqual(
    repository.list().map((item) => item.id),
    ["three", "two"],
  );
  assert.equal(repository.latest().executionAllowed, false);
  assert.equal(repository.latest().promotionGate.promotionAllowed, false);

  const restored = new LearningFeedbackRepository({ storage: store, limit: 2 });
  assert.deepEqual(restored.list(), repository.list());
  restored.clear();
  assert.equal(restored.list().length, 0);
});

test("Learning feedback repository rejects execution-capable reports", () => {
  const repository = new LearningFeedbackRepository({ storage: storage() });
  assert.throws(
    () => repository.append({ ...report("unsafe"), executionAllowed: true }),
    /report is invalid/,
  );
});
