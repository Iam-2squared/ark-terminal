const REQUIRED_MODULES = Object.freeze([
  "./analysis-core.js",
  "./runtime-orchestrator.js",
  "./integrated-ai-decision.js",
  "./recommendation-engine.js",
  "./explainability-engine.js",
  "./ui-integration.js",
  "./dashboard-renderer.js",
]);

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function clamp(value, minimum = 0, maximum = 100) {
  return Math.min(
    maximum,
    Math.max(
      minimum,
      Number(value) || 0,
    ),
  );
}

function gradeFromScore(score) {
  if (score >= 90) {
    return "A";
  }

  if (score >= 75) {
    return "B";
  }

  if (score >= 60) {
    return "C";
  }

  if (score >= 40) {
    return "D";
  }

  return "E";
}

export function inspectRuntimePayload(
  runtime = {},
) {
  const issues = [];
  const warnings = [];

  if (!runtime || typeof runtime !== "object") {
    issues.push(
      "Runtime result is missing.",
    );

    return {
      healthy: false,
      score: 0,
      grade: "E",
      issues,
      warnings,
    };
  }

  if (runtime.status !== "ready") {
    issues.push(
      "Runtime status is not ready.",
    );
  }

  if (!runtime.analysis) {
    issues.push(
      "Analysis result is missing.",
    );
  }

  if (
    !runtime.html ||
    typeof runtime.html !== "string"
  ) {
    issues.push(
      "Rendered HTML is missing.",
    );
  }

  const dashboard =
    runtime.analysis?.dashboard ?? {};

  if (!dashboard.action) {
    issues.push(
      "Dashboard action is missing.",
    );
  }

  if (!finite(dashboard.score)) {
    issues.push(
      "Dashboard score is invalid.",
    );
  }

  if (!finite(dashboard.confidence)) {
    issues.push(
      "Dashboard confidence is invalid.",
    );
  }

  const decision =
    runtime.analysis?.decision ?? {};

  if (
    !Array.isArray(
      decision.buyFactors,
    )
  ) {
    warnings.push(
      "Buy factors are unavailable.",
    );
  }

  if (
    !Array.isArray(
      decision.riskFactors,
    )
  ) {
    warnings.push(
      "Risk factors are unavailable.",
    );
  }

  if (
    finite(dashboard.confidence) &&
    Number(dashboard.confidence) < 50
  ) {
    warnings.push(
      "Analysis confidence is below 50.",
    );
  }

  if (
    finite(dashboard.score) &&
    (
      Number(dashboard.score) < 0 ||
      Number(dashboard.score) > 100
    )
  ) {
    issues.push(
      "Dashboard score is outside 0-100.",
    );
  }

  const deduction =
    issues.length * 25 +
    warnings.length * 8;

  const score =
    clamp(
      100 - deduction,
    );

  return {
    healthy:
      issues.length === 0,

    score,

    grade:
      gradeFromScore(score),

    issues,

    warnings,

    dashboard: {
      action:
        dashboard.action ??
        "UNKNOWN",

      score:
        finite(dashboard.score)
          ? Number(dashboard.score)
          : null,

      confidence:
        finite(dashboard.confidence)
          ? Number(dashboard.confidence)
          : null,

      macro:
        dashboard.macro ??
        "UNKNOWN",

      regime:
        dashboard.regime ??
        "UNKNOWN",
    },
  };
}

export async function verifyRuntimeModules({
  importer = (path) => import(path),
  modules = REQUIRED_MODULES,
} = {}) {
  const results = [];

  for (const modulePath of modules) {
    try {
      const loaded =
        await importer(modulePath);

      results.push({
        modulePath,
        loaded: true,
        exportCount:
          Object.keys(
            loaded ?? {},
          ).length,
        error: null,
      });
    }
    catch (error) {
      results.push({
        modulePath,
        loaded: false,
        exportCount: 0,
        error:
          error?.message ??
          String(error),
      });
    }
  }

  const failed =
    results.filter(
      (result) =>
        result.loaded !== true,
    );

  return {
    healthy:
      failed.length === 0,

    checkedCount:
      results.length,

    loadedCount:
      results.length -
      failed.length,

    failedCount:
      failed.length,

    results,
  };
}

export function buildRuntimeDiagnosticReport({
  runtime = {},
  modules = {},
} = {}) {
  const payload =
    inspectRuntimePayload(
      runtime,
    );

  const moduleHealth =
    modules?.healthy === true;

  const score =
    clamp(
      payload.score -
      (
        moduleHealth
          ? 0
          : 20
      ),
    );

  return {
    version:
      "ark-runtime-diagnostics-v1",

    generatedAt:
      new Date().toISOString(),

    healthy:
      payload.healthy &&
      moduleHealth,

    score,

    grade:
      gradeFromScore(score),

    payload,

    modules,

    summary:
      payload.healthy &&
      moduleHealth
        ? "AI runtime is healthy."
        : "AI runtime requires attention.",
  };
}

export function renderRuntimeDiagnosticBadge(
  report = {},
) {
  const status =
    report.healthy
      ? "HEALTHY"
      : "ATTENTION";

  return `
    <aside
      class="arkRuntimeDiagnosticBadge ${report.healthy ? "healthy" : "attention"}"
      data-ark-runtime-health="${status}"
    >
      <span>AI Runtime</span>
      <strong>${status}</strong>
      <small>
        Score ${Number(report.score ?? 0)}
        · Grade ${String(report.grade ?? "E")}
      </small>
    </aside>
  `;
}

export const RuntimeDiagnosticsInternals = {
  REQUIRED_MODULES,
  clamp,
  finite,
  gradeFromScore,
};