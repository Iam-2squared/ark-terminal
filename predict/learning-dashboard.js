import {
  loadCloudOperationsStatus,
  loadOfflineQueue,
} from "./cloud/cloud-operations-store.js";

function parseJson(value, fallback) {
  try {
    const parsed = JSON.parse(String(value ?? ""));
    return parsed ?? fallback;
  }
  catch {
    return fallback;
  }
}

function readArray(key) {
  const value = parseJson(globalThis.localStorage?.getItem?.(key), []);
  return Array.isArray(value) ? value : [];
}

function readObject(key) {
  const value = parseJson(globalThis.localStorage?.getItem?.(key), null);
  return value && typeof value === "object" && !Array.isArray(value)
    ? value
    : null;
}

function text(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = String(value ?? "--");
}

function percent(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `${number.toFixed(1)}%` : "--";
}

function numberText(value, digits = 2) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(digits) : "--";
}

function dateText(value) {
  if (!value) return "--";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? String(value)
    : parsed.toLocaleString("ja-JP");
}

function latestBy(items, key = "updatedAt") {
  return [...items].sort((left, right) =>
    String(right?.[key] ?? right?.createdAt ?? "")
      .localeCompare(String(left?.[key] ?? left?.createdAt ?? "")),
  )[0] ?? null;
}

function loadLearningState() {
  const continuous = readObject("ark.continuous-learning.v1") ?? {
    production: null,
    candidates: [],
    history: [],
  };

  const candidates = [
    ...(Array.isArray(continuous.candidates) ? continuous.candidates : []),
    ...readArray("ark.learning.candidates.v1"),
  ];

  const forwardTests = readArray("ark.learning.forward-tests.v1");
  const modelVersions = readArray("ark.learning.model-versions.v1");
  const reports = readArray("ark.learning.reports.v1");
  const history = [
    ...(Array.isArray(continuous.history) ? continuous.history : []),
    ...modelVersions,
  ];

  return {
    production: continuous.production ?? latestBy(modelVersions),
    candidates,
    forwardTests,
    reports,
    history,
    cloud: loadCloudOperationsStatus(),
    queue: loadOfflineQueue(),
  };
}

function renderProduction(production) {
  const metrics = production?.metrics ?? {};
  text("learningProductionVersion", production?.version ?? "未設定");
  text("learningAccuracy", percent(metrics.accuracy));
  text("learningWinRate", percent(metrics.winRate));
  text("learningProfitFactor", numberText(metrics.profitFactor));
  text("learningSharpe", numberText(metrics.sharpe));
  text("learningMaxDrawdown", percent(metrics.maxDrawdown));
  text("learningAverageReturn", percent(metrics.averageReturn));
}

function renderHealth(state) {
  const checks = [
    ["Data Quality", state.reports.length > 0],
    ["Sample Size", state.candidates.some((item) => Number(item?.sourceTradeCount) >= 50)],
    ["Forward Test", state.forwardTests.length > 0],
    ["Human Review", state.candidates.some((item) => item?.humanApprovalRequired === true)],
    ["Cloud Sync", state.cloud.authenticated === true],
    ["Offline Queue", state.queue.length === 0],
  ];

  const grid = document.getElementById("learningHealthGrid");
  if (grid) {
    grid.innerHTML = checks
      .map(([label, ok]) => `
        <div class="learningHealthItem" data-ok="${ok}">
          <span>${label}</span>
          <strong>${ok ? "OK" : "WAIT"}</strong>
        </div>
      `)
      .join("");
  }

  const healthy = checks.every(([, ok]) => ok);
  text("learningHealthLabel", healthy ? "Healthy" : "Monitoring");

  const badge = document.getElementById("learningCloudBadge");
  if (badge) {
    const stateName = state.cloud.syncing
      ? "同期中"
      : state.cloud.authenticated
        ? "接続済み"
        : state.cloud.online === false
          ? "オフライン"
          : state.cloud.configured
            ? "未接続"
            : "未設定";
    badge.textContent = stateName;
    badge.dataset.state = state.cloud.authenticated ? "connected" : "disconnected";
  }
}

