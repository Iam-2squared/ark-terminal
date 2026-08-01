import {
  fetchIntradayHistory,
} from "../data.js";

import {
  runIntradayBacktestModes,
} from "./intraday-backtest-modes.js";

const SVG_NAMESPACE =
  "http://www.w3.org/2000/svg";

const elements = {};

let stateProvider = null;
let backtestController = null;

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

function formatCurrency(
  value,
  signed = false,
) {
  if (!finite(value)) {
    return "--";
  }

  const number = Number(value);
  const prefix =
    signed && number > 0
      ? "+"
      : "";

  return `${prefix}¥${formatNumber(number, 0)}`;
}

function formatPercent(
  value,
  signed = false,
) {
  if (!finite(value)) {
    return "--";
  }

  const number = Number(value);
  const prefix =
    signed && number > 0
      ? "+"
      : "";

  return `${prefix}${formatNumber(number, 2)}%`;
}

function formatDateTime(time) {
  if (!finite(time)) {
    return "--";
  }

  const date =
    new Date(Number(time) * 1000);

  if (Number.isNaN(date.getTime())) {
    return "--";
  }

  return new Intl.DateTimeFormat(
    "ja-JP",
    {
      timeZone: "Asia/Tokyo",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    },
  ).format(date);
}

function setupLabel(setup) {
  const labels = {
    breakout_long: "上方向ブレイク",
    breakout_short: "下方向ブレイク",
    vwap_reclaim_long: "VWAP上抜け",
    vwap_reclaim_short: "VWAP下抜け",
    pullback_long: "押し目反発",
    pullback_short: "戻り売り",
    backtest: "短期セットアップ",
  };

  return labels[setup] ||
    setup ||
    "未分類";
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
    elements.status.classList.add(
      "passed",
    );
  }

  if (state === "failed") {
    elements.status.classList.add(
      "failed",
    );
  }
}

function createMetric(
  label,
  value,
  state = null,
) {
  const item =
    document.createElement("div");

  item.className =
    "intradayBacktestMetric";

  const labelElement =
    document.createElement("span");

  labelElement.textContent = label;

  const valueElement =
    document.createElement("strong");

  valueElement.textContent = value;

  if (state) {
    valueElement.classList.add(state);
  }

  item.append(
    labelElement,
    valueElement,
  );

  return item;
}

function valueState(value) {
  if (!finite(value)) {
    return null;
  }

  if (Number(value) > 0) {
    return "positive";
  }

  if (Number(value) < 0) {
    return "negative";
  }

  return "neutral";
}

function createSvgElement(
  name,
  attributes = {},
) {
  const element =
    document.createElementNS(
      SVG_NAMESPACE,
      name,
    );

  Object.entries(attributes).forEach(
    ([key, value]) => {
      element.setAttribute(
        key,
        String(value),
      );
    },
  );

  return element;
}

