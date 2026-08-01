import {
  fetchIntradayHistory,
} from "../data.js";

import {
  createIntradayTradingDecision,
} from "./intraday-trading-decision.js";

const elements = {};

let stateProvider = null;
let intradayController = null;

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function formatNumber(
  value,
  maximumFractionDigits = 2,
) {
  if (!finite(value)) {
    return "--";
  }

  return new Intl.NumberFormat("ja-JP", {
    maximumFractionDigits,
  }).format(Number(value));
}

function formatPrice(value) {
  return finite(value)
    ? `${formatNumber(value, 2)}`
    : "--";
}

function formatAge(seconds) {
  if (!finite(seconds)) {
    return "--";
  }

  const value = Math.max(
    0,
    Number(seconds),
  );

  if (value < 60) {
    return `${Math.round(value)}秒`;
  }

  if (value < 3600) {
    return `${Math.floor(value / 60)}分`;
  }

  return `${Math.floor(value / 3600)}時間`;
}

function setStatus(
  text,
  state = "neutral",
) {
  elements.status.textContent = text;

  elements.status.classList.remove(
    "passed",
    "failed",
  );

  if (state === "passed") {
    elements.status.classList.add("passed");
  }

  if (state === "failed") {
    elements.status.classList.add("failed");
  }
}

function createMetric(label, value) {
  const item =
    document.createElement("div");

  item.className =
    "intradayTradingMetric";

  const labelElement =
    document.createElement("span");

  labelElement.textContent = label;

  const valueElement =
    document.createElement("strong");

  valueElement.textContent = value;

  item.append(
    labelElement,
    valueElement,
  );

  return item;
}

function renderReasons(
  reasons = [],
  warnings = [],
) {
  elements.reasons.replaceChildren();

  const messages = Array.from(
    new Set([
      ...reasons,
      ...warnings,
    ]),
  );

  if (!messages.length) {
    const empty =
      document.createElement("p");

    empty.className = "emptyState";
    empty.textContent =
      "短期セットアップの条件を確認しました。";

    elements.reasons.append(empty);
    return;
  }

  messages.forEach((message) => {
    const item =
      document.createElement("div");

    item.className =
      "intradayTradingReason";

    item.textContent = message;

    elements.reasons.append(item);
  });
}

function renderUnavailable(
  message,
) {
  setStatus("取得失敗", "failed");

  elements.description.textContent =
    message;

  elements.summary.replaceChildren(
    createMetric("判定", "取得失敗"),
  );

  renderReasons([message]);
}

export function renderIntradayTrading(
  decision,
) {
  if (!decision?.available) {
    renderUnavailable(
      decision?.reasons?.[0] ||
        "15分足データを取得できませんでした。",
    );

    return;
  }

  const analysis = decision.analysis;
  const plan = decision.plan;

  if (decision.paperCandidate) {
    setStatus(
      decision.actionLabel,
      "passed",
    );
  } else if (
    plan?.action === "blocked"
  ) {
    setStatus(
      decision.actionLabel,
      "failed",
    );
  } else {
    setStatus(
      decision.actionLabel,
      "neutral",
    );
  }

  elements.description.textContent =
    `${decision.setupLabel}。` +
    `${analysis.entryCondition || "条件待ち"}。` +
    `確定済み15分足${analysis.sessionBarCount || 0}本を使用。`;

  const quantity =
    finite(plan?.quantity)
      ? `${formatNumber(plan.quantity, 0)}株`
      : "--";

  const riskReward =
    finite(plan?.riskReward)
      ? `${formatNumber(plan.riskReward, 2)} R`
      : "--";

  const volumeRatio =
    finite(analysis.volumeRatio)
      ? `${formatNumber(analysis.volumeRatio, 2)}倍`
      : "--";

  const quality =
    finite(analysis.dataQualityScore)
      ? `${formatNumber(
          analysis.dataQualityScore,
          0,
        )} / 100`
      : "--";

  const strength =
    finite(
      analysis.setupStrengthScore,
    )
      ? `${formatNumber(
          analysis.setupStrengthScore,
          0,
        )} / 100`
      : "--";

  elements.summary.replaceChildren(
    createMetric(
      "短期判断",
      decision.actionLabel,
    ),
    createMetric(
      "セットアップ",
      decision.setupLabel,
    ),
    createMetric(
      "現在値",
      formatPrice(analysis.currentPrice),
    ),
    createMetric(
      "日中VWAP",
      formatPrice(analysis.vwap),
    ),
    createMetric(
      "15分ATR",
      formatPrice(analysis.atr),
    ),
    createMetric(
      "出来高倍率",
      volumeRatio,
    ),
    createMetric(
      "直近高値",
      formatPrice(analysis.priorHigh),
    ),
    createMetric(
      "直近安値",
      formatPrice(analysis.priorLow),
    ),
    createMetric(
      "エントリー候補",
      formatPrice(plan?.entryPrice),
    ),
    createMetric(
      "損切り候補",
      formatPrice(plan?.stopPrice),
    ),
    createMetric(
      "第1利確候補",
      formatPrice(
        plan?.firstTargetPrice,
      ),
    ),
    createMetric(
      "第2利確候補",
      formatPrice(
        plan?.secondTargetPrice,
      ),
    ),
    createMetric(
      "仮想数量",
      quantity,
    ),
    createMetric(
      "リスクリワード",
      riskReward,
    ),
    createMetric(
      "セットアップ強度",
      strength,
    ),
    createMetric(
      "データ品質",
      quality,
    ),
    createMetric(
      "確定足の経過時間",
      formatAge(
        analysis.dataAgeSeconds,
      ),
    ),
    createMetric(
      "実注文",
      "無効",
    ),
  );

  renderReasons(
    decision.reasons,
    decision.warnings,
  );
}

