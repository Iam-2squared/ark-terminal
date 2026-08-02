function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function metricHtml(metric) {
  return `
    <div class="aiAccuracyMetric">
      <span>${escapeHtml(metric.label)}</span>
      <strong>${escapeHtml(metric.value)}</strong>
      <small>${escapeHtml(metric.detail)}</small>
    </div>
  `;
}

function horizonHtml(item) {
  return `
    <div class="aiAccuracyHorizon${item.available ? "" : " unavailable"}">
      <span>${escapeHtml(item.label)}</span>
      <strong>${escapeHtml(item.accuracy)}</strong>
      <small>${escapeHtml(item.sampleLabel)}</small>
      <small>${escapeHtml(item.intervalLabel)}</small>
    </div>
  `;
}

function evidenceHtml(item) {
  return `
    <div class="aiAccuracyEvidence${item.available ? "" : " unavailable"}">
      <span>${escapeHtml(item.label)}</span>
      <strong>${escapeHtml(item.accuracy)}</strong>
      <small>${escapeHtml(item.sampleLabel)}</small>
      <small>カバレッジ ${escapeHtml(item.coverage)}</small>
    </div>
  `;
}

export function renderAIAccuracyMonitor(viewModel, root) {
  if (!root) {
    return {
      rendered: false,
      reason: "container_unavailable",
    };
  }

  root.innerHTML = `
    <div class="aiAccuracyHeader">
      <div>
        <p class="cardLabel">${escapeHtml(viewModel.title)}</p>
        <h2 id="aiAccuracyMonitorTitle">${escapeHtml(viewModel.heading)}</h2>
      </div>
      <div class="aiAccuracyBadges">
        <span class="aiAccuracyBadge ${escapeHtml(viewModel.source.badgeClass)}">
          ${escapeHtml(viewModel.source.badge)}
        </span>
        <span class="aiAccuracyStatus ${escapeHtml(viewModel.status.className)}">
          ${escapeHtml(viewModel.status.label)}
        </span>
      </div>
    </div>

    <div class="aiAccuracyOverview">
      <section class="aiAccuracyHero">
        <span>${escapeHtml(viewModel.source.label)}</span>
        <strong data-ai-accuracy-value>${escapeHtml(viewModel.accuracy)}</strong>
        <p>${escapeHtml(viewModel.sampleLabel)}</p>
        <small>${escapeHtml(viewModel.intervalLabel)}</small>
        <small>${escapeHtml(viewModel.reliabilityLabel)}</small>
      </section>

      <section class="aiAccuracyMetricGrid">
        ${viewModel.metrics.map(metricHtml).join("")}
      </section>
    </div>

    <p class="aiAccuracyMessage">${escapeHtml(viewModel.message)}</p>

    <section class="aiAccuracySection" aria-labelledby="aiAccuracyHorizonTitle">
      <div class="aiAccuracySectionHeader">
        <h3 id="aiAccuracyHorizonTitle">予測期間別の精度</h3>
        <span>1・3・5・10・20営業日</span>
      </div>
      <div class="aiAccuracyHorizonGrid">
        ${viewModel.horizons.map(horizonHtml).join("")}
      </div>
    </section>

    <section class="aiAccuracySection" aria-labelledby="aiAccuracyEvidenceTitle">
      <div class="aiAccuracySectionHeader">
        <h3 id="aiAccuracyEvidenceTitle">評価データの内訳</h3>
        <span>${escapeHtml(viewModel.source.description)}</span>
      </div>
      <div class="aiAccuracyEvidenceGrid">
        ${viewModel.evidence.map(evidenceHtml).join("")}
      </div>
    </section>

    <p class="aiAccuracyNotice">${escapeHtml(viewModel.notice)}</p>
  `;

  root.dataset.aiAccuracyState = viewModel.status.className;
  root.dataset.aiAccuracySource = viewModel.source.badgeClass;

  return {
    rendered: true,
    root,
  };
}

export function mountAIAccuracyMonitor({ documentRef = globalThis.document } = {}) {
  if (!documentRef) {
    return {
      mounted: false,
      reason: "environment_unavailable",
      root: null,
    };
  }

  const existing = documentRef.getElementById?.("aiAccuracyMonitor");

  if (existing) {
    return {
      mounted: true,
      reused: true,
      root: existing,
    };
  }

  const dashboard = documentRef.querySelector?.(".dashboardGrid");

  if (!dashboard) {
    return {
      mounted: false,
      reason: "dashboard_unavailable",
      root: null,
    };
  }

  const root = documentRef.createElement("article");

  root.id = "aiAccuracyMonitor";
  root.className = "aiAccuracyMonitor fullWidthCard";
  root.setAttribute?.("aria-labelledby", "aiAccuracyMonitorTitle");

  const insertionPoint = dashboard.children?.[2] ?? null;

  if (insertionPoint && typeof dashboard.insertBefore === "function") {
    dashboard.insertBefore(root, insertionPoint);
  } else {
    dashboard.appendChild(root);
  }

  return {
    mounted: true,
    reused: false,
    root,
  };
}

export const AIAccuracyMonitorUIInternals = Object.freeze({
  escapeHtml,
  metricHtml,
  horizonHtml,
  evidenceHtml,
});
