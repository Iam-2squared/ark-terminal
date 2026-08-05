export const UNIFIED_DASHBOARD_V1_VERSION = "unified-dashboard-v1";

function normalizeStatus(value) {
  const status = String(value ?? "UNKNOWN").toUpperCase();
  if (["READY", "HEALTHY", "OK", "SUCCESS", "RUNNING", "SAFE"].includes(status)) return "HEALTHY";
  if (["BLOCKED", "FAILED", "ERROR", "UNSAFE"].includes(status)) return "BLOCKED";
  return "DEGRADED";
}

export function buildUnifiedDashboardV1({ modules = {}, quickActions = [], notices = [] } = {}) {
  const orderedKeys = [
    "prediction",
    "discovery",
    "aiAnalysis",
    "marketIntelligence",
    "portfolio",
    "paperTrading",
    "accuracy",
    "learning",
    "controlCenter",
  ];

  const cards = orderedKeys.map((key) => {
    const source = modules[key] ?? {};
    return {
      id: key,
      title: source.title ?? key,
      status: normalizeStatus(source.status ?? source.health),
      href: source.href ?? null,
      summary: source.summary ?? null,
      metrics: source.metrics ?? {},
      updatedAt: source.updatedAt ?? null,
    };
  });

  const blocked = cards.filter((card) => card.status === "BLOCKED").map((card) => card.id);
  const degraded = cards.filter((card) => card.status === "DEGRADED").map((card) => card.id);

  return {
    version: UNIFIED_DASHBOARD_V1_VERSION,
    generatedAt: new Date().toISOString(),
    overallStatus: blocked.length ? "BLOCKED" : degraded.length ? "DEGRADED" : "HEALTHY",
    cards,
    blocked,
    degraded,
    quickActions: Array.isArray(quickActions) ? quickActions : [],
    notices: Array.isArray(notices) ? notices : [],
    mobileReady: true,
    safety: {
      liveExecutionAllowed: false,
      brokerConnected: false,
    },
  };
}

export default buildUnifiedDashboardV1;
