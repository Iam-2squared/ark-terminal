import { SHADOW_SAFETY } from "./shadow-forward-operations.js";

function finite(value, fallback = 0) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
}

function assertShadowSafety(record) {
  const safety = record?.safety ?? {};
  if (safety.brokerWriteAllowed !== false || safety.liveTradingAllowed !== false) {
    throw new Error("shadow operations require broker and live trading writes to remain disabled");
  }
}

function summarizeEvaluations(evaluations = []) {
  const settled = evaluations.filter((item) => item?.status === "EVALUATED");
  const wins = settled.filter((item) => item.directionCorrect === true).length;
  const grossProfit = settled.filter((item) => finite(item.netPnl) > 0).reduce((sum, item) => sum + finite(item.netPnl), 0);
  const grossLoss = Math.abs(settled.filter((item) => finite(item.netPnl) < 0).reduce((sum, item) => sum + finite(item.netPnl), 0));
  const totalNetPnl = settled.reduce((sum, item) => sum + finite(item.netPnl), 0);
  const averageNetReturn = settled.length
    ? settled.reduce((sum, item) => sum + finite(item.netReturn), 0) / settled.length
    : null;
  return {
    sampleCount: settled.length,
    wins,
    losses: settled.length - wins,
    winRate: settled.length ? wins / settled.length : null,
    totalNetPnl,
    averageNetReturn,
    profitFactor: grossLoss > 0 ? grossProfit / grossLoss : grossProfit > 0 ? Infinity : null,
  };
}

export function analyzeShadowPerformanceByRegime(evaluations = []) {
  const buckets = new Map();
  for (const evaluation of evaluations) {
    assertShadowSafety(evaluation);
    const regime = String(evaluation.marketRegime ?? "UNKNOWN").toUpperCase();
    const bucket = buckets.get(regime) ?? [];
    bucket.push(evaluation);
    buckets.set(regime, bucket);
  }
  const regimes = [...buckets.entries()]
    .map(([marketRegime, rows]) => ({ marketRegime, ...summarizeEvaluations(rows) }))
    .sort((a, b) => b.sampleCount - a.sampleCount || a.marketRegime.localeCompare(b.marketRegime));
  return {
    status: regimes.length ? "REGIME_ANALYSIS_READY" : "INSUFFICIENT_DATA",
    overall: summarizeEvaluations(evaluations),
    regimes,
    safety: { ...SHADOW_SAFETY },
  };
}

export function buildShadowOperationsDashboard({ dailyLogs = [], evaluations = [] } = {}) {
  dailyLogs.forEach(assertShadowSafety);
  evaluations.forEach(assertShadowSafety);
  const regimePerformance = analyzeShadowPerformanceByRegime(evaluations);
  const latestLog = [...dailyLogs].sort((a, b) => String(b.date).localeCompare(String(a.date)))[0] ?? null;
  const totals = dailyLogs.reduce((acc, log) => {
    acc.predictions += finite(log.predictionCount);
    acc.evaluated += finite(log.evaluatedCount);
    acc.pending += finite(log.pendingCount);
    acc.noTrade += finite(log.noTradeCount);
    acc.netPnl += finite(log.totalNetPnl);
    return acc;
  }, { predictions: 0, evaluated: 0, pending: 0, noTrade: 0, netPnl: 0 });
  return {
    status: "SHADOW_DASHBOARD_READY",
    latestDate: latestLog?.date ?? null,
    totals,
    regimePerformance,
    recentDailyLogs: [...dailyLogs].sort((a, b) => String(b.date).localeCompare(String(a.date))).slice(0, 30),
    executionAllowed: false,
    safety: { ...SHADOW_SAFETY },
  };
}

function periodKey(date, period) {
  const value = String(date ?? "");
  if (period === "MONTHLY") return value.slice(0, 7);
  const d = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) return "UNKNOWN";
  const day = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  const week = Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
  return `${d.getUTCFullYear()}-W${String(week).padStart(2, "0")}`;
}

