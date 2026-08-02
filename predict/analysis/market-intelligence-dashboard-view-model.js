import { buildMarketIntelligenceView } from "./prediction-lab-v3-dashboard.js";
import { PREDICTION_HORIZONS } from "../market-intelligence/multi-horizon-prediction-engine.js";

export const MARKET_INTELLIGENCE_DASHBOARD_VERSION =
  "market-intelligence-dashboard-v1";

const METRIC_DEFINITIONS = Object.freeze([
  Object.freeze({ key: "marketScore", label: "MarketScore" }),
  Object.freeze({ key: "breadth", label: "Breadth" }),
  Object.freeze({ key: "liquidity", label: "Liquidity" }),
  Object.freeze({ key: "newsScore", label: "NewsScore" }),
  Object.freeze({ key: "sectorStrength", label: "SectorStrength" }),
  Object.freeze({ key: "compositeAI", label: "CompositeAI" }),
]);

const STATUS_PRESENTATION = Object.freeze({
  idle: Object.freeze({ label: "分析待ち", className: "idle" }),
  loading: Object.freeze({ label: "計算中", className: "loading" }),
  ready: Object.freeze({ label: "算出済み", className: "ready" }),
  partial: Object.freeze({ label: "一部データ", className: "partial" }),
  unavailable: Object.freeze({ label: "データ待ち", className: "unavailable" }),
  error: Object.freeze({ label: "取得失敗", className: "error" }),
});

const PROVIDER_PRESENTATION = Object.freeze({
  available: Object.freeze({ label: "接続済み", className: "available" }),
  ready: Object.freeze({ label: "接続済み", className: "available" }),
  partial: Object.freeze({ label: "一部取得", className: "partial" }),
  stale: Object.freeze({ label: "更新遅延", className: "stale" }),
  not_configured: Object.freeze({ label: "未設定", className: "unavailable" }),
  not_applicable: Object.freeze({ label: "対象外", className: "neutral" }),
  unavailable: Object.freeze({ label: "取得不可", className: "unavailable" }),
  error: Object.freeze({ label: "取得失敗", className: "error" }),
});

