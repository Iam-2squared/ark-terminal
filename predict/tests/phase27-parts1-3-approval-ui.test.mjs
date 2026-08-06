import assert from "node:assert/strict";
import test from "node:test";

import { buildOrderCandidateView } from "../approval/order-candidate-view.js";
import { createHumanApprovalSession, recordApproval } from "../approval/human-approval-session.js";
import { evaluateTwoStepConfirmation } from "../approval/two-step-confirmation.js";

test("Phase27 Part1 builds a complete human-review candidate without enabling execution", () => {
  const view = buildOrderCandidateView({
    proposal: {
      proposal: {
        symbol: "7203.T",
        side: "BUY",
        quantity: 100,
        orderType: "LIMIT",
        referencePrice: 3000,
        limitPrice: 2995,
        stopLossPrice: 2910,
        takeProfitPrice: 3180,
        maxLoss: 9000,
        rationale: ["trend", "liquidity"],
      },
      blockers: [],
    },
    analysis: { confidence: 0.72, marketRegime: "bull", liquidityStatus: "pass" },
    costs: { feePercent: 0.1, slippagePercent: 0.2 },
    risk: { level: "medium" },
  });

  assert.equal(view.status, "READY_FOR_HUMAN_REVIEW");
  assert.equal(view.candidate.symbol, "7203.T");
  assert.equal(view.candidate.maxLoss, 9000);
  assert.equal(view.safety.brokerWriteAllowed, false);
  assert.equal(view.safety.orderCreationAllowed, false);
});

test("Phase27 Part2 requires valid identity, expiry and unchanged candidate hash", () => {
  const session = createHumanApprovalSession({
    candidateId: "candidate-1",
    candidateHash: "hash-a",
    expiresAt: "2026-08-06T08:00:00Z",
  });
  const approved = recordApproval(session, {
    actorId: "human-1",
    step: 1,
    approvedAt: "2026-08-06T07:00:00Z",
    candidateHash: "hash-a",
  });

  assert.equal(approved.status, "AWAITING_FINAL_CONFIRMATION");
  assert.equal(approved.approvals.length, 1);
  assert.equal(approved.safety.executionAllowed, false);

  const changed = recordApproval(approved, {
    actorId: "human-1",
    step: 2,
    approvedAt: "2026-08-06T07:05:00Z",
    candidateHash: "hash-b",
  });
  assert.equal(changed.status, "BLOCKED");
  assert.ok(changed.blockers.includes("CANDIDATE_CHANGED_REAPPROVAL_REQUIRED"));
});

test("Phase27 Part3 only reaches DRY_RUN_READY after ordered two-step approval", () => {
  let session = createHumanApprovalSession({
    candidateId: "candidate-2",
    candidateHash: "hash-c",
    expiresAt: "2026-08-06T09:00:00Z",
  });
  session = recordApproval(session, {
    actorId: "human-1",
    step: 1,
    approvedAt: "2026-08-06T07:00:00Z",
    candidateHash: "hash-c",
  });
  session = recordApproval(session, {
    actorId: "human-1",
    step: 2,
    approvedAt: "2026-08-06T07:01:00Z",
    candidateHash: "hash-c",
  });

  const gate = evaluateTwoStepConfirmation(session);
  assert.equal(gate.status, "DRY_RUN_READY");
  assert.equal(gate.auditEvents.length, 2);
  assert.equal(gate.safety.brokerWriteAllowed, false);
  assert.equal(gate.safety.liveTradingAllowed, false);
});
