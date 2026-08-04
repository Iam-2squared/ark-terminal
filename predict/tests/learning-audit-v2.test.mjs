import test from "node:test";
import assert from "node:assert/strict";

import {
  LearningAuditV2,
  appendLearningAuditEntry,
  assertLearningAuditTrail,
  createLearningAuditEntry,
  createLearningAuditSnapshot,
  findLearningAuditEntries,
  summarizeLearningAuditTrail,
  verifyLearningAuditSnapshot,
  verifyLearningAuditTrail,
} from "../learning/learning-audit-v2.js";

test(
  "Learning audit creates deterministic entry",
  () => {
    const first =
      createLearningAuditEntry({
        eventType:
          "LEARNING_CYCLE_COMPLETED",

        actor:
          "learning-orchestrator",

        payload: {
          revision:
            2,
        },

        timestamp:
          "2026-08-04T00:00:00.000Z",
      });

    const second =
      createLearningAuditEntry({
        eventType:
          "LEARNING_CYCLE_COMPLETED",

        actor:
          "learning-orchestrator",

        payload: {
          revision:
            2,
        },

        timestamp:
          "2026-08-04T00:00:00.000Z",
      });

    assert.equal(
      first.hash,
      second.hash,
    );

    assert.equal(
      first.payloadHash,
      second.payloadHash,
    );

    assert.equal(
      first.sequence,
      1,
    );
  },
);

test(
  "Learning audit appends hash-linked entries",
  () => {
    let entries = [];

    entries =
      appendLearningAuditEntry({
        entries,

        eventType:
          "LEARNING_STARTED",

        actor:
          "system",

        timestamp:
          "2026-08-04T00:00:00.000Z",
      });

    entries =
      appendLearningAuditEntry({
        entries,

        eventType:
          "MODEL_PROMOTED",

        actor:
          "human-reviewer",

        payload: {
          revision:
            2,
        },

        timestamp:
          "2026-08-04T01:00:00.000Z",
      });

    assert.equal(
      entries.length,
      2,
    );

    assert.equal(
      entries[1]
        .previousHash,
      entries[0].hash,
    );

    assert.equal(
      entries[1]
        .sequence,
      2,
    );
  },
);

test(
  "Learning audit verifies valid chain",
  () => {
    let entries = [];

    entries =
      appendLearningAuditEntry({
        entries,

        eventType:
          "A",

        timestamp:
          "2026-08-04T00:00:00.000Z",
      });

    entries =
      appendLearningAuditEntry({
        entries,

        eventType:
          "B",

        timestamp:
          "2026-08-04T01:00:00.000Z",
      });

    const result =
      verifyLearningAuditTrail(
        entries,
      );

    assert.equal(
      result.valid,
      true,
    );

    assert.equal(
      result.issueCount,
      0,
    );

    assert.equal(
      result.entryCount,
      2,
    );
  },
);

test(
  "Learning audit detects payload tampering",
  () => {
    let entries = [];

    entries =
      appendLearningAuditEntry({
        entries,

        eventType:
          "MODEL_PROMOTED",

        payload: {
          revision:
            2,
        },

        timestamp:
          "2026-08-04T00:00:00.000Z",
      });

    entries[0].payload.revision =
      999;

    const result =
      verifyLearningAuditTrail(
        entries,
      );

    assert.equal(
      result.valid,
      false,
    );

    assert.ok(
      result.issues.some(
        (
          issue,
        ) =>
          issue.code ===
          "PAYLOAD_HASH_MISMATCH",
      ),
    );
  },
);

test(
  "Learning audit detects chain tampering",
  () => {
    let entries = [];

    entries =
      appendLearningAuditEntry({
        entries,

        eventType:
          "A",

        timestamp:
          "2026-08-04T00:00:00.000Z",
      });

    entries =
      appendLearningAuditEntry({
        entries,

        eventType:
          "B",

        timestamp:
          "2026-08-04T01:00:00.000Z",
      });

    entries[1].previousHash =
      "tampered";

    const result =
      verifyLearningAuditTrail(
        entries,
      );

    assert.equal(
      result.valid,
      false,
    );

    assert.ok(
      result.issues.some(
        (
          issue,
        ) =>
          issue.code ===
          "PREVIOUS_HASH_MISMATCH",
      ),
    );
  },
);

