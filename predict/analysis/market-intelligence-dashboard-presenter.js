function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function finiteOrNull(value) {
  if (value === null || value === undefined || value === "") return null;

  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function formatNumber(value, digits = 1) {
  const number = finiteOrNull(value);

  return number === null
    ? "--"
    : number.toLocaleString("ja-JP", {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      });
}

function formatPercent(value) {
  const number = finiteOrNull(value);
  return number === null ? "--" : `${formatNumber(number)}%`;
}

function formatTimestamp(value) {
  if (!value) return "更新時刻なし";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "更新時刻なし";

  return new Intl.DateTimeFormat("ja-JP", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function normalizedProgress(value) {
  const number = finiteOrNull(value);
  return number === null ? 0 : Math.min(100, Math.max(0, number));
}

function metricHtml(metric) {
  const availabilityClass = metric.available ? "" : " unavailable";
  const progressValue = metric.available
    ? `value="${normalizedProgress(metric.score)}"`
    : "";

  return `
    <div class="marketIntelligenceMetric${availabilityClass}">
      <div class="marketIntelligenceMetricHeading">
        <span>${escapeHtml(metric.label)}</span>
        <strong>${escapeHtml(formatNumber(metric.score))}</strong>
      </div>
      <progress
        max="100"
        ${progressValue}
        aria-label="${escapeHtml(metric.label)} score"
      ></progress>
      <small>
        品質 ${escapeHtml(formatPercent(metric.confidence))} /
        対象 ${escapeHtml(formatPercent(metric.coverage))}
      </small>
    </div>
  `;
}

function directionClass(direction) {
  if (direction === "上昇") return "positive";
  if (direction === "下落") return "negative";
  return "neutral";
}

function predictionHtml(prediction) {
  const classes = [
    "marketIntelligencePrediction",
    prediction.available ? "" : "unavailable",
    prediction.selected ? "selected" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return `
    <div class="${classes}">
      <div>
        <span>${escapeHtml(prediction.label)}</span>
        ${prediction.selected ? '<small class="selectedLabel">選択中</small>' : ""}
      </div>
      <strong class="${directionClass(prediction.direction)}">
        ${escapeHtml(prediction.direction)}
      </strong>
      <small>Score ${escapeHtml(formatNumber(prediction.score))}</small>
      <small>信頼度 ${escapeHtml(formatPercent(prediction.confidence))}</small>
    </div>
  `;
}

function providerHtml(provider) {
  const coverage = provider.coverage === null
    ? ""
    : ` / 対象 ${formatPercent(provider.coverage)}`;

  return `
    <div class="marketIntelligenceProvider">
      <div>
        <span>${escapeHtml(provider.label)}</span>
        <small>${escapeHtml(provider.source)}</small>
      </div>
      <div class="marketIntelligenceProviderState">
        <strong class="${escapeHtml(provider.statusClass)}">
          ${escapeHtml(provider.statusLabel)}
        </strong>
        <small>
          ${escapeHtml(provider.detail)}${escapeHtml(coverage)}
        </small>
      </div>
    </div>
  `;
}

function sectorItemHtml(item) {
  const change = item.averageChangePercent === null
    ? "変化率 --"
    : `平均 ${formatNumber(item.averageChangePercent, 2)}%`;

  return `
    <li>
      <span>${escapeHtml(item.name)}</span>
      <strong>${escapeHtml(formatNumber(item.score))}</strong>
      <small>${escapeHtml(change)}</small>
    </li>
  `;
}

function sectorListHtml(items, emptyMessage) {
  if (!Array.isArray(items) || !items.length) {
    return `<li class="unavailable"><span>${escapeHtml(emptyMessage)}</span></li>`;
  }

  return items.map(sectorItemHtml).join("");
}

function errorHtml(message) {
  if (!message) return "";

  return `
    <p class="marketIntelligenceError" role="status">
      ${escapeHtml(message)}
    </p>
  `;
}

export function renderMarketIntelligenceDashboard(viewModel, root) {
  if (!root) {
    return { rendered: false, reason: "container_unavailable" };
  }

  root.innerHTML = `
    <div class="marketIntelligenceHeader">
      <div>
        <p class="cardLabel">${escapeHtml(viewModel.title)}</p>
        <h2 id="marketIntelligenceDashboardTitle">
          ${escapeHtml(viewModel.heading)}
        </h2>
      </div>
      <div class="marketIntelligenceBadges">
        <span class="marketIntelligenceSymbol">
          ${escapeHtml(viewModel.symbol)}
        </span>
        <span class="marketIntelligenceStatus ${escapeHtml(viewModel.status.className)}">
          ${escapeHtml(viewModel.status.label)}
        </span>
      </div>
    </div>

    <p class="marketIntelligenceMessage">${escapeHtml(viewModel.message)}</p>
    ${errorHtml(viewModel.errorMessage)}

    <div class="marketIntelligenceOverview">
      <section class="marketIntelligenceHero" aria-label="Composite AI score">
        <span>CompositeAI</span>
        <strong>${escapeHtml(formatNumber(viewModel.compositeScore))}</strong>
        <div>
          <small>特徴量品質 ${escapeHtml(formatPercent(viewModel.featureConfidence))}</small>
          <small>カバレッジ ${escapeHtml(formatPercent(viewModel.featureCoverage))}</small>
        </div>
        <small>${escapeHtml(formatTimestamp(viewModel.calculatedAt))}</small>
      </section>

      <section class="marketIntelligenceMetricGrid" aria-label="主要市場特徴量">
        ${viewModel.metrics.map(metricHtml).join("")}
      </section>
    </div>

    <section class="marketIntelligenceSection" aria-labelledby="marketPredictionHorizonTitle">
      <div class="marketIntelligenceSectionHeader">
        <h3 id="marketPredictionHorizonTitle">予測期間別の市場方向</h3>
        <span>1・3・5・10・20営業日</span>
      </div>
      <div class="marketIntelligencePredictionGrid">
        ${viewModel.predictions.map(predictionHtml).join("")}
      </div>
    </section>

    <div class="marketIntelligenceDetailGrid">
      <section class="marketIntelligenceSection" aria-labelledby="marketBreadthTitle">
        <div class="marketIntelligenceSectionHeader">
          <h3 id="marketBreadthTitle">Market Breadth</h3>
          <span>${escapeHtml(formatPercent(viewModel.breadth.coverage))}</span>
        </div>
      <div class="marketIntelligenceBreadthGrid">
          <div><span>上昇</span><strong>${escapeHtml(formatNumber(viewModel.breadth.advancers, 0))}</strong></div>
          <div><span>下落</span><strong>${escapeHtml(formatNumber(viewModel.breadth.decliners, 0))}</strong></div>
          <div><span>横ばい</span><strong>${escapeHtml(formatNumber(viewModel.breadth.unchanged, 0))}</strong></div>
          <div><span>騰落比率</span><strong>${escapeHtml(formatNumber(viewModel.breadth.advanceDeclineRatio, 2))}</strong></div>
        </div>
      </section>

      <section class="marketIntelligenceSection" aria-labelledby="marketSectorTitle">
        <div class="marketIntelligenceSectionHeader">
          <h3 id="marketSectorTitle">Sector Strength</h3>
          <span>${escapeHtml(formatNumber(viewModel.sectors.sectorCount, 0))}業種</span>
        </div>
        <div class="marketIntelligenceSectorGrid">
          <div>
            <h4>上位</h4>
            <ul>${sectorListHtml(viewModel.sectors.leaders, "データ待ち")}</ul>
          </div>
          <div>
            <h4>下位</h4>
            <ul>${sectorListHtml(viewModel.sectors.laggards, "データ待ち")}</ul>
          </div>
        </div>
      </section>
    </div>

    <section class="marketIntelligenceSection" aria-labelledby="marketProviderTitle">
      <div class="marketIntelligenceSectionHeader">
        <h3 id="marketProviderTitle">Provider Health</h3>
        <span>未取得値は0として扱いません</span>
      </div>
      <div class="marketIntelligenceProviderGrid">
        ${viewModel.providers.map(providerHtml).join("")}
      </div>
    </section>

    <p class="marketIntelligenceNotice">${escapeHtml(viewModel.notice)}</p>
  `;

  root.dataset.marketIntelligenceState = viewModel.status.className;
  root.dataset.marketIntelligenceExecution = "disabled";
  root.setAttribute?.(
    "aria-busy",
    viewModel.status.className === "loading" ? "true" : "false",
  );

  return { rendered: true, root };
}

function hasClass(element, className) {
  return String(element?.className ?? "")
    .split(/\s+/)
    .includes(className);
}

export function mountMarketIntelligenceDashboard({
  documentRef = globalThis.document,
} = {}) {
  if (!documentRef) {
    return { mounted: false, reason: "environment_unavailable", root: null };
  }

  const existing = documentRef.getElementById?.(
    "marketIntelligenceDashboard",
  );

  if (existing) {
    return { mounted: true, reused: true, root: existing };
  }

  const dashboard = documentRef.querySelector?.(".dashboardGrid");
  if (!dashboard) {
    return { mounted: false, reason: "dashboard_unavailable", root: null };
  }

  const root = documentRef.createElement("article");
  root.id = "marketIntelligenceDashboard";
  root.className = "marketIntelligenceDashboard fullWidthCard";
  root.setAttribute?.("aria-labelledby", "marketIntelligenceDashboardTitle");

  const children = Array.from(dashboard.children ?? []);
  const anchorIndex = children.findIndex((child) =>
    hasClass(child, "predictionOutputCard"),
  );
  const insertionPoint = anchorIndex >= 0 ? children[anchorIndex + 1] : null;

  if (insertionPoint && typeof dashboard.insertBefore === "function") {
    dashboard.insertBefore(root, insertionPoint);
  } else {
    dashboard.appendChild(root);
  }

  return { mounted: true, reused: false, root };
}

export const MarketIntelligenceDashboardPresenterInternals = Object.freeze({
  escapeHtml,
  finiteOrNull,
  formatNumber,
  formatPercent,
  formatTimestamp,
  normalizedProgress,
  metricHtml,
  directionClass,
  predictionHtml,
  providerHtml,
  sectorItemHtml,
  sectorListHtml,
  errorHtml,
  hasClass,
});

export default renderMarketIntelligenceDashboard;
