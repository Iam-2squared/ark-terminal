import test from "node:test";
import assert from "node:assert/strict";

import { ForwardTestAutomationV1 } from "../validation/forward-test-automation-v1.js";
import { optimizeCalibration } from "../learning/calibration-optimizer-v1.js";
import { auditV101StableRelease, buildV101StableManifest } from "../release/v1-0-1-stable-release.js";

test("forward automation supports dry run, duplicate prevention, approval, and kill switch", () => {
  const now = () => new Date("2026-08-05T01:00:00.000Z");
  const runner = new ForwardTestAutomationV1({ now, marketHours: () => true });
  const signal = { id: "s1", symbol: "7203.T", action: "BUY", quantity: 100, price: 3000 };

  assert.equal(runner.submit(signal).status, "DRY_RUN_READY");
  assert.equal(runner.submit(signal).reason, "DUPLICATE_ORDER");

  runner.setMode("MANUAL_APPROVAL");
  assert.equal(runner.submit({ ...signal, id: "s2" }).status, "APPROVAL_REQUIRED");
  const approved = runner.approve("s2", true);
  assert.equal(approved.status, "PAPER_FILLED");
  assert.deepEqual(approved.pipeline, ["ORDER", "FILL", "PORTFOLIO", "TRADE_MEMORY", "ACCURACY"]);
  assert.equal(approved.liveExecutionAllowed, false);

  runner.activateKillSwitch("test");
  assert.equal(runner.submit({ ...signal, id: "s3" }).reason, "KILL_SWITCH_ACTIVE");
});

test("forward automation blocks closed market and produces a daily summary", () => {
  const runner = new ForwardTestAutomationV1({ marketHours: () => false });
  const result = runner.submit({ id: "closed", symbol: "9984.T", action: "BUY" });
  assert.equal(result.reason, "MARKET_CLOSED");
  assert.equal(runner.dailySummary().liveExecutionAllowed, false);
});

test("calibration optimizer remains review-only", () => {
  const records = Array.from({ length: 40 }, (_, index) => ({
    action: index % 4 === 0 ? "NO_TRADE" : "BUY",
    score: 40 + (index % 5) * 10,
    confidence: 40 + (index % 5) * 10,
    return: index % 3 === 0 ? -0.01 : 0.02,
    sector: index % 2 ? "TECH" : "AUTO",
    marketRegime: index % 2 ? "BULL" : "BEAR",
  }));
  const result = optimizeCalibration({ records });
  assert.equal(result.status, "REVIEW_REQUIRED");
  assert.equal(result.productionUpdateAllowed, false);
  assert.equal(result.automaticPromotionAllowed, false);
  assert.equal(result.humanApprovalRequired, true);
  assert.ok(result.candidates.length > 0);
});

test("v1.0.1 audit passes safe validated configuration", () => {
  const audit = auditV101StableRelease({
    smokeTest: { status: "READY" },
    historicalValidation: { status: "READY", dataQuality: { futureLeakDetected: false } },
    forwardTest: { liveExecutionAllowed: false, brokerConnected: false, killSwitchActive: false },
    calibration: { humanApprovalRequired: true, productionUpdateAllowed: false },
    ci: { predictTests: true, discoveryTests: true },
    deployment: { vercelReady: true },
    build: { version: "1.0.1", commit: "abc123" },
  });
  assert.equal(audit.status, "READY");
  assert.equal(audit.ready, true);
  assert.deepEqual(audit.blockers, []);

  const manifest = buildV101StableManifest({ commit: "abc123", buildId: "build-101" });
  assert.equal(manifest.version, "1.0.1");
  assert.equal(manifest.safety.liveTradingEnabled, false);
  assert.equal(manifest.safety.humanApprovalRequired, true);
});

test("v1.0.1 audit blocks unsafe or unvalidated state", () => {
  const audit = auditV101StableRelease({
    smokeTest: { status: "BLOCKED" },
    historicalValidation: { status: "BLOCKED", dataQuality: { futureLeakDetected: true } },
    forwardTest: { liveExecutionAllowed: true, brokerConnected: true },
    calibration: { humanApprovalRequired: false, productionUpdateAllowed: true },
    build: { version: "1.0.0" },
  });
  assert.equal(audit.status, "BLOCKED");
  assert.equal(audit.ready, false);
  assert.ok(audit.blockers.includes("forward-test-paper-only"));
  assert.ok(audit.blockers.includes("calibration-approval-gate"));
});
