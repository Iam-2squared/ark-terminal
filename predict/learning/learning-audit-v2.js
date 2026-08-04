import {
  createHash,
} from "node:crypto";

export const LEARNING_AUDIT_V2_VERSION =
  "learning-audit-v2";

export const LEARNING_AUDIT_V2_SCHEMA_VERSION =
  1;

function normalizeText(
  value,
  fallback = "",
) {
  const text =
    String(
      value ??
      fallback,
    ).trim();

  return text || fallback;
}

function normalizeTimestamp(
  value,
  fallback =
    new Date().toISOString(),
) {
  const source =
    value ??
    fallback;

  const milliseconds =
    typeof source === "number"
      ? source
      : Date.parse(source);

  if (!Number.isFinite(milliseconds)) {
    throw new TypeError(
      "Learning audit timestamp is invalid.",
    );
  }

  return new Date(
    milliseconds,
  ).toISOString();
}

function clone(value) {
  return value === undefined
    ? undefined
    : structuredClone(value);
}

function stableSerialize(value) {
  if (
    value === null ||
    typeof value !== "object"
  ) {
    return JSON.stringify(value);
  }

  if (Array.isArray(value)) {
    return [
      "[",
      value
        .map(
          stableSerialize,
        )
        .join(","),
      "]",
    ].join("");
  }

  const keys =
    Object.keys(value)
      .sort();

  return [
    "{",
    keys
      .map(
        (
          key,
        ) =>
          `${JSON.stringify(key)}:${stableSerialize(value[key])}`,
      )
      .join(","),
    "}",
  ].join("");
}

function hashValue(value) {
  return createHash(
    "sha256",
  )
    .update(
      stableSerialize(value),
      "utf8",
    )
    .digest(
      "hex",
    );
}

function normalizeMetadata(
  metadata,
) {
  if (
    !metadata ||
    typeof metadata !== "object" ||
    Array.isArray(metadata)
  ) {
    return {};
  }

  return clone(
    metadata,
  );
}

function normalizePayload(
  payload,
) {
  if (
    payload === undefined
  ) {
    return null;
  }

  return clone(
    payload,
  );
}

function buildHashMaterial(
  entry,
) {
  return {
    version:
      entry.version,

    schemaVersion:
      entry.schemaVersion,

    sequence:
      entry.sequence,

    id:
      entry.id,

    eventType:
      entry.eventType,

    actor:
      entry.actor,

    timestamp:
      entry.timestamp,

    previousHash:
      entry.previousHash,

    payloadHash:
      entry.payloadHash,

    metadata:
      entry.metadata,
  };
}

export function createLearningAuditEntry({
  eventType,
  actor = "system",
  payload = null,
  metadata = {},
  timestamp =
    new Date().toISOString(),
  sequence = 1,
  previousHash = null,
  id = null,
} = {}) {
  const normalizedEventType =
    normalizeText(
      eventType,
      "",
    ).toUpperCase();

  if (!normalizedEventType) {
    throw new TypeError(
      "Learning audit eventType is required.",
    );
  }

  const normalizedActor =
    normalizeText(
      actor,
      "system",
    );

  const normalizedTimestamp =
    normalizeTimestamp(
      timestamp,
    );

  const normalizedSequence =
    Math.max(
      1,
      Math.floor(
        Number(sequence) ||
        1,
      ),
    );

  const normalizedPreviousHash =
    previousHash === null ||
    previousHash === undefined ||
    previousHash === ""
      ? null
      : normalizeText(
          previousHash,
          "",
        );

  const normalizedPayload =
    normalizePayload(
      payload,
    );

  const payloadHash =
    hashValue(
      normalizedPayload,
    );

  const normalizedId =
    normalizeText(
      id,
      [
        "learning-audit",
        normalizedSequence,
        normalizedEventType,
        Date.parse(
          normalizedTimestamp,
        ),
      ].join(":"),
    );

  const entry = {
    version:
      LEARNING_AUDIT_V2_VERSION,

    schemaVersion:
      LEARNING_AUDIT_V2_SCHEMA_VERSION,

    sequence:
      normalizedSequence,

    id:
      normalizedId,

    eventType:
      normalizedEventType,

    actor:
      normalizedActor,

    timestamp:
      normalizedTimestamp,

    previousHash:
      normalizedPreviousHash,

    payload:
      normalizedPayload,

    payloadHash,

    metadata:
      normalizeMetadata(
        metadata,
      ),
  };

  return {
    ...entry,

    hash:
      hashValue(
        buildHashMaterial(
          entry,
        ),
      ),
  };
}

