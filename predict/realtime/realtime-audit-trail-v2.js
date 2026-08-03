export const REALTIME_AUDIT_TRAIL_V2_VERSION =
  "realtime-audit-trail-v2";

function finiteOrNull(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return null;
  }

  const number =
    Number(value);

  return Number.isFinite(number)
    ? number
    : null;
}

function normalizeTimestamp(
  value,
  now,
) {
  const raw =
    value ??
    now();

  const parsed =
    typeof raw === "number"
      ? raw
      : Date.parse(raw);

  if (!Number.isFinite(parsed)) {
    throw new TypeError(
      "Realtime audit timestamp is invalid.",
    );
  }

  return parsed;
}

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

function normalizeArray(value) {
  return Array.isArray(value)
    ? [...value]
    : [];
}

function normalizeSeverity(value) {
  const severity =
    normalizeText(
      value,
      "INFO",
    ).toUpperCase();

  if (
    [
      "INFO",
      "WARNING",
      "HIGH",
      "CRITICAL",
    ].includes(severity)
  ) {
    return severity;
  }

  return "INFO";
}

function normalizeDecision(value) {
  const decision =
    normalizeText(
      value,
      "UNKNOWN",
    ).toUpperCase();

  if (
    [
      "ALLOW",
      "WAIT",
      "BLOCK",
      "CONFIRMED",
      "REJECTED",
      "EXECUTED",
      "CANCELLED",
      "UNKNOWN",
    ].includes(decision)
  ) {
    return decision;
  }

  return "UNKNOWN";
}

function stableStringify(value) {
  if (
    value === null ||
    typeof value !== "object"
  ) {
    return JSON.stringify(value);
  }

  if (Array.isArray(value)) {
    return (
      "[" +
      value
        .map(
          stableStringify,
        )
        .join(",") +
      "]"
    );
  }

  const keys =
    Object.keys(value)
      .sort();

  return (
    "{" +
    keys
      .map(
        (
          key,
        ) =>
          `${JSON.stringify(key)}:${stableStringify(value[key])}`,
      )
      .join(",") +
    "}"
  );
}

function createHash(input) {
  const text =
    String(input);

  let hash =
    2166136261;

  for (
    let index = 0;
    index < text.length;
    index += 1
  ) {
    hash ^=
      text.charCodeAt(index);

    hash =
      Math.imul(
        hash,
        16777619,
      );
  }

  return (
    hash >>> 0
  )
    .toString(16)
    .padStart(
      8,
      "0",
    );
}

function buildEntryId({
  timestamp,
  symbol,
  eventType,
  decision,
  sequence,
}) {
  const payload =
    [
      timestamp,
      symbol,
      eventType,
      decision,
      sequence,
    ].join(":");

  return (
    `audit-${createHash(payload)}`
  );
}

function deriveSeverity({
  eventType,
  decision,
  blockers,
}) {
  if (
    decision === "BLOCK" ||
    blockers.length > 0
  ) {
    return "CRITICAL";
  }

  if (
    decision === "WAIT" ||
    eventType === "ANOMALY"
  ) {
    return "HIGH";
  }

  if (
    decision === "CONFIRMED"
  ) {
    return "WARNING";
  }

  return "INFO";
}

