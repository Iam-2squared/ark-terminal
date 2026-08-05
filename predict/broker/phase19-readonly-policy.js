export const PHASE19_READONLY_POLICY_VERSION =
  "phase19-readonly-policy-v1";

export const PHASE19_READONLY_POLICY =
  Object.freeze({
    connectionMode: "READ_ONLY",
    allowLiveTrading: false,
    allowOrderCreation: false,
    allowOrderPreview: false,
    allowOrderTransmission: false,
    allowCancellation: false,
    allowAccountMutation: false,
    requireCredentialIsolation: true,
    requireAuditLogging: true,
    requireHumanApproval: true,
    permittedOperations: Object.freeze([
      "CONNECT",
      "DISCONNECT",
      "READ_ACCOUNT",
      "READ_BALANCES",
      "READ_POSITIONS",
      "READ_ORDERS",
      "READ_EXECUTIONS",
      "RECONCILE",
    ]),
  });

export function assertPhase19ReadonlyOperation(operation) {
  const normalized = String(operation || "").toUpperCase();

  if (!PHASE19_READONLY_POLICY.permittedOperations.includes(normalized)) {
    const error = new Error(
      `Phase19 read-only policy blocked operation: ${normalized || "UNKNOWN"}`,
    );
    error.code = "PHASE19_READONLY_OPERATION_BLOCKED";
    error.operation = normalized || null;
    error.transmitted = false;
    throw error;
  }

  return {
    allowed: true,
    operation: normalized,
    transmitted: false,
    policyVersion: PHASE19_READONLY_POLICY_VERSION,
  };
}

export function createPhase19ReadonlySafetyState() {
  return {
    policyVersion: PHASE19_READONLY_POLICY_VERSION,
    mode: PHASE19_READONLY_POLICY.connectionMode,
    connected: false,
    authenticated: false,
    liveTradingEnabled: false,
    brokerExecutionAllowed: false,
    orderCreationAllowed: false,
    orderTransmissionAllowed: false,
    transmitted: false,
    humanApprovalRequired: true,
  };
}
