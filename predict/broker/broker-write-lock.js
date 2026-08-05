import {
  BROKER_MODES,
} from "./broker-adapter-contract.js";

export const BROKER_WRITE_LOCK_VERSION =
  "broker-write-lock-v1";

export const BROKER_WRITE_LOCK =
  Object.freeze({
    status: "LOCKED",
    liveTradingEnabled: false,
    allowLiveOrderSubmission: false,
    allowLiveOrderCancellation: false,
    failClosedOnUnknownMode: true,
    permittedWriteModes: Object.freeze([
      BROKER_MODES.PAPER,
      BROKER_MODES.DRY_RUN,
    ]),
    releaseStage: "NOT_APPROVED",
    releaseRequiresCodeChange: true,
    releaseRequirements: Object.freeze([
      "stable_paper_trading_results",
      "validated_accuracy_and_risk_metrics",
      "semi_automatic_human_approval_stage",
      "explicit_owner_approval",
    ]),
  });

function normalizeOperation(operation) {
  return String(operation || "BROKER_WRITE")
    .trim()
    .toUpperCase();
}

export function evaluateBrokerWriteLock({
  adapterInfo = {},
  operation = "BROKER_WRITE",
} = {}) {
  const mode =
    String(adapterInfo?.mode || "")
      .trim()
      .toLowerCase();

  const reportsLiveExecution =
    adapterInfo?.liveTradingEnabled === true;

  const isLive =
    mode === BROKER_MODES.LIVE ||
    reportsLiveExecution;

  const allowed =
    !isLive &&
    BROKER_WRITE_LOCK.permittedWriteModes
      .includes(mode);

  return {
    allowed,
    blocked: !allowed,
    operation: normalizeOperation(operation),
    mode: mode || null,
    adapterReportsLiveExecution:
      reportsLiveExecution,
    reason: allowed
      ? null
      : isLive
        ? "live_broker_execution_locked"
        : "broker_write_mode_not_allowed",
    transmitted: false,
    lockVersion: BROKER_WRITE_LOCK_VERSION,
    lockStatus: BROKER_WRITE_LOCK.status,
    releaseStage: BROKER_WRITE_LOCK.releaseStage,
  };
}

export function createBrokerWriteSafetyState() {
  return {
    version: BROKER_WRITE_LOCK_VERSION,
    status: BROKER_WRITE_LOCK.status,
    liveTradingEnabled: false,
    brokerExecutionAllowed: false,
    orderSubmissionAllowed: false,
    orderCancellationAllowed: false,
    transmitted: false,
    releaseStage: BROKER_WRITE_LOCK.releaseStage,
  };
}

export const BrokerWriteLockInternals = {
  normalizeOperation,
};