function normalizeEntry({
  entry,
  index,
  now,
  previousHash,
}) {
  if (
    !entry ||
    typeof entry !== "object"
  ) {
    throw new TypeError(
      "Realtime audit entry must be an object.",
    );
  }

  const timestamp =
    normalizeTimestamp(
      entry.timestamp ??
      entry.createdAt,
      now,
    );

  const symbol =
    normalizeText(
      entry.symbol ??
      entry.instrument ??
      "UNKNOWN",
      "UNKNOWN",
    ).toUpperCase();

  const eventType =
    normalizeText(
      entry.eventType ??
      entry.type ??
      "REALTIME_DECISION",
      "REALTIME_DECISION",
    ).toUpperCase();

  const decision =
    normalizeDecision(
      entry.decision ??
      entry.status,
    );

  const blockers =
    normalizeArray(
      entry.blockers,
    ).map(
      (
        blocker,
      ) =>
        typeof blocker === "string"
          ? blocker
          : normalizeText(
              blocker?.code ??
              blocker?.name ??
              "UNKNOWN_BLOCKER",
              "UNKNOWN_BLOCKER",
            ),
    );

  const reasons =
    normalizeArray(
      entry.reasons ??
      entry.reason,
    );

  if (
    !reasons.length &&
    entry.reason
  ) {
    reasons.push(
      entry.reason,
    );
  }

  const source =
    normalizeText(
      entry.source ??
      "ARK_TERMINAL",
      "ARK_TERMINAL",
    ).toUpperCase();

  const actor =
    normalizeText(
      entry.actor ??
      entry.confirmedBy ??
      "SYSTEM",
      "SYSTEM",
    );

  const severity =
    normalizeSeverity(
      entry.severity ??
      deriveSeverity({
        eventType,
        decision,
        blockers,
      }),
    );

  const sequence =
    index + 1;

  const payload = {
    sequence,

    timestamp:
      new Date(
        timestamp,
      ).toISOString(),

    symbol,

    eventType,

    decision,

    severity,

    source,

    actor,

    reasons:
      reasons.map(
        (
          reason,
        ) =>
          normalizeText(
            reason,
            "UNKNOWN_REASON",
          ),
      ),

    blockers,

    gateScore:
      finiteOrNull(
        entry.gateScore,
      ),

    positionMultiplier:
      finiteOrNull(
        entry.positionMultiplier,
      ),

    orderQuantity:
      finiteOrNull(
        entry.orderQuantity ??
        entry.order?.quantity,
      ),

    orderValue:
      finiteOrNull(
        entry.orderValue ??
        entry.order?.estimatedValue,
      ),

    humanConfirmationRequired:
      entry.humanConfirmationRequired ??
      entry.humanConfirmation?.required ??
      false,

    humanConfirmed:
      entry.humanConfirmed ??
      entry.humanConfirmation?.confirmed ??
      false,

    metadata:
      entry.metadata ??
      {},
  };

  const entryId =
    normalizeText(
      entry.id,
      buildEntryId({
        timestamp,
        symbol,
        eventType,
        decision,
        sequence,
      }),
    );

  const hashPayload = {
    ...payload,

    entryId,

    previousHash,
  };

  const hash =
    createHash(
      stableStringify(
        hashPayload,
      ),
    );

  return {
    version:
      REALTIME_AUDIT_TRAIL_V2_VERSION,

    entryId,

    ...payload,

    previousHash,

    hash,
  };
}

function validateChain(entries) {
  const errors = [];

  for (
    let index = 0;
    index < entries.length;
    index += 1
  ) {
    const current =
      entries[index];

    const expectedPreviousHash =
      index === 0
        ? null
        : entries[index - 1].hash;

    if (
      current.previousHash !==
      expectedPreviousHash
    ) {
      errors.push({
        index,

        entryId:
          current.entryId,

        code:
          "PREVIOUS_HASH_MISMATCH",
      });
    }

    const hashPayload = {
      sequence:
        current.sequence,

      timestamp:
        current.timestamp,

      symbol:
        current.symbol,

      eventType:
        current.eventType,

      decision:
        current.decision,

      severity:
        current.severity,

      source:
        current.source,

      actor:
        current.actor,

      reasons:
        current.reasons,

      blockers:
        current.blockers,

      gateScore:
        current.gateScore,

      positionMultiplier:
        current.positionMultiplier,

      orderQuantity:
        current.orderQuantity,

      orderValue:
        current.orderValue,

      humanConfirmationRequired:
        current.humanConfirmationRequired,

      humanConfirmed:
        current.humanConfirmed,

      metadata:
        current.metadata,

      entryId:
        current.entryId,

      previousHash:
        current.previousHash,
    };

    const expectedHash =
      createHash(
        stableStringify(
          hashPayload,
        ),
      );

    if (
      current.hash !==
      expectedHash
    ) {
      errors.push({
        index,

        entryId:
          current.entryId,

        code:
          "ENTRY_HASH_MISMATCH",
      });
    }
  }

  return {
    valid:
      errors.length === 0,

    errors,
  };
}

