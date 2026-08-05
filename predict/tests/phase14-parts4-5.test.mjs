import test from "node:test";
import assert from "node:assert/strict";

import { auditPhase14Release } from "../release/phase14-release-audit-v1.js";
import { buildV1ReleaseManifest } from "../release/v1-release-manifest.js";

function readyInput() {
  return {
    unifiedDashboard: { version: "unified-dashboard-v1", mobileReady: true },
    controlCenter: { overallStatus: "HEALTHY" },
    paperTrading: {
      liveExecutionAllowed: false,
      brokerConnected: false,
      controls: { killSwitchActive: false },
    },
    learning: {
      humanApprovalRequired: true,
      automaticPromotionAllowed: false,
    },
    dataValidation: { futureLeakDetected: false },
    uiState: {
      version: "ui-state-v1",
      supports: { loading: true, error: true, empty: true },
    },
    cache: {
      version: "performance-cache-v1",
      deduplicationEnabled: true,
      ttlEnabled: true,
    },
    ci: { predictTests: true, discoveryTests: true },
    environment: { openAiConfigured: true },
    build: { version: "1.0.0", commit: "abc123" },
  };
}

test("Phase14 release audit is ready only when blocker checks pass", () => {
  const result = auditPhase14Release(readyInput());
  assert.equal(result.ready, true);
  assert.equal(result.status, "READY");
  assert.deepEqual(result.blockers, []);
  assert.equal(result.safety.liveTradingEnabled, false);
});

test("Phase14 release audit blocks future leak and unsafe paper trading", () => {
  const input = readyInput();
  input.dataValidation.futureLeakDetected = true;
  input.paperTrading.liveExecutionAllowed = true;
  const result = auditPhase14Release(input);
  assert.equal(result.ready, false);
  assert.equal(result.status, "BLOCKED");
  assert.ok(result.blockers.includes("future-leak"));
  assert.ok(result.blockers.includes("paper-only"));
});

test("v1 release manifest remains paper-only and approval-gated", () => {
  const manifest = buildV1ReleaseManifest({ commit: "abc123", buildId: "build-1" });
  assert.equal(manifest.version, "1.0.0");
  assert.equal(manifest.channel, "stable");
  assert.equal(manifest.safety.liveTradingEnabled, false);
  assert.equal(manifest.safety.brokerConnectionEnabled, false);
  assert.equal(manifest.safety.humanApprovalRequired, true);
});