function renderSummary(state) {
  const reviewCount = state.candidates.filter((item) =>
    ["READY_FOR_REVIEW", "READY_FOR_HUMAN_REVIEW"].includes(item?.status),
  ).length;

  text("learningCandidateCount", state.candidates.length);
  text("learningReviewCount", reviewCount);
  text("learningForwardCount", state.forwardTests.length);
  text("learningReportCount", state.reports.length);
  text("learningQueueCount", state.queue.length);
  text("learningLastSync", dateText(state.cloud.lastSuccessAt ?? state.cloud.lastSyncAt));
}

function renderComparison(state) {
  const target = document.getElementById("learningCandidateComparison");
  if (!target) return;

  const candidate = latestBy(state.candidates, "createdAt");
  if (!candidate) {
    target.innerHTML = '<p class="emptyState">Candidateはまだありません。</p>';
    return;
  }

  const productionMetrics = state.production?.metrics ?? {};
  const candidateMetrics = candidate?.walkForward?.metrics ?? candidate?.metrics ?? {};
  const rows = [
    ["Accuracy", percent(productionMetrics.accuracy), percent(candidateMetrics.accuracy)],
    ["Win Rate", percent(productionMetrics.winRate), percent(candidateMetrics.winRate)],
    ["Profit Factor", numberText(productionMetrics.profitFactor), numberText(candidateMetrics.profitFactor)],
    ["Sharpe", numberText(productionMetrics.sharpe), numberText(candidateMetrics.sharpe)],
    ["Max DD", percent(productionMetrics.maxDrawdown), percent(candidateMetrics.maxDrawdown)],
  ];

  target.innerHTML = `
    <div class="learningComparisonHeader">
      <div><span>Production</span><strong>${state.production?.version ?? "未設定"}</strong></div>
      <div><span>Candidate</span><strong>${candidate.version ?? candidate.candidateVersion ?? candidate.id}</strong></div>
    </div>
    <div class="learningComparisonRows">
      ${rows.map(([label, production, challenger]) => `
        <div class="learningComparisonRow">
          <span>${label}</span>
          <strong>${production}</strong>
          <strong>${challenger}</strong>
        </div>
      `).join("")}
    </div>
    <p class="dataSourceDescription">状態：${candidate.status ?? "UNKNOWN"}／自動昇格：無効</p>
  `;
}

function renderTimeline(state) {
  const target = document.getElementById("learningTimeline");
  if (!target) return;

  const entries = [
    ...state.history,
    ...state.reports.map((item) => ({
      type: "LEARNING_REPORT",
      at: item.updatedAt ?? item.createdAt,
      note: item.summary ?? item.status ?? "学習レポート",
    })),
    ...state.forwardTests.map((item) => ({
      type: "FORWARD_TEST",
      at: item.generatedAt ?? item.updatedAt,
      note: item.status ?? "Forward Test",
    })),
  ]
    .sort((left, right) =>
      String(right?.at ?? right?.updatedAt ?? "")
        .localeCompare(String(left?.at ?? left?.updatedAt ?? "")),
    )
    .slice(0, 30);

  if (!entries.length) {
    target.innerHTML = '<p class="emptyState">学習履歴はまだありません。</p>';
    return;
  }

  target.innerHTML = entries.map((item) => `
    <article class="learningTimelineItem">
      <time>${dateText(item.at ?? item.updatedAt ?? item.createdAt)}</time>
      <strong>${item.type ?? item.action ?? item.status ?? "LEARNING_EVENT"}</strong>
      <p>${item.note ?? item.reason ?? item.candidateId ?? item.version ?? "監査履歴"}</p>
    </article>
  `).join("");
}

export function renderLearningDashboard() {
  const state = loadLearningState();
  renderProduction(state.production);
  renderHealth(state);
  renderSummary(state);
  renderComparison(state);
  renderTimeline(state);
  return state;
}

renderLearningDashboard();

export const LearningDashboardInternals = Object.freeze({
  dateText,
  latestBy,
  loadLearningState,
  numberText,
  parseJson,
  percent,
});