function setLoading(loading) {
  elements.refreshButton.disabled =
    loading;

  elements.refreshButton.textContent =
    loading
      ? "15分足を取得中"
      : "短期判断を更新";

  if (loading) {
    setStatus("取得中");
  }
}

function paperAccount() {
  const equity =
    Number(elements.paperEquity.value);

  return {
    executionMode: "paper",

    equity:
      finite(equity) && equity > 0
        ? equity
        : 1_000_000,

    openPositions: 0,
    dailyPnlPercent: 0,
    consecutiveLosses: 0,
  };
}

export async function refreshIntradayTrading(
  suppliedState = null,
) {
  const state =
    suppliedState ||
    stateProvider?.();

  const symbol = state?.symbol;

  if (!symbol) {
    renderUnavailable(
      "先に通常分析を実行してください。",
    );

    return null;
  }

  intradayController?.abort();

  intradayController =
    new AbortController();

  setLoading(true);

  try {
    const history =
      await fetchIntradayHistory(
        symbol,
        {
          signal:
            intradayController.signal,
        },
      );

    const decision =
      createIntradayTradingDecision({
        symbol,
        intradayHistory: history,
        account: paperAccount(),

        lotSize:
          symbol.endsWith(".T")
            ? 100
            : 1,
      });

    renderIntradayTrading(decision);

    return decision;
  } catch (error) {
    if (error.name !== "AbortError") {
      console.error(
        "Intraday trading:",
        error,
      );

      renderUnavailable(
        error.message ||
          "15分足の取得に失敗しました。",
      );
    }

    return null;
  } finally {
    setLoading(false);
  }
}

export function initIntradayTrading(
  getState,
) {
  stateProvider = getState;

  [
    "intradayTradingStatus",
    "intradayTradingDescription",
    "intradayTradingSummary",
    "intradayTradingReasons",
    "paperEquity",
    "refreshIntradayButton",
  ].forEach((id) => {
    elements[
      id
        .replace(
          "intradayTrading",
          "",
        )
        .replace(/^./, (value) =>
          value.toLowerCase(),
        )
    ] = document.getElementById(id);
  });

  elements.status =
    document.getElementById(
      "intradayTradingStatus",
    );

  elements.description =
    document.getElementById(
      "intradayTradingDescription",
    );

  elements.summary =
    document.getElementById(
      "intradayTradingSummary",
    );

  elements.reasons =
    document.getElementById(
      "intradayTradingReasons",
    );

  elements.paperEquity =
    document.getElementById(
      "paperEquity",
    );

  elements.refreshButton =
    document.getElementById(
      "refreshIntradayButton",
    );

  elements.refreshButton.addEventListener(
    "click",
    () => {
      void refreshIntradayTrading();
    },
  );
}