export function buildShadowPeriodicReports(dailyLogs = []) {
  dailyLogs.forEach(assertShadowSafety);
  const build = (period) => {
    const grouped = new Map();
    for (const log of dailyLogs) {
      const key = periodKey(log.date, period);
      const bucket = grouped.get(key) ?? [];
      bucket.push(log);
      grouped.set(key, bucket);
    }
    return [...grouped.entries()].map(([periodKeyValue, logs]) => {
      const predictionCount = logs.reduce((sum, log) => sum + finite(log.predictionCount), 0);
      const evaluatedCount = logs.reduce((sum, log) => sum + finite(log.evaluatedCount), 0);
      const wins = logs.reduce((sum, log) => sum + finite(log.wins), 0);
      const totalNetPnl = logs.reduce((sum, log) => sum + finite(log.totalNetPnl), 0);
      return {
        period: periodKeyValue,
        predictionCount,
        evaluatedCount,
        pendingCount: logs.reduce((sum, log) => sum + finite(log.pendingCount), 0),
        winRate: evaluatedCount ? wins / evaluatedCount : null,
        totalNetPnl,
        averageDailyNetPnl: logs.length ? totalNetPnl / logs.length : 0,
        dayCount: logs.length,
      };
    }).sort((a, b) => b.period.localeCompare(a.period));
  };
  return {
    weekly: build("WEEKLY"),
    monthly: build("MONTHLY"),
    safety: { ...SHADOW_SAFETY },
  };
}

export function evaluateShadowOperationalSafety(input = {}, limits = {}) {
  const maxPending = Math.max(0, finite(limits.maxPending, 100));
  const maxDailyLoss = Math.max(0, finite(limits.maxDailyLoss, 50000));
  const maxStaleMinutes = Math.max(1, finite(limits.maxStaleMinutes, 30));
  const blockers = [];
  const warnings = [];
  if (input.killSwitchActive === true) blockers.push("KILL_SWITCH_ACTIVE");
  if (input.dataQualityHealthy === false) blockers.push("DATA_QUALITY_UNHEALTHY");
  if (input.bridgeConnected === false) blockers.push("BRIDGE_DISCONNECTED");
  if (input.rssConnected === false) blockers.push("RSS_DISCONNECTED");
  if (finite(input.pendingCount) > maxPending) blockers.push("PENDING_LIMIT_EXCEEDED");
  if (finite(input.dailyNetPnl) < -maxDailyLoss) blockers.push("DAILY_LOSS_LIMIT_EXCEEDED");
  if (finite(input.dataAgeMinutes) > maxStaleMinutes) blockers.push("STALE_DATA");
  if (input.auditChecksumValid === false) blockers.push("AUDIT_CHECKSUM_MISMATCH");
  if (input.sampleCount != null && finite(input.sampleCount) < 30) warnings.push("LOW_SAMPLE_SIZE");
  return {
    status: blockers.length ? "HALTED" : warnings.length ? "WARNING" : "HEALTHY",
    blockers,
    warnings,
    shadowOperationsAllowed: blockers.length === 0,
    brokerWrites: 0,
    liveOrders: 0,
    excelOrderWrites: 0,
    orderTriggerChanges: 0,
    safety: { ...SHADOW_SAFETY },
  };
}

export function runShadowOperationsIntelligence({ dailyLogs = [], evaluations = [], operationalState = {}, limits = {} } = {}) {
  const safetyState = evaluateShadowOperationalSafety(operationalState, limits);
  const dashboard = buildShadowOperationsDashboard({ dailyLogs, evaluations });
  const reports = buildShadowPeriodicReports(dailyLogs);
  return {
    status: safetyState.status === "HALTED" ? "SHADOW_OPERATIONS_HALTED" : "SHADOW_OPERATIONS_READY",
    dashboard,
    reports,
    safetyState,
    executionAllowed: false,
    brokerWrites: 0,
    liveOrders: 0,
    excelOrderWrites: 0,
    orderTriggerChanges: 0,
    safety: { ...SHADOW_SAFETY },
  };
}