function renderEquityCurve(result) {
  elements.chart.replaceChildren();

  const curve =
    (result.equityCurve || [])
      .filter((point) =>
        finite(point.equity),
      );

  if (curve.length < 2) {
    const empty =
      document.createElement("p");

    empty.className = "emptyState";
    empty.textContent =
      "資産曲線を描くためのデータが不足しています。";

    elements.chart.append(empty);
    return;
  }

  const width = 900;
  const height = 260;
  const padding = 28;

  const equities =
    curve.map((point) =>
      Number(point.equity),
    );

  const actualMinimum =
    Math.min(...equities);

  const actualMaximum =
    Math.max(...equities);

  let plotMinimum =
    actualMinimum;

  let plotMaximum =
    actualMaximum;

  if (
    plotMinimum ===
    plotMaximum
  ) {
    const visualPadding =
      Math.max(
        1,
        Math.abs(
          plotMinimum,
        ) * 0.0001,
      );

    plotMinimum -=
      visualPadding;

    plotMaximum +=
      visualPadding;
  }

  const usableWidth =
    width - padding * 2;

  const usableHeight =
    height - padding * 2;

  const xFor = (index) =>
    padding +
    (
      index /
      Math.max(
        1,
        curve.length - 1,
      )
    ) *
      usableWidth;

  const yFor = (value) =>
    padding +
    (
      1 -
      (
        Number(value) -
        plotMinimum
      ) /
        (
          plotMaximum -
          plotMinimum
        )
    ) *
      usableHeight;

  const svg =
    createSvgElement(
      "svg",
      {
        viewBox:
          `0 0 ${width} ${height}`,

        role: "img",

        "aria-label":
          "短期バックテスト資産曲線",
      },
    );

  svg.classList.add(
    "intradayBacktestSvg",
  );

  const initialEquity =
    result.account
      ?.initialEquity;

  if (finite(initialEquity)) {
    const baseline =
      createSvgElement(
        "line",
        {
          x1: padding,
          x2:
            width - padding,

          y1:
            yFor(initialEquity),

          y2:
            yFor(initialEquity),
        },
      );

    baseline.classList.add(
      "intradayBacktestBaseline",
    );

    svg.append(baseline);
  }

  const points =
    curve
      .map(
        (point, index) =>
          `${xFor(index)},${yFor(
            point.equity,
          )}`,
      )
      .join(" ");

  const line =
    createSvgElement(
      "polyline",
      {
        points,
        fill: "none",
      },
    );

  line.classList.add(
    "intradayBacktestLine",
  );

  svg.append(line);

  const start =
    createSvgElement(
      "circle",
      {
        cx: xFor(0),
        cy:
          yFor(
            curve[0].equity,
          ),
        r: 4,
      },
    );

  start.classList.add(
    "intradayBacktestPoint",
  );

  const lastIndex =
    curve.length - 1;

  const end =
    createSvgElement(
      "circle",
      {
        cx:
          xFor(lastIndex),

        cy:
          yFor(
            curve[lastIndex]
              .equity,
          ),

        r: 5,
      },
    );

  end.classList.add(
    "intradayBacktestPoint",
    "ending",
  );

  svg.append(
    start,
    end,
  );

  const legend =
    document.createElement("div");

  legend.className =
    "intradayBacktestChartLegend";

  legend.append(
    createMetric(
      "曲線内最高資産",
      formatCurrency(actualMaximum),
    ),

    createMetric(
      "曲線内最低資産",
      formatCurrency(actualMinimum),
    ),
  );

  elements.chart.append(
    svg,
    legend,
  );
}

function appendCell(
  row,
  value,
  className = null,
) {
  const cell =
    document.createElement("td");

  cell.textContent = value;

  if (className) {
    cell.classList.add(
      className,
    );
  }

  row.append(cell);
}

function renderTrades(result) {
  elements.trades.replaceChildren();

  const trades =
    result.trades || [];

  if (!trades.length) {
    const empty =
      document.createElement("p");

    empty.className = "emptyState";
    empty.textContent =
      "今回の期間では、取引条件を満たす売買はありませんでした。";

    elements.trades.append(empty);
    return;
  }

  const wrapper =
    document.createElement("div");

  wrapper.className =
    "intradayBacktestTableWrapper";

  const table =
    document.createElement("table");

  table.className =
    "intradayBacktestTable";

  const header =
    document.createElement("thead");

  const headerRow =
    document.createElement("tr");

  [
    "日時",
    "方向",
    "セットアップ",
    "エントリー",
    "決済",
    "数量",
    "純損益",
    "損益率",
    "決済理由",
  ].forEach((label) => {
    const cell =
      document.createElement("th");

    cell.textContent = label;
    headerRow.append(cell);
  });

  header.append(headerRow);

  const body =
    document.createElement("tbody");

  trades
    .slice(-100)
    .forEach((trade) => {
      const row =
        document.createElement("tr");

      const state =
        valueState(trade.netPnl);

      appendCell(
        row,
        formatDateTime(
          trade.entryTime,
        ),
      );

      appendCell(
        row,
        trade.side === "long"
          ? "買い"
          : "空売り",
      );

      appendCell(
        row,
        setupLabel(
          trade.setup,
        ),
      );

      appendCell(
        row,
        formatNumber(
          trade.entryPrice,
          2,
        ),
      );

      appendCell(
        row,
        formatNumber(
          trade.exitPrice,
          2,
        ),
      );

      appendCell(
        row,
        formatNumber(
          trade.initialQuantity,
          0,
        ),
      );

      appendCell(
        row,
        formatCurrency(
          trade.netPnl,
          true,
        ),
        state,
      );

      appendCell(
        row,
        formatPercent(
          trade.returnPercent,
          true,
        ),
        state,
      );

      appendCell(
        row,
        trade.exitReason ||
          "--",
      );

      body.append(row);
    });

  table.append(
    header,
    body,
  );

  wrapper.append(table);
  elements.trades.append(wrapper);
}

