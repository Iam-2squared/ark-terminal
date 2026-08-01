import {
  analyzeIntradayMarket,
} from "./intraday-market.js";

import {
  createShortTermTradePlan,
  TRADE_ACTIONS,
} from "./short-term-core.js";

export const INTRADAY_TRADING_INTEGRATION_VERSION =
  "intraday-trading-integration-v1";

export const DEFAULT_INTRADAY_TRADING_POLICY =
  Object.freeze({
    requireSpreadData: false,
    maximumDataAgeSeconds: 20 * 60,
  });

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function positive(value) {
  return finite(value) && Number(value) > 0;
}

export function tradeActionLabel(action) {
  const labels = {
    [TRADE_ACTIONS.ENTER_LONG]: "買い候補",
    [TRADE_ACTIONS.ENTER_SHORT]: "空売り候補",
    [TRADE_ACTIONS.WAIT]: "待機",
    [TRADE_ACTIONS.BLOCKED]: "取引停止",
    [TRADE_ACTIONS.HOLD]: "保有継続",
    [TRADE_ACTIONS.TAKE_PARTIAL]: "一部利確",
    [TRADE_ACTIONS.EXIT]: "決済",
  };

  return labels[action] || "判定不能";
}

export function setupLabel(setup) {
  const labels = {
    breakout_long: "上方向ブレイク",
    breakout_short: "下方向ブレイク",
    vwap_reclaim_long: "VWAP上抜け",
    vwap_reclaim_short: "VWAP下抜け",
    pullback_long: "押し目反発",
    pullback_short: "戻り売り",
    stale_data: "市場外・データ更新待ち",
    insufficient_data: "15分足不足",
    wait: "セットアップ待ち",
  };

  return labels[setup] || setup || "未分類";
}

export function createIntradayTradingDecision({
  symbol,
  intradayHistory,
  account = {},
  lotSize,
  spreadPercent = null,
  nowSeconds,
  policy = {},
} = {}) {
  const candles =
    intradayHistory?.candles;

  if (!Array.isArray(candles) || !candles.length) {
    return {
      version:
        INTRADAY_TRADING_INTEGRATION_VERSION,
      available: false,
      ready: false,
      action: TRADE_ACTIONS.BLOCKED,
      actionLabel: "取得失敗",
      setupLabel: "15分足なし",
      analysis: null,
      plan: null,
      reasons: [
        "15分足データを取得できませんでした。",
      ],
      warnings: [],
    };
  }

  const analysisOptions = {
    policy: policy.intraday || {},
  };

  if (finite(nowSeconds)) {
    analysisOptions.nowSeconds =
      Number(nowSeconds);
  }

  const analysis =
    analyzeIntradayMarket(
      candles,
      analysisOptions,
    );

  const signal = {
    ...(analysis.tradeSignal || {}),

    direction:
      analysis.direction || "中立",

    currentPrice:
      analysis.currentPrice ?? null,

    atr:
      analysis.atr ?? null,

    confidenceScore:
      analysis.setupStrengthScore ?? null,

    dataQualityScore:
      analysis.dataQualityScore ?? null,

    spreadPercent:
      finite(spreadPercent)
        ? Number(spreadPercent)
        : null,

    dataAgeSeconds:
      analysis.dataAgeSeconds ?? null,

    setup:
      analysis.setup || "wait",

    entryCondition:
      analysis.entryCondition ||
      "短期セットアップ待ち",

    marketBlocked:
      analysis.marketBlocked === true,

    marketBlockReason:
      analysis.marketBlocked
        ? analysis.reasons?.[0] ||
          "市場データ更新待ち"
        : null,
  };

  const resolvedAccount = {
    executionMode: "paper",
    equity: 1_000_000,
    openPositions: 0,
    dailyPnlPercent: 0,
    consecutiveLosses: 0,
    ...(account || {}),
  };

  const resolvedLotSize =
    positive(lotSize)
      ? Math.floor(Number(lotSize))
      : String(symbol || "")
          .toUpperCase()
          .endsWith(".T")
        ? 100
        : 1;

  const tradingPolicy = {
    ...DEFAULT_INTRADAY_TRADING_POLICY,
    ...(policy.trading || {}),
  };

  const plan =
    createShortTermTradePlan({
      signal,
      account: resolvedAccount,
      lotSize: resolvedLotSize,
      policy: tradingPolicy,
    });

  const warnings = [];

  if (!finite(spreadPercent)) {
    warnings.push(
      "売買スプレッドをまだ取得していないため、Paper候補の計算では未反映です。",
    );
  }

  warnings.push(
    "手数料・税金・約定滑りは未反映です。",
  );

  warnings.push(
    "短期セットアップ強度は未校正で、的中確率ではありません。",
  );

  const reasons = Array.from(
    new Set([
      ...(analysis.reasons || []),
      ...(plan.reasons || []),
    ]),
  );

  return {
    version:
      INTRADAY_TRADING_INTEGRATION_VERSION,

    available: true,
    ready:
      analysis.ready === true &&
      analysis.marketBlocked !== true,

    symbol,
    analysis,
    plan,

    action: plan.action,
    actionLabel:
      tradeActionLabel(plan.action),

    setupLabel:
      setupLabel(analysis.setup),

    paperCandidate:
      plan.action ===
        TRADE_ACTIONS.ENTER_LONG ||
      plan.action ===
        TRADE_ACTIONS.ENTER_SHORT,

    liveExecutionAllowed: false,
    executionMode: "paper",
    estimatedCostsIncluded: false,

    reasons,
    warnings,
  };
}

export const IntradayTradingDecisionInternals = {
  finite,
  positive,
};