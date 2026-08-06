const RELEASE_SAFETY = Object.freeze({
  mode: "READ_ONLY_PAPER_RELEASE",
  brokerWriteAllowed: false,
  liveTradingAllowed: false,
  orderCreationAllowed: false,
  orderTransmissionAllowed: false,
  orderCancellationAllowed: false,
  orderModificationAllowed: false,
  excelOrderWriteAllowed: false,
  orderTriggerWriteAllowed: false,
  automaticCandidateCreationAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  humanApprovalRequired: true,
});

function finite(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function average(values = []) {
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
}

export function buildPaperOperationsSnapshot({ positions = [], orders = [], cash = 0, asOf = new Date().toISOString() } = {}) {
  const normalizedOrders = orders.map((order, index) => ({
    id: order.id ?? `paper-${index}`,
    symbol: String(order.symbol ?? "UNKNOWN").toUpperCase(),
    side: String(order.side ?? "HOLD").toUpperCase(),
    quantity: Math.max(0, finite(order.quantity, 0)),
    limitPrice: finite(order.limitPrice, null),
    status: String(order.status ?? "PENDING").toUpperCase(),
    filledQuantity: Math.max(0, finite(order.filledQuantity, 0)),
    averageFillPrice: finite(order.averageFillPrice, null),
    paperOnly: true,
  }));
  const normalizedPositions = positions.map((position) => ({
    symbol: String(position.symbol ?? "UNKNOWN").toUpperCase(),
    quantity: finite(position.quantity, 0),
    averagePrice: finite(position.averagePrice, 0),
    markPrice: finite(position.markPrice, 0),
    unrealizedPnl: finite(position.unrealizedPnl, 0),
    paperOnly: true,
  }));
  return {
    asOf,
    cash: finite(cash, 0),
    orders: normalizedOrders,
    positions: normalizedPositions,
    pendingOrders: normalizedOrders.filter((order) => order.status === "PENDING").length,
    partiallyFilledOrders: normalizedOrders.filter((order) => order.status === "PARTIALLY_FILLED").length,
    brokerWrites: 0,
    liveOrders: 0,
    safety: { ...RELEASE_SAFETY },
  };
}

export function buildRiskAndAuditReport({ snapshots = [], limits = {}, health = {} } = {}) {
  const dailyLossLimit = Math.abs(finite(limits.dailyLossLimit, 0.03));
  const maxDrawdownLimit = Math.abs(finite(limits.maxDrawdownLimit, 0.15));
  const stale = health.dataFresh === false;
  const rssDisconnected = health.rssConnected === false;
  const bridgeDisconnected = health.bridgeConnected === false;
  const netPnls = snapshots.map((snapshot) => finite(snapshot.netPnl, 0));
  const totalNetPnl = netPnls.reduce((sum, value) => sum + value, 0);
  const worstDailyLoss = netPnls.length ? Math.min(...netPnls) : 0;
  const maxDrawdown = Math.max(0, ...snapshots.map((snapshot) => Math.abs(finite(snapshot.drawdown, 0))));
  const blockers = [];
  if (stale) blockers.push("STALE_DATA");
  if (rssDisconnected) blockers.push("RSS_DISCONNECTED");
  if (bridgeDisconnected) blockers.push("BRIDGE_DISCONNECTED");
  if (Math.abs(Math.min(0, worstDailyLoss)) > dailyLossLimit) blockers.push("DAILY_LOSS_LIMIT_BREACH");
  if (maxDrawdown > maxDrawdownLimit) blockers.push("MAX_DRAWDOWN_LIMIT_BREACH");
  return {
    status: blockers.length ? "HALTED" : "READ_ONLY_HEALTHY",
    blockers,
    totalNetPnl,
    averageNetPnl: average(netPnls),
    worstDailyLoss,
    maxDrawdown,
    killSwitchRequired: blockers.length > 0,
    brokerWrites: 0,
    liveOrders: 0,
    safety: { ...RELEASE_SAFETY },
  };
}

export function buildReleaseReadinessDashboard({ operations, riskReport, validation = {}, resilience = {} } = {}) {
  const blockers = [
    ...(riskReport?.blockers ?? []),
    ...(validation.outOfSamplePassed === false ? ["OOS_VALIDATION_FAILED"] : []),
    ...(validation.auditPassed === false ? ["AUDIT_VALIDATION_FAILED"] : []),
    ...(resilience.backupVerified === false ? ["BACKUP_NOT_VERIFIED"] : []),
    ...(resilience.restoreVerified === false ? ["RESTORE_NOT_VERIFIED"] : []),
    ...(resilience.recoveryDrillPassed === false ? ["RECOVERY_DRILL_FAILED"] : []),
  ];
  return {
    status: blockers.length ? "NOT_RELEASE_READY" : "READY_FOR_HUMAN_RELEASE_REVIEW",
    blockers,
    operations,
    riskReport,
    validation,
    resilience,
    automaticReleaseAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    brokerWrites: 0,
    liveOrders: 0,
    safety: { ...RELEASE_SAFETY },
  };
}

export function runPhase33To39ReadOnlyRelease(input = {}) {
  const operations = buildPaperOperationsSnapshot(input.operations ?? {});
  const riskReport = buildRiskAndAuditReport(input.risk ?? {});
  const dashboard = buildReleaseReadinessDashboard({
    operations,
    riskReport,
    validation: input.validation ?? {},
    resilience: input.resilience ?? {},
  });
  return {
    phaseRange: "33-39",
    status: dashboard.status,
    operations,
    riskReport,
    dashboard,
    realOrderPathImplemented: false,
    brokerWrites: 0,
    liveOrders: 0,
    safety: { ...RELEASE_SAFETY },
  };
}

export { RELEASE_SAFETY };
