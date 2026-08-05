export const VALIDATION_RELEASE_V1 = "validation-release-v1";

function ready(value) {
  return String(value?.status ?? value).toUpperCase() === "READY";
}

export function buildValidationReleaseV1({
  historical = {},
  backtest = {},
  benchmark = {},
  weakness = {},
  optimization = {},
  version = "v1.1.0-rc1",
  commit = null,
} = {}) {
  const checks = [
    { id: "historical", passed: ready(historical) && !historical?.metadata?.futureLeakDetected },
    { id: "backtest", passed: ready(backtest) && !backtest?.futureLeakDetected },
    { id: "benchmark", passed: ready(benchmark) },
    { id: "weakness", passed: ready(weakness) },
    { id: "optimization", passed: ready(optimization) },
    { id: "approval-gate", passed: optimization?.automaticPromotionAllowed === false && optimization?.humanApprovalRequired === true },
  ];
  const blockers = checks.filter((check) => !check.passed).map((check) => check.id);

  return {
    version: VALIDATION_RELEASE_V1,
    releaseVersion: version,
    generatedAt: new Date().toISOString(),
    commit,
    status: blockers.length ? "BLOCKED" : "READY_FOR_REVIEW",
    checks,
    blockers,
    report: {
      historicalRows: historical?.metadata?.rowCount ?? 0,
      symbols: historical?.metadata?.symbolCount ?? 0,
      trades: backtest?.overall?.sampleSize ?? 0,
      accuracy: benchmark?.classification?.accuracy ?? 0,
      weakSegments: weakness?.weakSegments?.length ?? 0,
      candidate: optimization?.bestCandidate?.id ?? null,
    },
    productionUpdateAllowed: false,
    automaticPromotionAllowed: false,
    humanApprovalRequired: true,
  };
}

export default buildValidationReleaseV1;
