export const DRY_RUN_VERSION = "phase27-dry-run-v1";

function freezeDeep(value) {
  if (value && typeof value === "object" && !Object.isFrozen(value)) {
    Object.freeze(value);
    for (const child of Object.values(value)) freezeDeep(child);
  }
  return value;
}

export function buildDryRunRecord(input = {}) {
  const approval = input.approval ?? {};
  const risk = input.risk ?? {};
  const killSwitch = input.killSwitch ?? {};
  const candidate = input.candidate ?? {};
  const blockers = [];

  if (approval.status !== "DRY_RUN_READY") blockers.push("TWO_STEP_APPROVAL_INCOMPLETE");
  if (risk.status !== "DRY_RUN_ALLOWED") blockers.push("RISK_GOVERNOR_BLOCKED");
  if (killSwitch.status !== "ARMED") blockers.push("KILL_SWITCH_HALTED");
  if (!candidate.symbol) blockers.push("SYMBOL_MISSING");
  if (!candidate.side) blockers.push("SIDE_MISSING");
  if (!(Number(candidate.quantity) > 0)) blockers.push("QUANTITY_INVALID");
  if (!(Number(candidate.limitPrice ?? candidate.price) > 0)) blockers.push("PRICE_INVALID");

  const record = {
    version: DRY_RUN_VERSION,
    status: blockers.length ? "BLOCKED" : "DRY_RUN_COMPLETED",
    blockers,
    generatedAt: input.generatedAt ?? new Date().toISOString(),
    candidate: {
      symbol: candidate.symbol ?? null,
      side: candidate.side ?? null,
      quantity: Number(candidate.quantity ?? 0),
      orderType: candidate.orderType ?? "LIMIT",
      limitPrice: Number(candidate.limitPrice ?? candidate.price ?? 0),
      stopLossPrice: Number(candidate.stopLossPrice ?? 0) || null,
      takeProfitPrice: Number(candidate.takeProfitPrice ?? 0) || null,
      maxLoss: Number(candidate.maxLoss ?? 0) || null,
    },
    approvals: {
      status: approval.status ?? null,
      firstApprovedBy: approval.firstApprovedBy ?? null,
      finalApprovedBy: approval.finalApprovedBy ?? null,
      candidateHash: approval.candidateHash ?? null,
    },
    risk: {
      status: risk.status ?? null,
      blockers: risk.blockers ?? [],
      limits: risk.limits ?? {},
    },
    killSwitch: {
      status: killSwitch.status ?? null,
      reasons: killSwitch.reasons ?? [],
    },
    intendedBrokerPayload: {
      symbol: candidate.symbol ?? null,
      side: candidate.side ?? null,
      quantity: Number(candidate.quantity ?? 0),
      orderType: candidate.orderType ?? "LIMIT",
      limitPrice: Number(candidate.limitPrice ?? candidate.price ?? 0),
    },
    sideEffects: {
      brokerWrites: 0,
      liveOrders: 0,
      cancellations: 0,
      modifications: 0,
    },
    safety: {
      mode: "DRY_RUN_ONLY",
      brokerWriteAllowed: false,
      liveTradingAllowed: false,
      orderCreationAllowed: false,
      orderCancellationAllowed: false,
      orderModificationAllowed: false,
      humanApprovalRequired: true,
    },
  };

  return freezeDeep(record);
}

export default buildDryRunRecord;
