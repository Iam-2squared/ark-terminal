import test from "node:test";
import assert from "node:assert/strict";

import {
  RealtimeAuditTrailV2,
  buildRealtimeAuditTrail,
  createAuditEntryFromDecision,
  verifyRealtimeAuditTrail,
} from "../realtime/realtime-audit-trail-v2.js";

const NOW =
  Date.parse(
    "2026-08-03T11:00:00.000Z",
  );

function decisionInput() {
  return {
    version:
      "realtime-decision-gate-v2",

    symbol:
      "285A",

    direction:
      "BUY",

    decision:
      "ALLOW",

    reason:
      "ALL_REALTIME_DECISION_GATES_PASSED",

    gateScore:
      96,

    positionMultiplier:
      65,

    blockers:
      [],
  };
}

function planInput() {
  return {
    version:
      "realtime-execution-planner-v2",

    status:
      "AWAITING_HUMAN_CONFIRMATION",

    order: {
      quantity:
        200,

      estimatedValue:
        100000,
    },

    humanConfirmation: {
      required:
        true,

      confirmed:
        false,
    },
  };
}

test(
  "Audit trail creates chained entries",
  () => {
    const result =
      buildRealtimeAuditTrail({
        entries: [
          {
            symbol:
              "285A",

            eventType:
              "REALTIME_DECISION",

            decision:
              "ALLOW",

            timestamp:
              NOW,
          },

          {
            symbol:
              "285A",

            eventType:
              "EXECUTION_PLAN",

            decision:
              "WAIT",

            timestamp:
              NOW + 1000,
          },
        ],

        now:
          () => NOW,
      });

    assert.equal(
      result.version,
      "realtime-audit-trail-v2",
    );

    assert.equal(
      result.entryCount,
      2,
    );

    assert.equal(
      result.chainValid,
      true,
    );

    assert.equal(
      result.entries[0]
        .previousHash,
      null,
    );

    assert.equal(
      result.entries[1]
        .previousHash,
      result.entries[0]
        .hash,
    );
  },
);

test(
  "Audit trail derives critical severity for blocked decisions",
  () => {
    const result =
      buildRealtimeAuditTrail({
        entries: [
          {
            symbol:
              "7203",

            decision:
              "BLOCK",

            blockers: [
              "RISK_LIMIT",
            ],

            timestamp:
              NOW,
          },
        ],

        now:
          () => NOW,
      });

    assert.equal(
      result.entries[0]
        .severity,
      "CRITICAL",
    );

    assert.equal(
      result.summary
        .blockedCount,
      1,
    );
  },
);

test(
  "Audit trail detects tampering",
  () => {
    const result =
      buildRealtimeAuditTrail({
        entries: [
          {
            symbol:
              "285A",

            decision:
              "ALLOW",

            timestamp:
              NOW,
          },
        ],

        now:
          () => NOW,
      });

    const tampered =
      result.entries.map(
        (
          entry,
        ) => ({
          ...entry,
        }),
      );

    tampered[0]
      .decision =
      "BLOCK";

    const verification =
      verifyRealtimeAuditTrail(
        tampered,
      );

    assert.equal(
      verification.valid,
      false,
    );

    assert.ok(
      verification.errors.some(
        (
          error,
        ) =>
          error.code ===
          "ENTRY_HASH_MISMATCH",
      ),
    );
  },
);

test(
  "Audit entry is created from realtime decision",
  () => {
    const entry =
      createAuditEntryFromDecision({
        decision:
          decisionInput(),

        executionPlan:
          planInput(),

        actor:
          "reviewer",

        timestamp:
          NOW,
      });

    assert.equal(
      entry.symbol,
      "285A",
    );

    assert.equal(
      entry.eventType,
      "EXECUTION_PLAN",
    );

    assert.equal(
      entry.orderQuantity,
      200,
    );

    assert.equal(
      entry.humanConfirmationRequired,
      true,
    );
  },
);

test(
  "Audit trail supports appending to existing chain",
  () => {
    const first =
      buildRealtimeAuditTrail({
        entries: [
          {
            symbol:
              "285A",

            decision:
              "ALLOW",

            timestamp:
              NOW,
          },
        ],

        now:
          () => NOW,
      });

    const second =
      buildRealtimeAuditTrail({
        existingEntries:
          first.entries,

        entries: [
          {
            symbol:
              "285A",

            decision:
              "CONFIRMED",

            humanConfirmed:
              true,

            timestamp:
              NOW + 1000,
          },
        ],

        now:
          () => NOW,
      });

    assert.equal(
      second.entryCount,
      2,
    );

    assert.equal(
      second.addedCount,
      1,
    );

    assert.equal(
      second.chainValid,
      true,
    );

    assert.equal(
      second.summary
        .confirmedCount,
      1,
    );
  },
);

test(
  "Audit trail handles empty input",
  () => {
    const result =
      buildRealtimeAuditTrail({
        entries:
          [],

        now:
          () => NOW,
      });

    assert.equal(
      result.ready,
      false,
    );

    assert.equal(
      result.entryCount,
      0,
    );

    assert.equal(
      result.latestHash,
      null,
    );
  },
);

test(
  "Audit trail validates input",
  () => {
    assert.throws(
      () =>
        buildRealtimeAuditTrail({
          entries:
            "invalid",
        }),

      /entries must be an array/,
    );

    assert.throws(
      () =>
        buildRealtimeAuditTrail({
          now:
            NOW,
        }),

      /clock must be a function/,
    );
  },
);

test(
  "Audit trail class appends and verifies",
  () => {
    const audit =
      new RealtimeAuditTrailV2({
        now:
          () => NOW,
      });

    const first =
      audit.append([
        {
          symbol:
            "285A",

          decision:
            "ALLOW",

          timestamp:
            NOW,
        },
      ]);

    assert.equal(
      first.entryCount,
      1,
    );

    const second =
      audit.append([
        {
          symbol:
            "285A",

          decision:
            "CONFIRMED",

          humanConfirmed:
            true,

          timestamp:
            NOW + 1000,
        },
      ]);

    assert.equal(
      second.entryCount,
      2,
    );

    assert.equal(
      audit.verify()
        .valid,
      true,
    );

    assert.equal(
      audit.snapshot()
        .length,
      2,
    );
  },
);