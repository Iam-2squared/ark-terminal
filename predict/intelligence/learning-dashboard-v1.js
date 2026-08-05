export const LEARNING_DASHBOARD_V1 = "learning-dashboard-v1";

function clone(value) {
  return value === undefined ? undefined : structuredClone(value);
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

export function buildLearningDashboardV1({
  productionModel = null,
  candidates = [],
  walkForwardReports = [],
  driftReports = [],
  learningLog = [],
} = {}) {
  const normalizedCandidates = asArray(candidates).map((candidate) => ({
    id: candidate?.id ?? candidate?.version ?? null,
    version: candidate?.version ?? candidate?.modelVersion ?? null,
    status: candidate?.status ?? "UNKNOWN",
    metrics: clone(candidate?.metrics ?? candidate?.walkForward?.metrics ?? null),
    humanApprovalRequired: true,
    productionUpdateAllowed: false,
  }));

  const normalizedWalkForward = asArray(walkForwardReports).map((report) => ({
    candidateVersion: report?.candidateVersion ?? report?.version ?? null,
    status: report?.status ?? "UNKNOWN",
    outOfSample: report?.outOfSample === true,
    futureLeakChecked: report?.futureLeakChecked === true,
    metrics: clone(report?.candidateMetrics ?? report?.metrics ?? null),
  }));

  const normalizedDrift = asArray(driftReports).map((report) => ({
    detected: report?.detected === true || report?.driftDetected === true,
    severity: report?.severity ?? "UNKNOWN",
    detectedAt: report?.detectedAt ?? report?.generatedAt ?? null,
    source: clone(report),
  }));

  const normalizedLog = asArray(learningLog)
    .map((entry) => ({
      type: entry?.type ?? entry?.event ?? "UNKNOWN",
      timestamp: entry?.timestamp ?? entry?.createdAt ?? null,
      candidateId: entry?.candidateId ?? entry?.data?.candidateId ?? null,
      detail: clone(entry?.data ?? entry?.detail ?? null),
    }))
    .sort((a, b) => String(b.timestamp ?? "").localeCompare(String(a.timestamp ?? "")));

  return {
    version: LEARNING_DASHBOARD_V1,
    generatedAt: new Date().toISOString(),
    production: clone(productionModel),
    candidates: normalizedCandidates,
    walkForward: normalizedWalkForward,
    drift: normalizedDrift,
    log: normalizedLog,
    summary: {
      candidateCount: normalizedCandidates.length,
      awaitingApproval: normalizedCandidates.filter((candidate) => ["AWAITING_APPROVAL", "READY_FOR_REVIEW"].includes(candidate.status)).length,
      passedWalkForward: normalizedWalkForward.filter((report) => report.outOfSample && report.futureLeakChecked).length,
      driftAlertCount: normalizedDrift.filter((report) => report.detected).length,
    },
    safety: {
      automaticPromotionAllowed: false,
      humanApprovalRequired: true,
      brokerExecutionAllowed: false,
    },
  };
}

export default buildLearningDashboardV1;
