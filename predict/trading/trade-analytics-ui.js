import {
  renderTradeAnalyticsHtml,
} from "./trade-analytics-presenter.js";

export const TRADE_ANALYTICS_UI_VERSION =
  "trade-analytics-ui-v1";

export const DEFAULT_TRADE_ANALYTICS_ROOT_ID =
  "intraday-trade-analytics";

function validRoot(root) {
  return Boolean(
    root &&
    typeof root === "object" &&
    "innerHTML" in root
  );
}

export function findTradeAnalyticsRoot({
  documentRef =
    globalThis.document,
  rootId =
    DEFAULT_TRADE_ANALYTICS_ROOT_ID,
} = {}) {
  if (
    !documentRef ||
    typeof documentRef
      .getElementById !==
      "function"
  ) {
    return null;
  }

  return (
    documentRef.getElementById(
      rootId,
    ) || null
  );
}

export function createTradeAnalyticsRoot({
  documentRef =
    globalThis.document,
  parent,
  rootId =
    DEFAULT_TRADE_ANALYTICS_ROOT_ID,
} = {}) {
  if (
    !documentRef ||
    typeof documentRef
      .createElement !==
      "function"
  ) {
    return null;
  }

  if (
    !parent ||
    typeof parent
      .appendChild !==
      "function"
  ) {
    return null;
  }

  const existing =
    findTradeAnalyticsRoot({
      documentRef,
      rootId,
    });

  if (existing) {
    return existing;
  }

  const root =
    documentRef.createElement(
      "div",
    );

  root.id =
    rootId;

  root.dataset.component =
    "trade-analytics";

  parent.appendChild(root);

  return root;
}

export function mountTradeAnalytics({
  root,
  analytics = {},
} = {}) {
  if (!validRoot(root)) {
    return {
      mounted: false,
      reason:
        "missing_root",
      root: null,
      html: "",
    };
  }

  const html =
    renderTradeAnalyticsHtml(
      analytics,
    );

  root.innerHTML =
    html;

  if (root.dataset) {
    root.dataset.mounted =
      "true";

    root.dataset.version =
      TRADE_ANALYTICS_UI_VERSION;
  }

  return {
    mounted: true,
    reason: null,
    root,
    html,
  };
}

export function clearTradeAnalytics({
  root,
} = {}) {
  if (!validRoot(root)) {
    return false;
  }

  root.innerHTML = "";

  if (root.dataset) {
    root.dataset.mounted =
      "false";
  }

  return true;
}

export function mountTradeAnalyticsById({
  analytics = {},
  documentRef =
    globalThis.document,
  rootId =
    DEFAULT_TRADE_ANALYTICS_ROOT_ID,
} = {}) {
  const root =
    findTradeAnalyticsRoot({
      documentRef,
      rootId,
    });

  return mountTradeAnalytics({
    root,
    analytics,
  });
}

export function resolveAnalyticsFromBacktestModes(
  result = {},
  {
    preferredMode =
      "signal",
  } = {},
) {
  if (
    preferredMode ===
      "executable" &&
    result.executable
      ?.analytics
  ) {
    return (
      result.executable
        .analytics
    );
  }

  if (
    result.signal
      ?.analytics
  ) {
    return (
      result.signal.analytics
    );
  }

  if (
    result.executable
      ?.analytics
  ) {
    return (
      result.executable
        .analytics
    );
  }

  if (result.analytics) {
    return result.analytics;
  }

  return {};
}

export function mountBacktestTradeAnalytics({
  result = {},
  preferredMode =
    "signal",
  root,
} = {}) {
  const analytics =
    resolveAnalyticsFromBacktestModes(
      result,
      {
        preferredMode,
      },
    );

  return mountTradeAnalytics({
    root,
    analytics,
  });
}

export const TradeAnalyticsUiInternals = {
  validRoot,
};