function renderWarnings(
  result,
  executableResult = null,
) {
  elements.warnings.replaceChildren();

  const warnings = [
    ...(result.warnings || []),
  ];

  if (
    Number(
      result.meta?.closedBarCount ||
      0,
    ) < 200
  ) {
    warnings.push(
      "検証足が200本未満のため、成績の判断には少なすぎます。",
    );
  }

  if (
    Number(
      result.metrics?.tradeCount ||
      0,
    ) < 30
  ) {
    warnings.push(
      "取引数が30回未満のため、勝率やProfit Factorは暫定値です。",
    );
  }

  const diagnostics =
    result.diagnostics || {};

  if (
    Number(
      result.meta
        ?.candidateCount || 0,
    ) === 0 &&
    Number(
      result.meta
        ?.signalEvaluationCount || 0,
    ) > 0
  ) {
    warnings.push(
      `候補0件の診断：判定${result.meta.signalEvaluationCount}回、` +
      `15分足不足${diagnostics.insufficientDataCount || 0}回、` +
      `通常の条件待ち${diagnostics.waitSetupCount || 0}回、` +
      `最終リスクゲート拒否${diagnostics.planRejectedCount || 0}回。`,
    );

    const topReasons =
      Object.entries(
        diagnostics.reasonCounts || {},
      )
        .sort(
          (first, second) =>
            second[1] - first[1],
        )
        .slice(0, 3);

    if (topReasons.length) {
      warnings.push(
        "主な見送り理由：" +
        topReasons
          .map(
            ([reason, count]) =>
              `${reason}（${count}回）`,
          )
          .join(" / "),
      );
    }
  }

  warnings.push(
    "資産曲線と売買履歴は、単元制約を外したシグナル性能モードです。",
  );

  if (executableResult) {
    const signalTrades =
      Number(
        result.metrics
          ?.tradeCount || 0,
      );

    const executableTrades =
      Number(
        executableResult.metrics
          ?.tradeCount || 0,
      );

    warnings.push(
      `実行可能性モードは${executableResult.modeConstraints?.lotSize || 1}株単位・最大投資額${executableResult.modeConstraints?.maximumPositionPercent || 20}%です。`,
    );

    if (
      signalTrades > 0 &&
      executableTrades === 0
    ) {
      warnings.push(
        "シグナルは発生していますが、現在の資産・売買単元・投資上限では実行可能な取引がありません。",
      );
    }
  }

  Array.from(
    new Set(warnings),
  ).forEach((warning) => {
    const item =
      document.createElement("p");

    item.textContent = warning;
    elements.warnings.append(item);
  });
}

