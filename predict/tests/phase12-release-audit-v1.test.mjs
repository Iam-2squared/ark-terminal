import test from "node:test";
import assert from "node:assert/strict";

import { auditPhase12Release } from "../release/phase12-release-audit-v1.js";

function readyInput() {
  return {
    rankingAdapter: { version: "discovery-ranking-adapter-v2" },
    discoveryFinal: { version: "discovery-final-v1", mobileReady: true },
    predictionLabFinal: {
      version: "prediction-lab-final-v1",
      mobileReady: true,
      candidate: {
        humanApprovalRequired: true,
        productionUpdateAllowed: false,
      },
    },
    paperTradingFinal: {
      version: "paper-trading-final-v1",
      mobileReady: true,
      liveExecutionAllowed: false,
      brokerConnected: false,
    },
    ci: { predictTests: true, discoveryTests: true },
  };
}

test("release audit passes only when all final surfaces and safety gates pass", () => {
  const audit = auditPhase12Release(readyInput());

  assert.equal(audit.status, "READY");
  assert.equal(audit.ready, true);
  assert.equal(audit.passedCount, audit.totalCount);
  assert.deepEqual(audit.blockers, []);
  assert.equal(audit.releaseRules.liveTradingEnabled, false);
  assert.equal(audit.releaseRules.automaticModelPromotionEnabled, false);
});

test("release audit blocks unsafe paper trading configuration", () => {
  const input = readyInput();
  input.paperTradingFinal.liveExecutionAllowed = true;

  const audit = auditPhase12Release(input);

  assert.equal(audit.status, "BLOCKED");
  assert.equal(audit.ready, false);
  assert.ok(audit.blockers.includes("paper-only-safety"));
});

test("release audit blocks missing CI evidence", () => {
  const input = readyInput();
  input.ci.discoveryTests = false;

  const audit = auditPhase12Release(input);

  assert.equal(audit.status, "BLOCKED");
  assert.ok(audit.blockers.includes("ci-discovery"));
});