test(
  "Learning audit assertion throws on tampering",
  () => {
    let entries = [];

    entries =
      appendLearningAuditEntry({
        entries,

        eventType:
          "A",

        timestamp:
          "2026-08-04T00:00:00.000Z",
      });

    entries[0].hash =
      "invalid";

    assert.throws(
      () =>
        assertLearningAuditTrail(
          entries,
        ),

      (
        error,
      ) =>
        error.code ===
        "LEARNING_AUDIT_VERIFICATION_FAILED",
    );
  },
);

test(
  "Learning audit summary groups events and actors",
  () => {
    let entries = [];

    entries =
      appendLearningAuditEntry({
        entries,

        eventType:
          "MODEL_EVALUATED",

        actor:
          "system",

        timestamp:
          "2026-08-04T00:00:00.000Z",
      });

    entries =
      appendLearningAuditEntry({
        entries,

        eventType:
          "MODEL_EVALUATED",

        actor:
          "system",

        timestamp:
          "2026-08-04T01:00:00.000Z",
      });

    entries =
      appendLearningAuditEntry({
        entries,

        eventType:
          "MODEL_PROMOTED",

        actor:
          "human-reviewer",

        timestamp:
          "2026-08-04T02:00:00.000Z",
      });

    const summary =
      summarizeLearningAuditTrail(
        entries,
      );

    assert.equal(
      summary.valid,
      true,
    );

    assert.equal(
      summary.byEventType
        .MODEL_EVALUATED,
      2,
    );

    assert.equal(
      summary.byActor
        .system,
      2,
    );
  },
);

test(
  "Learning audit supports filtering",
  () => {
    let entries = [];

    entries =
      appendLearningAuditEntry({
        entries,

        eventType:
          "MODEL_EVALUATED",

        actor:
          "system",

        timestamp:
          "2026-08-04T00:00:00.000Z",
      });

    entries =
      appendLearningAuditEntry({
        entries,

        eventType:
          "MODEL_PROMOTED",

        actor:
          "human-reviewer",

        timestamp:
          "2026-08-04T01:00:00.000Z",
      });

    const filtered =
      findLearningAuditEntries({
        entries,

        eventType:
          "MODEL_PROMOTED",
      });

    assert.equal(
      filtered.length,
      1,
    );

    assert.equal(
      filtered[0].actor,
      "human-reviewer",
    );
  },
);

test(
  "Learning audit snapshot verifies unchanged chain",
  () => {
    let entries = [];

    entries =
      appendLearningAuditEntry({
        entries,

        eventType:
          "MODEL_PROMOTED",

        timestamp:
          "2026-08-04T00:00:00.000Z",
      });

    const snapshot =
      createLearningAuditSnapshot({
        entries,

        createdAt:
          "2026-08-04T02:00:00.000Z",

        createdBy:
          "audit-system",
      });

    const verification =
      verifyLearningAuditSnapshot({
        entries,

        snapshot,
      });

    assert.equal(
      verification.valid,
      true,
    );
  },
);

test(
  "Learning audit snapshot detects changed chain",
  () => {
    let entries = [];

    entries =
      appendLearningAuditEntry({
        entries,

        eventType:
          "MODEL_PROMOTED",

        payload: {
          revision:
            2,
        },

        timestamp:
          "2026-08-04T00:00:00.000Z",
      });

    const snapshot =
      createLearningAuditSnapshot({
        entries,

        createdAt:
          "2026-08-04T02:00:00.000Z",
      });

    entries[0].payload.revision =
      3;

    const verification =
      verifyLearningAuditSnapshot({
        entries,

        snapshot,
      });

    assert.equal(
      verification.valid,
      false,
    );
  },
);

test(
  "Learning audit class stores entries safely",
  () => {
    const audit =
      new LearningAuditV2();

    audit.append({
      eventType:
        "LEARNING_STARTED",

      actor:
        "system",

      timestamp:
        "2026-08-04T00:00:00.000Z",
    });

    audit.append({
      eventType:
        "MODEL_PROMOTED",

      actor:
        "human-reviewer",

      timestamp:
        "2026-08-04T01:00:00.000Z",
    });

    const listed =
      audit.list();

    listed[0].actor =
      "mutated";

    assert.equal(
      audit.list()[0].actor,
      "system",
    );

    assert.equal(
      audit.verify().valid,
      true,
    );

    assert.equal(
      audit.summary()
        .entryCount,
      2,
    );

    audit.reset();

    assert.equal(
      audit.list().length,
      0,
    );
  },
);