export function appendLearningAuditEntry({
  entries = [],
  eventType,
  actor = "system",
  payload = null,
  metadata = {},
  timestamp =
    new Date().toISOString(),
  id = null,
} = {}) {
  if (!Array.isArray(entries)) {
    throw new TypeError(
      "Learning audit entries must be an array.",
    );
  }

  const previousEntry =
    entries.at(-1) ??
    null;

  const entry =
    createLearningAuditEntry({
      eventType,

      actor,

      payload,

      metadata,

      timestamp,

      id,

      sequence:
        entries.length +
        1,

      previousHash:
        previousEntry?.hash ??
        null,
    });

  return [
    ...clone(entries),
    entry,
  ];
}

export function verifyLearningAuditTrail(
  entries = [],
) {
  if (!Array.isArray(entries)) {
    throw new TypeError(
      "Learning audit entries must be an array.",
    );
  }

  const issues = [];
  const seenIds =
    new Set();

  for (
    let index = 0;
    index < entries.length;
    index += 1
  ) {
    const entry =
      entries[index];

    if (
      !entry ||
      typeof entry !== "object" ||
      Array.isArray(entry)
    ) {
      issues.push({
        index,

        code:
          "INVALID_ENTRY",

        message:
          "Audit entry is not an object.",
      });

      continue;
    }

    const expectedSequence =
      index +
      1;

    if (
      entry.sequence !==
      expectedSequence
    ) {
      issues.push({
        index,

        entryId:
          entry.id ??
          null,

        code:
          "SEQUENCE_MISMATCH",

        expected:
          expectedSequence,

        actual:
          entry.sequence,
      });
    }

    if (
      !entry.id
    ) {
      issues.push({
        index,

        code:
          "MISSING_ID",
      });
    }
    else if (
      seenIds.has(
        entry.id,
      )
    ) {
      issues.push({
        index,

        entryId:
          entry.id,

        code:
          "DUPLICATE_ID",
      });
    }
    else {
      seenIds.add(
        entry.id,
      );
    }

    const expectedPreviousHash =
      index === 0
        ? null
        : entries[
            index -
            1
          ]?.hash ??
          null;

    if (
      entry.previousHash !==
      expectedPreviousHash
    ) {
      issues.push({
        index,

        entryId:
          entry.id ??
          null,

        code:
          "PREVIOUS_HASH_MISMATCH",

        expected:
          expectedPreviousHash,

        actual:
          entry.previousHash,
      });
    }

    const expectedPayloadHash =
      hashValue(
        entry.payload ??
        null,
      );

    if (
      entry.payloadHash !==
      expectedPayloadHash
    ) {
      issues.push({
        index,

        entryId:
          entry.id ??
          null,

        code:
          "PAYLOAD_HASH_MISMATCH",

        expected:
          expectedPayloadHash,

        actual:
          entry.payloadHash,
      });
    }

    const expectedHash =
      hashValue(
        buildHashMaterial({
          version:
            entry.version,

          schemaVersion:
            entry.schemaVersion,

          sequence:
            entry.sequence,

          id:
            entry.id,

          eventType:
            entry.eventType,

          actor:
            entry.actor,

          timestamp:
            entry.timestamp,

          previousHash:
            entry.previousHash,

          payloadHash:
            entry.payloadHash,

          metadata:
            entry.metadata ??
            {},
        }),
      );

    if (
      entry.hash !==
      expectedHash
    ) {
      issues.push({
        index,

        entryId:
          entry.id ??
          null,

        code:
          "ENTRY_HASH_MISMATCH",

        expected:
          expectedHash,

        actual:
          entry.hash,
      });
    }
  }

  return {
    version:
      LEARNING_AUDIT_V2_VERSION,

    valid:
      issues.length ===
      0,

    entryCount:
      entries.length,

    issueCount:
      issues.length,

    issues,

    headHash:
      entries.at(-1)
        ?.hash ??
      null,
  };
}