export function renderIntradayBacktest(
  result,
  executableResult = null,
  modeComparison = {},
) {
  const metrics =
    result.metrics || {};

  const comparison =
    result.comparison || {};

  const diagnostics =
    result.diagnostics || {};

  const featurePassCounts =
    diagnostics.featurePassCounts || {};

  const executableMetrics =
    executableResult
      ?.metrics || {};

  const totalReturnState =
    valueState(
      metrics.totalReturnPercent,
    );

  setStatus(
    "検証完了",
    Number(metrics.tradeCount) > 0
      ? "passed"
      : "neutral",
  );

  elements.description.textContent =
    `確定済み15分足${result.meta.closedBarCount}本を時系列順に検証しました。` +
    ` シグナル性能モード${metrics.tradeCount}回、` +
    `実行可能性モード${executableMetrics.tradeCount || 0}回。` +
    " 資産曲線と売買履歴はシグナル性能モードです。";

  const profitFactor =
    metrics.profitFactorState ===
      "no_losses"
      ? "損失取引なし"
      : finite(
          metrics.profitFactor,
        )
        ? formatNumber(
            metrics.profitFactor,
            2,
          )
        : "--";

  elements.summary.replaceChildren(
    createMetric(
      "詳細表示",
      "シグナル性能",
    ),

    createMetric(
      "シグナル取引",
      formatNumber(
        metrics.tradeCount,
        0,
      ),
    ),

    createMetric(
      "シグナル総リターン",
      formatPercent(
        metrics.totalReturnPercent,
        true,
      ),
      valueState(
        metrics.totalReturnPercent,
      ),
    ),

    createMetric(
      "実行可能取引",
      formatNumber(
        executableMetrics.tradeCount || 0,
        0,
      ),
    ),

    createMetric(
      "実行可能総リターン",
      formatPercent(
        executableMetrics.totalReturnPercent,
        true,
      ),
      valueState(
        executableMetrics.totalReturnPercent,
      ),
    ),

    createMetric(
      "取引数の差",
      formatNumber(
        modeComparison.tradeCountDifference || 0,
        0,
      ),
    ),

    createMetric(
      "シグナル候補",
      formatNumber(
        modeComparison.signalCandidateCount || 0,
        0,
      ),
    ),

    createMetric(
      "実行可能候補",
      formatNumber(
        modeComparison.executableCandidateCount || 0,
        0,
      ),
    ),

    createMetric(
      "開始資産",
      formatCurrency(
        result.account
          .initialEquity,
      ),
    ),

    createMetric(
      "終了資産",
      formatCurrency(
        result.account
          .endingEquity,
      ),
      totalReturnState,
    ),

    createMetric(
      "総リターン",
      formatPercent(
        metrics.totalReturnPercent,
        true,
      ),
      totalReturnState,
    ),

    createMetric(
      "純損益",
      formatCurrency(
        metrics.totalNetPnl,
        true,
      ),
      valueState(
        metrics.totalNetPnl,
      ),
    ),

    createMetric(
      "取引回数",
      formatNumber(
        metrics.tradeCount,
        0,
      ),
    ),

    createMetric(
      "勝率",
      formatPercent(
        metrics.winRate,
      ),
    ),

    createMetric(
      "Profit Factor",
      profitFactor,
    ),

    createMetric(
      "最大ドローダウン",
      formatPercent(
        metrics.maximumDrawdownPercent,
      ),
      valueState(
        metrics.maximumDrawdownPercent,
      ),
    ),

    createMetric(
      "平均保有15分足",
      finite(
        metrics.averageHoldingBars,
      )
        ? `${formatNumber(
            metrics.averageHoldingBars,
            1,
          )}本`
        : "--",
    ),

    createMetric(
      "市場エクスポージャー",
      formatPercent(
        metrics.exposureRate,
      ),
    ),

    createMetric(
      "同期間買い持ち",
      formatPercent(
        comparison
          .buyAndHoldReturnPercent,
        true,
      ),
      valueState(
        comparison
          .buyAndHoldReturnPercent,
      ),
    ),

    createMetric(
      "買い持ちとの差",
      formatPercent(
        comparison
          .excessVsBuyAndHold,
        true,
      ),
      valueState(
        comparison
          .excessVsBuyAndHold,
      ),
    ),

    createMetric(
      "概算売買コスト",
      formatCurrency(
        result.estimatedCosts
          .total,
      ),
    ),

    createMetric(
      "候補シグナル",
      formatNumber(
        result.meta
          .candidateCount,
        0,
      ),
    ),

    createMetric(
      "判定回数",
      formatNumber(
        result.meta
          .signalEvaluationCount,
        0,
      ),
    ),

    createMetric(
      "VWAP上 / 下",
      `${formatNumber(
        featurePassCounts.aboveVwap || 0,
        0,
      )} / ${formatNumber(
        featurePassCounts.belowVwap || 0,
        0,
      )}`,
    ),

    createMetric(
      "出来高急増",
      formatNumber(
        featurePassCounts.volumeSurge || 0,
        0,
      ),
    ),

    createMetric(
      "高値 / 安値ブレイク",
      `${formatNumber(
        featurePassCounts.breakoutLong || 0,
        0,
      )} / ${formatNumber(
        featurePassCounts.breakoutShort || 0,
        0,
      )}`,
    ),

    createMetric(
      "押し目 / 戻り売り",
      `${formatNumber(
        featurePassCounts.pullbackLong || 0,
        0,
      )} / ${formatNumber(
        featurePassCounts.pullbackShort || 0,
        0,
      )}`,
    ),

    createMetric(
      "最大出来高倍率",
      finite(
        diagnostics.maximumVolumeRatio,
      )
        ? `${formatNumber(
            diagnostics.maximumVolumeRatio,
            2,
          )}倍`
        : "--",
    ),

    createMetric(
      "最大セットアップ強度",
      finite(
        diagnostics.maximumSetupStrength,
      )
        ? `${formatNumber(
            diagnostics.maximumSetupStrength,
            0,
          )} / 100`
        : "--",
    ),

    createMetric(
      "最終ゲート拒否",
      formatNumber(
        diagnostics.planRejectedCount || 0,
        0,
      ),
    ),

    createMetric(
      "15分足不足判定",
      formatNumber(
        diagnostics.insufficientDataCount || 0,
        0,
      ),
    ),

    createMetric(
      "見送り候補",
      formatNumber(
        result.meta
          .skippedCandidateCount,
        0,
      ),
    ),

    createMetric(
      "実注文",
      "無効",
    ),
  );

  renderEquityCurve(result);
  renderTrades(result);
  renderWarnings(
    result,
    executableResult,
  );
}

