export const MODEL_PERFORMANCE_UI_V1_VERSION = "model-performance-ui-v1";

const BASELINE_STORAGE_KEY = "ark.phase11.modelPerformanceBaseline.v1";
const REPORT_STORAGE_KEY = "ark.phase11.modelPerformanceReport.v1";

function finite(value) {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function readJson(storage, key) {
  try {
    const value = JSON.parse(storage?.getItem?.(key) ?? "null");
    return value && typeof value === "object" ? value : null;
  } catch {
    return null;
  }
}

function metric(source, ...keys) {
  for (const key of keys) {
    const value = finite(source?.[key]);
    if (value !== null) return value;
  }
  return null;
}

function normalizeMetrics(source = {}) {
  return {
    accuracy: metric(source, "accuracy", "predictionAccuracy", "winRate"),
    profitFactor: metric(source, "profitFactor", "pf"),
    sharpe: metric(source, "sharpe", "sharpeRatio"),
    maxDrawdown: metric(source, "maxDrawdown", "maximumDrawdown"),
    averageReturn: metric(source, "averageReturn", "averageReturnPercent"),
    sampleSize: metric(source, "sampleSize", "count", "trades"),
  };
}

export function createModelPerformanceViewModel({
  baseline = null,
  validation = null,
  selection = null,
} = {}) {
  const productionSource = baseline?.overall ?? validation?.productionMetrics ?? {};
  const candidateSource = validation?.candidateMetrics ?? selection?.selectedCandidate?.metrics ?? {};
  const selected = selection?.selectedCandidate ?? null;
  const safety = {
    humanApprovalRequired: selection?.safety?.humanApprovalRequired !== false,
    productionUpdateAllowed: selection?.safety?.productionUpdateAllowed === true,
    brokerExecutionAllowed: selection?.safety?.brokerExecutionAllowed === true,
  };

  return {
    version: MODEL_PERFORMANCE_UI_V1_VERSION,
    hasData: Boolean(baseline || validation || selection),
    productionVersion:
      baseline?.productionModelVersion ??
      baseline?.modelVersion ??
      validation?.productionVersion ??
      selection?.productionVersion ??
      null,
    candidateVersion:
      validation?.candidateVersion ??
      selected?.version ??
      null,
    productionMetrics: normalizeMetrics(productionSource),
    candidateMetrics: normalizeMetrics(candidateSource),
    validationStatus: validation?.status ?? "NOT_VALIDATED",
    selectionStatus: selection?.status ?? "NO_SELECTION_REPORT",
    selectedCandidate: selected,
    futureLeakChecked: validation?.futureLeakChecked === true,
    outOfSample: validation?.outOfSample === true,
    warnings: [
      ...(Array.isArray(validation?.warnings) ? validation.warnings : []),
      ...(!baseline ? ["PRODUCTION_BASELINE_NOT_AVAILABLE"] : []),
      ...(!validation ? ["CANDIDATE_VALIDATION_NOT_AVAILABLE"] : []),
    ],
    safety,
  };
}

function format(value, { suffix = "", digits = 2 } = {}) {
  const number = finite(value);
  return number === null ? "--" : `${number.toFixed(digits)}${suffix}`;
}

function text(documentRef, tag, value, className = "") {
  const node = documentRef.createElement(tag);
  node.textContent = value;
  if (className) node.className = className;
  return node;
}

function metricCard(documentRef, label, production, candidate, options = {}) {
  const card = text(documentRef, "div", "", "modelPerformanceMetric");
  card.append(text(documentRef, "span", label));
  const values = text(documentRef, "div", "", "modelPerformanceMetricValues");
  values.append(text(documentRef, "strong", format(production, options)));
  values.append(text(documentRef, "strong", format(candidate, options)));
  card.append(values);
  return card;
}

function injectStyles(documentRef) {
  if (documentRef.getElementById("modelPerformanceUiV1Styles")) return;
  if (typeof documentRef.createElement !== "function") return;
  const style = documentRef.createElement("style");
  style.id = "modelPerformanceUiV1Styles";
  style.textContent = `
    .modelPerformanceCard{display:grid;gap:20px;padding:24px;border:1px solid var(--border);border-radius:20px;background:var(--panel)}
    .modelPerformanceHeader,.modelPerformanceSafety{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;flex-wrap:wrap}
    .modelPerformanceBadge{padding:7px 11px;border:1px solid var(--border);border-radius:999px;color:var(--muted);font-size:.82rem}
    .modelPerformanceBadge.ready{color:var(--green);border-color:color-mix(in srgb,var(--green) 35%,transparent)}
    .modelPerformanceVersions,.modelPerformanceGrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
    .modelPerformanceVersion,.modelPerformanceMetric{padding:14px;border:1px solid var(--border);border-radius:14px;background:var(--panel-light)}
    .modelPerformanceVersion span,.modelPerformanceMetric>span{display:block;color:var(--muted);font-size:.82rem;margin-bottom:6px}
    .modelPerformanceMetricValues{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
    .modelPerformanceMetricValues strong:first-child{color:var(--muted)}
    .modelPerformanceColumns{display:grid;grid-template-columns:1fr 1fr;gap:8px;color:var(--muted);font-size:.78rem;text-align:center}
    .modelPerformanceChecks{display:flex;gap:8px;flex-wrap:wrap}
    .modelPerformanceCheck{padding:7px 10px;border-radius:999px;background:var(--panel-light);font-size:.8rem}
    .modelPerformanceCheck.pass{color:var(--green)}.modelPerformanceCheck.fail{color:var(--orange)}
    .modelPerformanceWarnings{margin:0;padding-left:20px;color:var(--orange);font-size:.85rem}
    .modelPerformanceSafety{padding:14px;border:1px solid var(--border);border-radius:14px;background:rgba(255,159,10,.06)}
    .modelPerformanceSafety strong{color:var(--orange)}
    @media(max-width:720px){.modelPerformanceVersions,.modelPerformanceGrid{grid-template-columns:1fr}.modelPerformanceMetricValues{grid-template-columns:1fr 1fr}}
  `;
  documentRef.head?.append?.(style);
}

export function mountModelPerformanceUiV1({
  windowRef = globalThis.window,
  documentRef = globalThis.document,
  source = null,
} = {}) {
  const domAvailable =
    Boolean(windowRef && documentRef) &&
    typeof documentRef.createElement === "function" &&
    typeof documentRef.getElementById === "function" &&
    typeof documentRef.querySelector === "function";

  if (!domAvailable) return { mounted: false, reason: "dom_unavailable" };
  injectStyles(documentRef);

  const savedBaseline = readJson(windowRef.localStorage, BASELINE_STORAGE_KEY);
  const savedReport = readJson(windowRef.localStorage, REPORT_STORAGE_KEY);
  const resolved = source ?? windowRef.__ARK_MODEL_PERFORMANCE__ ?? savedReport ?? {};
  const view = createModelPerformanceViewModel({
    baseline: resolved.baseline ?? savedBaseline,
    validation: resolved.validation ?? null,
    selection: resolved.selection ?? null,
  });

  let root = documentRef.getElementById("modelPerformanceCard");
  if (!root) {
    root = text(documentRef, "article", "", "modelPerformanceCard fullWidthCard");
    root.id = "modelPerformanceCard";
    const anchor = documentRef.getElementById("globalEvaluationCard");
    anchor?.parentNode?.insertBefore?.(root, anchor);
    if (!root.parentNode) documentRef.querySelector(".dashboardGrid")?.append?.(root);
  }
  root.replaceChildren();

  const header = text(documentRef, "div", "", "modelPerformanceHeader");
  const heading = text(documentRef, "div", "");
  heading.append(text(documentRef, "p", "MODEL GOVERNANCE", "cardLabel"));
  heading.append(text(documentRef, "h2", "Production / Candidate 比較"));
  const badge = text(
    documentRef,
    "span",
    view.selectedCandidate ? "人間レビュー待ち" : view.hasData ? "検証中" : "検証データなし",
    `modelPerformanceBadge${view.selectedCandidate ? " ready" : ""}`,
  );
  header.append(heading, badge);
  root.append(header);
  root.append(text(documentRef, "p", "本番モデルと候補モデルの検証成績を比較します。表示は実測レポートのみで、自動昇格や実注文は行いません。", "dataSourceDescription"));

  const versions = text(documentRef, "div", "", "modelPerformanceVersions");
  for (const [label, value] of [
    ["Production", view.productionVersion ?? "未登録"],
    ["Candidate", view.candidateVersion ?? "未選定"],
  ]) {
    const item = text(documentRef, "div", "", "modelPerformanceVersion");
    item.append(text(documentRef, "span", label));
    item.append(text(documentRef, "strong", String(value)));
    versions.append(item);
  }
  root.append(versions);

  const columns = text(documentRef, "div", "", "modelPerformanceColumns");
  columns.append(text(documentRef, "span", "Production"), text(documentRef, "span", "Candidate"));
  root.append(columns);

  const grid = text(documentRef, "div", "", "modelPerformanceGrid");
  const metrics = [
    ["Accuracy", "accuracy", { suffix: "%" }],
    ["Profit Factor", "profitFactor", {}],
    ["Sharpe", "sharpe", {}],
    ["Max Drawdown", "maxDrawdown", { suffix: "%" }],
    ["Average Return", "averageReturn", { suffix: "%" }],
    ["Sample Size", "sampleSize", { digits: 0 }],
  ];
  for (const [label, key, options] of metrics) {
    grid.append(metricCard(documentRef, label, view.productionMetrics[key], view.candidateMetrics[key], options));
  }
  root.append(grid);

  const checks = text(documentRef, "div", "", "modelPerformanceChecks");
  for (const [label, passed] of [
    ["Out-of-Sample", view.outOfSample],
    ["Future Leak Check", view.futureLeakChecked],
    ["Human Approval", view.safety.humanApprovalRequired],
  ]) {
    checks.append(text(documentRef, "span", `${passed ? "✓" : "!"} ${label}`, `modelPerformanceCheck ${passed ? "pass" : "fail"}`));
  }
  root.append(checks);

  if (view.warnings.length) {
    const warnings = text(documentRef, "ul", "", "modelPerformanceWarnings");
    for (const warning of [...new Set(view.warnings)]) warnings.append(text(documentRef, "li", warning));
    root.append(warnings);
  }

  const safety = text(documentRef, "div", "", "modelPerformanceSafety");
  safety.append(text(documentRef, "strong", "安全状態"));
  safety.append(text(documentRef, "span", "本番更新：無効 / ブローカー実行：無効 / 最終判断：人間"));
  root.append(safety);

  return { mounted: true, view };
}

export function startModelPerformanceUiV1(options = {}) {
  const { windowRef = globalThis.window } = options;
  const render = (event) => mountModelPerformanceUiV1({ ...options, source: event?.detail ?? options.source ?? null });
  render();
  windowRef?.addEventListener?.("ark:model-performance-updated", render);
  return {
    render,
    stop() {
      windowRef?.removeEventListener?.("ark:model-performance-updated", render);
    },
  };
}

export default mountModelPerformanceUiV1;