export function assertLearningAuditTrail(
  entries = [],
) {
  const result =
    verifyLearningAuditTrail(
      entries,
    );

  if (!result.valid) {
    const error =
      new Error(
        "Learning audit trail verification failed.",
      );

    error.code =
      "LEARNING_AUDIT_VERIFICATION_FAILED";

    error.issues =
      result.issues;

    throw error;
  }

  return result;
}

export function summarizeLearningAuditTrail(
  entries = [],
) {
  const verification =
    verifyLearningAuditTrail(
      entries,
    );

  const byEventType = {};
  const byActor = {};

  for (const entry of entries) {
    const eventType =
      normalizeText(
        entry?.eventType,
        "UNKNOWN",
      );

    const actor =
      normalizeText(
        entry?.actor,
        "UNKNOWN",
      );

    byEventType[eventType] =
      (
        byEventType[eventType] ??
        0
      ) +
      1;

    byActor[actor] =
      (
        byActor[actor] ??
        0
      ) +
      1;
  }

  return {
    version:
      LEARNING_AUDIT_V2_VERSION,

    valid:
      verification.valid,

    entryCount:
      entries.length,

    issueCount:
      verification.issueCount,

    firstTimestamp:
      entries[0]
        ?.timestamp ??
      null,

    latestTimestamp:
      entries.at(-1)
        ?.timestamp ??
      null,

    headHash:
      verification.headHash,

    byEventType,

    byActor,

    issues:
      verification.issues,
  };
}

export function findLearningAuditEntries({
  entries = [],
  eventType = null,
  actor = null,
  from = null,
  to = null,
  limit = null,
} = {}) {
  if (!Array.isArray(entries)) {
    throw new TypeError(
      "Learning audit entries must be an array.",
    );
  }

  const normalizedEventType =
    eventType === null
      ? null
      : normalizeText(
          eventType,
          "",
        ).toUpperCase();

  const normalizedActor =
    actor === null
      ? null
      : normalizeText(
          actor,
          "",
        );

  const fromMilliseconds =
    from === null
      ? null
      : Date.parse(
          normalizeTimestamp(
            from,
          ),
        );

  const toMilliseconds =
    to === null
      ? null
      : Date.parse(
          normalizeTimestamp(
            to,
          ),
        );

  const filtered =
    entries.filter(
      (
        entry,
      ) => {
        if (
          normalizedEventType &&
          entry.eventType !==
            normalizedEventType
        ) {
          return false;
        }

        if (
          normalizedActor &&
          entry.actor !==
            normalizedActor
        ) {
          return false;
        }

        const timestamp =
          Date.parse(
            entry.timestamp,
          );

        if (
          fromMilliseconds !==
            null &&
          timestamp <
            fromMilliseconds
        ) {
          return false;
        }

        if (
          toMilliseconds !==
            null &&
          timestamp >
            toMilliseconds
        ) {
          return false;
        }

        return true;
      },
    );

  if (
    limit === null ||
    limit === undefined
  ) {
    return clone(
      filtered,
    );
  }

  const normalizedLimit =
    Math.max(
      0,
      Math.floor(
        Number(limit) ||
        0,
      ),
    );

  return clone(
    filtered.slice(
      -normalizedLimit,
    ),
  );
}