export function buildRealtimeAuditTrail({
  entries = [],
  existingEntries = [],
  now = Date.now,
} = {}) {
  if (
    typeof now !== "function"
  ) {
    throw new TypeError(
      "Realtime audit clock must be a function.",
    );
  }

  if (!Array.isArray(entries)) {
    throw new TypeError(
      "Realtime audit entries must be an array.",
    );
  }

  if (!Array.isArray(existingEntries)) {
    throw new TypeError(
      "Realtime existing audit entries must be an array.",
    );
  }

  const normalizedExisting =
    existingEntries.map(
      (
        entry,
      ) => ({
        ...entry,
      }),
    );

  let previousHash =
    normalizedExisting.length
      ? normalizedExisting[
          normalizedExisting.length - 1
        ].hash
      : null;

  const startIndex =
    normalizedExisting.length;

  const newEntries =
    entries.map(
      (
        entry,
        index,
      ) => {
        const normalized =
          normalizeEntry({
            entry,

            index:
              startIndex +
              index,

            now,

            previousHash,
          });

        previousHash =
          normalized.hash;

        return normalized;
      },
    );

  const trail = [
    ...normalizedExisting,
    ...newEntries,
  ];

  const validation =
    validateChain(
      trail,
    );

  const decisions =
    trail.reduce(
      (
        summary,
        entry,
      ) => {
        summary[
          entry.decision
        ] =
          (
            summary[
              entry.decision
            ] ??
            0
          ) +
          1;

        return summary;
      },
      {},
    );

  return {
    version:
      REALTIME_AUDIT_TRAIL_V2_VERSION,

    ready:
      trail.length > 0,

    entryCount:
      trail.length,

    addedCount:
      newEntries.length,

    chainValid:
      validation.valid,

    chainErrors:
      validation.errors,

    latestHash:
      trail.length
        ? trail[
            trail.length - 1
          ].hash
        : null,

    entries:
      trail,

    summary: {
      decisions,

      blockedCount:
        trail.filter(
          (
            entry,
          ) =>
            entry.decision ===
            "BLOCK",
        ).length,

      confirmedCount:
        trail.filter(
          (
            entry,
          ) =>
            entry.humanConfirmed ===
            true,
        ).length,

      criticalCount:
        trail.filter(
          (
            entry,
          ) =>
            entry.severity ===
            "CRITICAL",
        ).length,

      symbols:
        [
          ...new Set(
            trail.map(
              (
                entry,
              ) =>
                entry.symbol,
            ),
          ),
        ],
    },
  };
}

export function verifyRealtimeAuditTrail(
  trail = [],
) {
  if (!Array.isArray(trail)) {
    throw new TypeError(
      "Realtime audit trail must be an array.",
    );
  }

  return validateChain(
    trail,
  );
}

export function createAuditEntryFromDecision({
  decision,
  executionPlan = null,
  actor = "SYSTEM",
  timestamp = null,
} = {}) {
  if (
    !decision ||
    typeof decision !== "object"
  ) {
    throw new TypeError(
      "Realtime decision is required.",
    );
  }

  return {
    timestamp,

    symbol:
      decision.symbol,

    eventType:
      executionPlan
        ? "EXECUTION_PLAN"
        : "REALTIME_DECISION",

    decision:
      executionPlan
        ?.status ??
      decision.decision,

    severity:
      decision.decision ===
        "BLOCK"
        ? "CRITICAL"
        : decision.decision ===
            "WAIT"
          ? "HIGH"
          : "INFO",

    source:
      "REALTIME_DECISION_GATE_V2",

    actor,

    reasons: [
      decision.reason,
    ],

    blockers:
      decision.blockers ??
      [],

    gateScore:
      decision.gateScore,

    positionMultiplier:
      decision.positionMultiplier,

    orderQuantity:
      executionPlan
        ?.order
        ?.quantity ??
      null,

    orderValue:
      executionPlan
        ?.order
        ?.estimatedValue ??
      null,

    humanConfirmationRequired:
      executionPlan
        ?.humanConfirmation
        ?.required ??
      false,

    humanConfirmed:
      executionPlan
        ?.humanConfirmation
        ?.confirmed ??
      false,

    metadata: {
      direction:
        decision.direction,

      gateVersion:
        decision.version,

      executionPlanVersion:
        executionPlan
          ?.version ??
        null,
    },
  };
}

export class RealtimeAuditTrailV2 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };

    this.entries =
      Array.isArray(
        config.entries,
      )
        ? [
            ...config.entries,
          ]
        : [];
  }

  append(entries = []) {
    const result =
      buildRealtimeAuditTrail({
        entries,

        existingEntries:
          this.entries,

        now:
          this.config.now ??
          Date.now,
      });

    this.entries =
      result.entries;

    return result;
  }

  verify() {
    return verifyRealtimeAuditTrail(
      this.entries,
    );
  }

  snapshot() {
    return [
      ...this.entries,
    ];
  }
}

export const realtimeAuditTrailV2 =
  new RealtimeAuditTrailV2();

export default buildRealtimeAuditTrail;