function finiteOrNull(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function clamp(value, minimum = 0, maximum = 100) {
  const number = finiteOrNull(value);
  return number === null
    ? null
    : Math.min(maximum, Math.max(minimum, number));
}

function timestampOrNull(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function resolveResult(report) {
  const root = report?.result ?? report ?? null;
  const prediction = root?.features
    ? root
    : root?.prediction?.features
      ? root.prediction
      : null;

  return {
    root,
    prediction,
  };
}

function fallbackReport(root, key) {
  const reports = {
    marketScore: root?.compositeMarket ?? root?.marketSnapshot ?? null,
    breadth: root?.breadth ?? null,
    liquidity: root?.liquidity ?? null,
    newsScore: root?.newsIntelligence ?? null,
    sectorStrength: root?.sectorStrength ?? null,
    compositeAI: null,
  };

  return reports[key];
}

function metricView(root, prediction, definition) {
  const detail = prediction?.features?.details?.[definition.key] ?? null;
  const fallback = fallbackReport(root, definition.key);
  const score = clamp(detail?.score ?? fallback?.score);
  const confidence = clamp(detail?.confidence ?? fallback?.confidence);
  const coverage = clamp(detail?.coverage ?? fallback?.coverage);
  const available = Boolean(
    detail?.available === true ||
      (score !== null && confidence !== null && confidence > 0),
  );

  return {
    key: definition.key,
    label: definition.label,
    score: available ? score : null,
    confidence: available ? confidence : null,
    coverage: available ? coverage : null,
    source: String(detail?.source ?? fallback?.source ?? "unknown"),
    available,
  };
}

function predictionViews(report) {
  const shared = buildMarketIntelligenceView(report ?? {});
  const predictions = new Map(
    shared.predictions.map((prediction) => [prediction.horizon, prediction]),
  );

  return PREDICTION_HORIZONS.map((horizon) => {
    const prediction = predictions.get(horizon) ?? null;
    const available = Boolean(
      prediction &&
        prediction.score !== null &&
        prediction.confidence > 0,
    );

    return {
      horizon,
      label: `${horizon}日`,
      direction: available ? String(prediction.direction) : "判定不能",
      score: available ? clamp(prediction.score) : null,
      confidence: available ? clamp(prediction.confidence) : null,
      status: prediction?.status ?? "unavailable",
      selected: horizon === shared.selectedHorizon,
      available,
    };
  });
}

function providerPresentation(status) {
  return (
    PROVIDER_PRESENTATION[String(status || "").toLowerCase()] ??
    PROVIDER_PRESENTATION.unavailable
  );
}

function providerView({
  key,
  label,
  source,
  status,
  coverage = null,
  timestamp = null,
  detail = "",
}) {
  const presentation = providerPresentation(status);

  return {
    key,
    label,
    source: String(source || "未取得"),
    status: String(status || "unavailable"),
    statusLabel: presentation.label,
    statusClass: presentation.className,
    coverage: clamp(coverage),
    timestamp: timestampOrNull(timestamp),
    detail: String(detail || ""),
  };
}

function latestCollectionTimestamp(items) {
  const timestamps = (Array.isArray(items) ? items : [])
    .map((item) => Date.parse(item?.publishedAt ?? item?.timestamp))
    .filter(Number.isFinite);

  return timestamps.length
    ? new Date(Math.max(...timestamps)).toISOString()
    : null;
}

function providerViews(state, root) {
  const breadthSource = state?.marketBreadthSource ?? {};
  const environment = state?.marketEnvironment ?? {};
  const context = state?.context ?? {};
  const environmentAvailable = Math.max(
    0,
    finiteOrNull(environment.availableCount) ?? 0,
  );
  const environmentRequested = Math.max(
    environmentAvailable,
    finiteOrNull(environment.requestedCount) ?? environmentAvailable,
  );
  const environmentCoverage = environmentRequested > 0
    ? (environmentAvailable / environmentRequested) * 100
    : null;
  const environmentStatus = environmentAvailable === 0
    ? "unavailable"
    : environmentAvailable < environmentRequested
      ? "partial"
      : "available";
  const breadthAvailable = Math.max(
    0,
    finiteOrNull(breadthSource.availableCount) ??
      finiteOrNull(root?.breadth?.availableCount) ??
      0,
  );
  const breadthRequested = Math.max(
    breadthAvailable,
    finiteOrNull(breadthSource.expectedObservationCount) ??
      finiteOrNull(root?.breadth?.requestedCount) ??
      breadthAvailable,
  );
  const environmentSeries = Array.isArray(environment.series)
    ? environment.series
    : [];

  return [
    providerView({
      key: "breadth",
      label: "市場Breadth",
      source: breadthSource.source ?? "Ark Screener",
      status: breadthSource.status ?? (breadthAvailable ? "available" : "unavailable"),
      coverage:
        breadthSource.coverage ??
        root?.breadth?.coverage ??
        null,
      timestamp: breadthSource.timestamp ?? root?.breadth?.timestamp,
      detail: breadthRequested
        ? `${breadthAvailable}/${breadthRequested}銘柄`
        : "構成銘柄データなし",
    }),
    providerView({
      key: "environment",
      label: "指数・為替",
      source: "Market Data Core",
      status: environmentStatus,
      coverage: environmentCoverage,
      timestamp:
        environmentSeries
          ?.map((item) => item?.timestamp)
          .filter(Boolean)
          .sort()
          .at(-1) ?? null,
      detail: environmentRequested
        ? `${environmentAvailable}/${environmentRequested}系列`
        : "系列データなし",
    }),
    providerView({
      key: "news",
      label: "企業ニュース",
      source: context.providers?.news ?? "Finnhub",
      status: context.status?.news ?? (context.news?.length ? "available" : "unavailable"),
      coverage: root?.newsIntelligence?.coverage ?? null,
      timestamp: latestCollectionTimestamp(context.news),
      detail: `${Array.isArray(context.news) ? context.news.length : 0}件`,
    }),
    providerView({
      key: "tdnet",
      label: "適時開示",
      source: context.providers?.disclosures ?? "J-Quants TDnet",
      status:
        context.status?.disclosures ??
        (context.disclosures?.length ? "available" : "not_configured"),
      timestamp: latestCollectionTimestamp(context.disclosures),
      detail: `${Array.isArray(context.disclosures) ? context.disclosures.length : 0}件`,
    }),
  ];
}

function breadthView(root) {
  const report = root?.breadth ?? {};
  const score = clamp(report.score);
  const availableCount = Math.max(0, finiteOrNull(report.availableCount) ?? 0);
  const available = score !== null && availableCount > 0;

  return {
    available,
    score: available ? score : null,
    advancers: available
      ? Math.max(0, finiteOrNull(report.advancers) ?? 0)
      : null,
    decliners: available
      ? Math.max(0, finiteOrNull(report.decliners) ?? 0)
      : null,
    unchanged: available
      ? Math.max(0, finiteOrNull(report.unchanged) ?? 0)
      : null,
    availableCount: available ? availableCount : null,
    requestedCount: available
      ? Math.max(
          availableCount,
          finiteOrNull(report.requestedCount) ?? availableCount,
        )
      : null,
    coverage: available ? clamp(report.coverage) : null,
    advanceDeclineRatio: available
      ? finiteOrNull(report.advanceDeclineRatio)
      : null,
  };
}

function sectorItem(item) {
  const score = clamp(item?.score);

  return {
    name: String(item?.sector || "未分類"),
    score,
    confidence: clamp(item?.confidence) ?? 0,
    averageChangePercent: finiteOrNull(item?.averageChangePercent),
    available: score !== null,
  };
}

function sectorView(root) {
  const report = root?.sectorStrength ?? {};
  const available = clamp(report.score) !== null;

  return {
    available,
    sectorCount: available
      ? Math.max(0, finiteOrNull(report.sectorCount) ?? 0)
      : null,
    positiveSectors: available
      ? Math.max(0, finiteOrNull(report.positiveSectors) ?? 0)
      : null,
    negativeSectors: available
      ? Math.max(0, finiteOrNull(report.negativeSectors) ?? 0)
      : null,
    leaders: (Array.isArray(report.leaders) ? report.leaders : [])
      .slice(0, 3)
      .map(sectorItem),
    laggards: (Array.isArray(report.laggards) ? report.laggards : [])
      .slice(0, 3)
      .map(sectorItem),
  };
}

function statusView(report, prediction, phase, error) {
  let status = String(phase || "").toLowerCase();

  if (!status) {
    if (error || report?.error || report?.status === "error") {
      status = "error";
    } else if (prediction?.features?.status === "ready") {
      status = "ready";
    } else if (
      prediction?.features?.status === "partial" ||
      report?.status === "partial" ||
      report?.status === "validation_required"
    ) {
      status = "partial";
    } else {
      status = "unavailable";
    }
  }

  const normalized = Object.hasOwn(STATUS_PRESENTATION, status)
    ? status
    : "unavailable";
  const presentation = STATUS_PRESENTATION[normalized];

  return {
    key: normalized,
    label: presentation.label,
    className: presentation.className,
  };
}

function dashboardMessage(status) {
  const messages = {
    idle: "通常分析を実行すると、市場特徴量を自動計算します。",
    loading: "既存のMarket Intelligence Engineで市場特徴量を計算しています。",
    ready: "利用可能な実データから市場特徴量と期間別予測を算出しました。",
    partial: "一部の情報が未取得のため、利用可能な特徴量だけで算出しています。",
    unavailable: "市場特徴量をまだ算出できません。Provider状態を確認してください。",
    error: "Market Intelligenceの計算に失敗しました。通常分析の結果は維持されます。",
  };

  return messages[status] ?? messages.unavailable;
}

export function buildMarketIntelligenceDashboardViewModel({
  report = null,
  state = {},
  phase = null,
  error = null,
} = {}) {
  const { root, prediction } = resolveResult(report);
  const status = statusView(report, prediction, phase, error);
  const metrics = METRIC_DEFINITIONS.map((definition) =>
    metricView(root, prediction, definition),
  );
  const composite = metrics.find((metric) => metric.key === "compositeAI");

  return {
    version: MARKET_INTELLIGENCE_DASHBOARD_VERSION,
    title: "Market Intelligence",
    heading: "市場インテリジェンス",
    symbol: String(state?.symbol ?? "--"),
    status,
    message: dashboardMessage(status.key),
    compositeScore: composite?.score ?? null,
    featureCoverage: clamp(prediction?.features?.coverage),
    featureConfidence: clamp(prediction?.features?.confidence),
    calculatedAt: timestampOrNull(
      prediction?.timestamp ?? root?.timestamp ?? report?.result?.timestamp,
    ),
    metrics,
    predictions: predictionViews(report),
    breadth: breadthView(root),
    sectors: sectorView(root),
    providers: providerViews(state, root),
    selectedHorizon: finiteOrNull(report?.selectedHorizon) ?? 5,
    errorMessage: error?.message ?? report?.error?.message ?? null,
    notice:
      "スコアと信頼度は分析用指標であり、価格上昇確率や利益を保証しません。",
    executionAllowed: false,
  };
}

export const MarketIntelligenceDashboardViewModelInternals = Object.freeze({
  METRIC_DEFINITIONS,
  STATUS_PRESENTATION,
  PROVIDER_PRESENTATION,
  finiteOrNull,
  clamp,
  timestampOrNull,
  resolveResult,
  fallbackReport,
  metricView,
  predictionViews,
  providerPresentation,
  providerView,
  latestCollectionTimestamp,
  providerViews,
  breadthView,
  sectorItem,
  sectorView,
  statusView,
  dashboardMessage,
});

export default buildMarketIntelligenceDashboardViewModel;