export function createLearningAuditSnapshot({
  entries = [],
  createdAt =
    new Date().toISOString(),
  createdBy = "system",
} = {}) {
  const verification =
    assertLearningAuditTrail(
      entries,
    );

  const timestamp =
    normalizeTimestamp(
      createdAt,
    );

  return {
    version:
      LEARNING_AUDIT_V2_VERSION,

    schemaVersion:
      LEARNING_AUDIT_V2_SCHEMA_VERSION,

    createdAt:
      timestamp,

    createdBy:
      normalizeText(
        createdBy,
        "system",
      ),

    entryCount:
      entries.length,

    headHash:
      verification.headHash,

    snapshotHash:
      hashValue({
        createdAt:
          timestamp,

        createdBy:
          normalizeText(
            createdBy,
            "system",
          ),

        entryCount:
          entries.length,

        headHash:
          verification.headHash,
      }),
  };
}

export function verifyLearningAuditSnapshot({
  entries = [],
  snapshot,
} = {}) {
  if (
    !snapshot ||
    typeof snapshot !== "object" ||
    Array.isArray(snapshot)
  ) {
    throw new TypeError(
      "Learning audit snapshot is required.",
    );
  }

  const verification =
    verifyLearningAuditTrail(
      entries,
    );

  const expectedSnapshotHash =
    hashValue({
      createdAt:
        snapshot.createdAt,

      createdBy:
        snapshot.createdBy,

      entryCount:
        snapshot.entryCount,

      headHash:
        snapshot.headHash,
    });

  const issues = [
    ...verification.issues,
  ];

  if (
    snapshot.entryCount !==
    entries.length
  ) {
    issues.push({
      code:
        "SNAPSHOT_ENTRY_COUNT_MISMATCH",

      expected:
        entries.length,

      actual:
        snapshot.entryCount,
    });
  }

  if (
    snapshot.headHash !==
    verification.headHash
  ) {
    issues.push({
      code:
        "SNAPSHOT_HEAD_HASH_MISMATCH",

      expected:
        verification.headHash,

      actual:
        snapshot.headHash,
    });
  }

  if (
    snapshot.snapshotHash !==
    expectedSnapshotHash
  ) {
    issues.push({
      code:
        "SNAPSHOT_HASH_MISMATCH",

      expected:
        expectedSnapshotHash,

      actual:
        snapshot.snapshotHash,
    });
  }

  return {
    version:
      LEARNING_AUDIT_V2_VERSION,

    valid:
      issues.length ===
      0,

    issueCount:
      issues.length,

    issues,
  };
}

export class LearningAuditV2 {
  constructor({
    entries = [],
  } = {}) {
    if (!Array.isArray(entries)) {
      throw new TypeError(
        "Learning audit entries must be an array.",
      );
    }

    this.entries =
      clone(
        entries,
      );

    if (
      this.entries.length >
      0
    ) {
      assertLearningAuditTrail(
        this.entries,
      );
    }
  }

  append(input = {}) {
    this.entries =
      appendLearningAuditEntry({
        entries:
          this.entries,

        ...input,
      });

    return clone(
      this.entries.at(-1),
    );
  }

  list() {
    return clone(
      this.entries,
    );
  }

  verify() {
    return verifyLearningAuditTrail(
      this.entries,
    );
  }

  assert() {
    return assertLearningAuditTrail(
      this.entries,
    );
  }

  summary() {
    return summarizeLearningAuditTrail(
      this.entries,
    );
  }

  find(input = {}) {
    return findLearningAuditEntries({
      entries:
        this.entries,

      ...input,
    });
  }

  snapshot(input = {}) {
    return createLearningAuditSnapshot({
      entries:
        this.entries,

      ...input,
    });
  }

  reset() {
    this.entries = [];

    return [];
  }
}

export const learningAuditV2 =
  new LearningAuditV2();

export default appendLearningAuditEntry;