function renderError(message) {
  setStatus(
    "検証失敗",
    "failed",
  );

  elements.description.textContent =
    message;

  elements.summary.replaceChildren(
    createMetric(
      "状態",
      "検証失敗",
      "negative",
    ),
  );

  elements.chart.replaceChildren();

  const chartError =
    document.createElement("p");

  chartError.className =
    "emptyState";

  chartError.textContent =
    "資産曲線を表示できません。";

  elements.chart.append(chartError);

  elements.trades.replaceChildren();

  const tradeError =
    document.createElement("p");

  tradeError.className =
    "emptyState";

  tradeError.textContent =
    message;

  elements.trades.append(tradeError);

  elements.warnings.replaceChildren();
}

function paperEquity() {
  const input =
    document.getElementById(
      "paperEquity",
    );

  const value =
    Number(input?.value);

  return finite(value) &&
    value > 0
      ? value
      : 1_000_000;
}

function setLoading(loading) {
  elements.runButton.disabled =
    loading;

  elements.runButton.textContent =
    loading
      ? "短期バックテスト中"
      : "短期バックテストを実行";

  if (loading) {
    setStatus("検証中");
  }
}

export async function runIntradayBacktestUi() {
  const state =
    stateProvider?.();

  const symbol =
    state?.symbol;

  if (!symbol) {
    renderError(
      "先に通常分析を実行してください。",
    );

    return null;
  }

  backtestController?.abort();

  backtestController =
    new AbortController();

  setLoading(true);

  try {
    const history =
      await fetchIntradayHistory(
        symbol,
        {
          range: "1mo",
          interval: "15m",
          signal:
            backtestController.signal,
        },
      );

    const modes =
      runIntradayBacktestModes({
        symbol,

        intradayHistory:
          history,

        initialEquity:
          paperEquity(),

        executableLotSize:
          symbol.endsWith(".T")
            ? 100
            : 1,

        signalLotSize:
          1,

        signalMaximumPositionPercent:
          100,

        executableMaximumPositionPercent:
          20,

        commonPolicy: {
          commissionPercentPerSide:
            0.05,

          spreadPercent:
            0.1,

          slippagePercentPerSide:
            0.05,

          closeAtSessionEnd:
            true,

          allowOvernightEntry:
            false,
        },
      });

    renderIntradayBacktest(
      modes.signal,
      modes.executable,
      modes.comparison,
    );

    return modes;
  } catch (error) {
    if (
      error.name !==
      "AbortError"
    ) {
      console.error(
        "Intraday backtest:",
        error,
      );

      renderError(
        error.message ||
          "短期バックテストに失敗しました。",
      );
    }

    return null;
  } finally {
    setLoading(false);
  }
}

export function initIntradayPaperBacktest(
  getState,
) {
  stateProvider = getState;

  elements.status =
    document.getElementById(
      "intradayBacktestStatus",
    );

  elements.description =
    document.getElementById(
      "intradayBacktestDescription",
    );

  elements.summary =
    document.getElementById(
      "intradayBacktestSummary",
    );

  elements.chart =
    document.getElementById(
      "intradayBacktestChart",
    );

  elements.trades =
    document.getElementById(
      "intradayBacktestTrades",
    );

  elements.warnings =
    document.getElementById(
      "intradayBacktestWarnings",
    );

  elements.runButton =
    document.getElementById(
      "runIntradayBacktestButton",
    );

  elements.runButton.addEventListener(
    "click",
    () => {
      void runIntradayBacktestUi();
    },
  );
}