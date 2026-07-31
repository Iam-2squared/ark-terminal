import { groupPerformance, summarizePerformance } from "./backtest/engine.js";
import {
  exportPredictionsAsync,
  getPredictionsAsync,
} from "./backtest/storage.js";
import {
  loadWeights,
  recommendWeights,
  resetWeights,
  saveWeights,
} from "./analysis/weights.js";
import {
  buildPerformanceAnalytics,
  indicatorAccuracy,
  recordMonth,
} from "./learning/analytics.js";
import { exportMachineLearningDataset } from "./learning/dataset.js";
import {
  filterPredictionHistory,
  paginatePredictionHistory,
  predictionSymbols,
} from "./performance-history.js";

const factorLabels = {
  movingAverages: "移動平均線",
  rsi: "RSI",
  macd: "MACD",
  bollingerBands: "ボリンジャーバンド",
  volume: "出来高",
  adx: "ADX",
  atr: "ATR",
  stochastic: "ストキャスティクス",
  vwap: "VWAP",
  high52Week: "52週高値",
  low52Week: "52週安値",
  news: "ニュース",
  disclosure: "適時開示",
  sentiment: "投資家心理",
};

const state = {
  records: [],
  analytics: null,
  recommendation: null,
  historyPage: 1,
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function number(value, digits = 1) {
  return finite(value)
    ? Number(value).toLocaleString("ja-JP", {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      })
    : "--";
}

function percent(value) {
  return finite(value) ? `${number(value, 1)}%` : "--";
}

function signedPercent(value) {
  if (!finite(value)) return "--";

  return `${Number(value) >= 0 ? "+" : ""}${number(value, 1)}%`;
}

function returnClass(value) {
  if (!finite(value)) return "";

  return Number(value) >= 0 ? "positive" : "negative";
}

function downloadText(filename, text) {
  const blob = new Blob([text], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function renderMetrics(records, forecast) {
  const metrics = summarizePerformance(records);
  const interval = metrics.winRateConfidenceInterval;
  const mapping = {
    metricSamples: metrics.sampleCount,
    metricWinRate: percent(metrics.winRate),
    metricAverageReturn: percent(metrics.averageReturn),
    metricMedianReturn: percent(metrics.medianReturn),
    metricMaximumDrawdown: percent(metrics.maximumDrawdown),
    metricProfitFactor:
      metrics.profitFactor === Infinity ? "∞" : number(metrics.profitFactor, 2),
    metricProfitLoss: `${percent(metrics.averageProfit)} / ${percent(
      metrics.averageLoss,
    )}`,
    metricTradingCost: percent(metrics.totalTradingCost),
    metricStreaks: `${metrics.maximumWins} / ${metrics.maximumLosses}`,
    metricSharpe: number(metrics.sharpe, 2),
    metricMae: percent(forecast.mae),
    metricRmse: percent(forecast.rmse),
  };

  Object.entries(mapping).forEach(([id, value]) => {
    document.getElementById(id).textContent = value;
  });

  document.getElementById("metricWinRateInterval").textContent =
    finite(interval?.lower) && finite(interval?.upper)
      ? `${number(interval.lower, 1)}～${number(interval.upper, 1)}%`
      : "--";
  document.getElementById("metricForecastSamples").textContent =
    forecast.sampleCount
      ? `${forecast.sampleCount}件の期待値を検証`
      : "期待値データを蓄積中";
  document.getElementById("metricForecastBias").textContent =
    finite(forecast.bias)
      ? `誤差バイアス ${signedPercent(forecast.bias)}`
      : "--";
}

function renderGroupTable(elementId, groups, { limit = 50 } = {}) {
  const host = document.getElementById(elementId);

  if (!groups.length) {
    host.innerHTML = '<p class="emptyState">確定済みデータがありません。</p>';
    return;
  }

  host.innerHTML = `
    <table class="performanceTable">
      <thead>
        <tr>
          <th>分類</th>
          <th>件数</th>
          <th>勝率</th>
          <th>費用後平均</th>
          <th>中央値</th>
          <th>PF</th>
        </tr>
      </thead>
      <tbody>
        ${groups
          .slice(0, limit)
          .map(
            (group) => `
              <tr>
                <td>${escapeHtml(group.key)}</td>
                <td>${group.sampleCount}</td>
                <td>${percent(group.winRate)}</td>
                <td class="${returnClass(group.averageReturn)}">
                  ${percent(group.averageReturn)}
                </td>
                <td>${percent(group.medianReturn)}</td>
                <td>${
                  group.profitFactor === Infinity
                    ? "∞"
                    : number(group.profitFactor, 2)
                }</td>
              </tr>
            `,
          )
          .join("")}
      </tbody>
    </table>
  `;
}

function renderImprovementInsights(analytics) {
  const host = document.getElementById("improvementInsights");
  const badge = document.getElementById("improvementDataBadge");

  badge.textContent = `${analytics.all.length}件で分析`;
  badge.className = `dataSourceBadge ${
    analytics.all.length >= 30 ? "available" : "partial"
  }`;
  host.innerHTML = analytics.insights
    .map(
      (insight) => `
        <article class="improvementItem ${escapeHtml(insight.level)}">
          <strong>${escapeHtml(insight.title)}</strong>
          <span>${escapeHtml(insight.detail)}</span>
        </article>
      `,
    )
    .join("");
}

function comparisonItem(label, allValue, recentValue, formatter = percent) {
  const delta =
    finite(allValue) && finite(recentValue)
      ? Number(recentValue) - Number(allValue)
      : null;

  return `
    <div class="comparisonItem">
      <span>${escapeHtml(label)}</span>
      <strong>${formatter(recentValue)}</strong>
      <small>全期間 ${formatter(allValue)}</small>
      <em class="${returnClass(delta)}">
        ${finite(delta) ? `差 ${signedPercent(delta)}` : "比較データなし"}
      </em>
    </div>
  `;
}

function renderRecentComparison(analytics) {
  const { all, recent, forecastAll, forecastRecent } = analytics.comparison;

  document.getElementById("recentComparison").innerHTML = [
    comparisonItem("勝率", all.winRate, recent.winRate),
    comparisonItem("平均リターン", all.averageReturn, recent.averageReturn),
    comparisonItem("最大ドローダウン", all.maximumDrawdown, recent.maximumDrawdown),
    comparisonItem("期待変動幅MAE", forecastAll.mae, forecastRecent.mae),
  ].join("");
}

function renderIndicatorTable(items) {
  const host = document.getElementById("indicatorPerformance");

  if (!items.length) {
    host.innerHTML =
      '<p class="emptyState">条件付き特徴量を含む検証データを蓄積中です。</p>';
    return;
  }

  host.innerHTML = `
    <table class="performanceTable wideTable">
      <thead>
        <tr>
          <th>#</th>
          <th>条件</th>
          <th>発生回数</th>
          <th>勝率</th>
          <th>平均リターン</th>
          <th>平均利益</th>
          <th>平均損失</th>
          <th>最大利益</th>
          <th>最大損失</th>
        </tr>
      </thead>
      <tbody>
        ${items
          .map(
            (item, index) => `
              <tr>
                <td>${index + 1}</td>
                <td>${escapeHtml(item.label)}</td>
                <td>${item.sampleCount}</td>
                <td>${percent(item.winRate)}</td>
                <td class="${returnClass(item.averageReturn)}">${percent(
                  item.averageReturn,
                )}</td>
                <td class="positive">${percent(item.averageProfit)}</td>
                <td class="negative">${percent(item.averageLoss)}</td>
                <td class="positive">${percent(item.maximumProfit)}</td>
                <td class="negative">${percent(item.maximumLoss)}</td>
              </tr>
            `,
          )
          .join("")}
      </tbody>
    </table>
  `;
}

function renderCombinationTable(items) {
  const host = document.getElementById("combinationPerformance");

  if (!items.length) {
    host.innerHTML =
      '<p class="emptyState">同じ条件の組み合わせが3件以上になると表示します。</p>';
    return;
  }

  host.innerHTML = `
    <table class="performanceTable wideTable">
      <thead>
        <tr>
          <th>#</th>
          <th>条件の組み合わせ</th>
          <th>件数</th>
          <th>勝率</th>
          <th>平均リターン</th>
          <th>平均利益</th>
          <th>平均損失</th>
        </tr>
      </thead>
      <tbody>
        ${items
          .map(
            (item, index) => `
              <tr>
                <td>${index + 1}</td>
                <td class="wrapCell">${escapeHtml(item.label)}</td>
                <td>${item.sampleCount}</td>
                <td>${percent(item.winRate)}</td>
                <td class="${returnClass(item.averageReturn)}">${percent(
                  item.averageReturn,
                )}</td>
                <td class="positive">${percent(item.averageProfit)}</td>
                <td class="negative">${percent(item.averageLoss)}</td>
              </tr>
            `,
          )
          .join("")}
      </tbody>
    </table>
  `;
}

function best(items, order = "high") {
  const available = items.filter((item) => item.sampleCount >= 3);

  return [...available].sort((first, second) =>
    order === "high"
      ? (second.winRate || 0) - (first.winRate || 0)
      : (first.winRate || 0) - (second.winRate || 0),
  )[0];
}

function reasonCard(title, item, fallback) {
  return `
    <article class="reasonAnalysisItem">
      <span>${escapeHtml(title)}</span>
      ${
        item
          ? `<strong>${escapeHtml(item.label)}</strong>
             <small>${item.sampleCount}件・勝率${percent(item.winRate)}・平均${percent(
               item.averageReturn,
             )}</small>`
          : `<strong>データ蓄積中</strong><small>${escapeHtml(fallback)}</small>`
      }
    </article>
  `;
}

function renderReasonAnalysis(analytics) {
  const currentMonth = new Date().toISOString().slice(0, 7);
  const monthlyIndicators = indicatorAccuracy(
    analytics.all.filter((record) => recordMonth(record) === currentMonth),
  );
  const recentByKey = new Map(
    analytics.recentIndicators.map((item) => [item.key, item]),
  );
  const declining = analytics.indicators
    .map((item) => ({
      ...item,
      delta: finite(recentByKey.get(item.key)?.winRate)
        ? recentByKey.get(item.key).winRate - item.winRate
        : null,
    }))
    .filter((item) => finite(item.delta) && item.sampleCount >= 5)
    .sort((first, second) => first.delta - second.delta)[0];
  const reliable = [...analytics.indicators]
    .filter((item) => item.sampleCount >= 5)
    .sort(
      (first, second) =>
        second.sampleCount * (second.winRate || 0) -
        first.sampleCount * (first.winRate || 0),
    )[0];

  document.getElementById("reasonPerformance").innerHTML = [
    reasonCard("今月最も当たった予測理由", best(monthlyIndicators), "今月3件以上で表示"),
    reasonCard(
      "今月最も外れた予測理由",
      best(monthlyIndicators, "low"),
      "今月3件以上で表示",
    ),
    reasonCard(
      "全期間で最も信頼できる条件",
      reliable,
      "全期間5件以上で表示",
    ),
    declining
      ? `
        <article class="reasonAnalysisItem">
          <span>最近精度が落ちている条件</span>
          <strong>${escapeHtml(declining.label)}</strong>
          <small>全期間比 ${signedPercent(declining.delta)}</small>
        </article>
      `
      : reasonCard(
          "最近精度が落ちている条件",
          null,
          "直近30日と全期間を比較中",
        ),
  ].join("");
}

function renderIndustryIndicators(items) {
  const host = document.getElementById("industryIndicatorPerformance");
  const eligible = items.filter((item) => item.sampleCount >= 3).slice(0, 40);

  if (!eligible.length) {
    host.innerHTML =
      '<p class="emptyState">同じ業種・条件が3件以上になると表示します。</p>';
    return;
  }

  host.innerHTML = `
    <table class="performanceTable">
      <thead>
        <tr>
          <th>業種</th>
          <th>有効条件</th>
          <th>件数</th>
          <th>勝率</th>
          <th>平均リターン</th>
        </tr>
      </thead>
      <tbody>
        ${eligible
          .map(
            (item) => `
              <tr>
                <td>${escapeHtml(item.industry)}</td>
                <td>${escapeHtml(item.label)}</td>
                <td>${item.sampleCount}</td>
                <td>${percent(item.winRate)}</td>
                <td class="${returnClass(item.averageReturn)}">${percent(
                  item.averageReturn,
                )}</td>
              </tr>
            `,
          )
          .join("")}
      </tbody>
    </table>
  `;
}

function renderWeights(current, recommendation = null) {
  const recommended = recommendation?.recommended;
  const evidence = recommendation?.evidence || {};

  document.getElementById("weightList").innerHTML = Object.entries(current)
    .map(([key, value]) => {
      const next = recommended?.[key];
      const delta = finite(next) ? Number(next) - Number(value) : null;
      const proof = evidence[key];

      return `
        <div class="weightItem">
          <span>${escapeHtml(factorLabels[key] || key)}</span>
          <div>
            <strong>${number(value, 2)}%</strong>
            ${
              finite(next)
                ? `<em class="${returnClass(delta)}">→ ${number(next, 2)}% (${signedPercent(
                    delta,
                  ).replace("%", "pt")})</em>`
                : ""
            }
            ${
              proof?.sampleCount
                ? `<small>${proof.sampleCount}件・補正精度${percent(
                    proof.reliableAccuracy,
                  )}</small>`
                : "<small>根拠データ待ち</small>"
            }
          </div>
        </div>
      `;
    })
    .join("");
}

function historyFilters() {
  return {
    scope: document.getElementById("historyScope").value,
    result: document.getElementById("historyResult").value,
    symbol: document.getElementById("historySymbol").value,
    dateFrom: document.getElementById("historyDateFrom").value,
    dateTo: document.getElementById("historyDateTo").value,
  };
}

function renderPredictionLog() {
  const details = document.getElementById("predictionHistoryDetails");

  if (!details.open) return;

  const host = document.getElementById("predictionLog");
  const filtered = filterPredictionHistory(state.records, historyFilters());
  const page = paginatePredictionHistory(filtered, state.historyPage, 50);

  state.historyPage = page.page;
  document.getElementById("historyStatus").textContent =
    `${page.total}件中 ${page.start}～${page.end}件を表示。1ページ最大50件です。`;
  document.getElementById("historyPageStatus").textContent =
    `${page.page} / ${page.pageCount}ページ`;
  document.getElementById("historyPreviousButton").disabled = page.page <= 1;
  document.getElementById("historyNextButton").disabled =
    page.page >= page.pageCount;

  if (!page.rows.length) {
    host.innerHTML =
      '<p class="emptyState">指定した条件に一致する履歴がありません。</p>';
    return;
  }

  host.innerHTML = `
    <table class="performanceTable wideTable">
      <thead>
        <tr>
          <th>日時</th>
          <th>銘柄</th>
          <th>期間</th>
          <th>区分</th>
          <th>方向</th>
          <th>スコア</th>
          <th>分析時価格</th>
          <th>予測変動</th>
          <th>実騰落率</th>
          <th>予測誤差</th>
          <th>費用後損益</th>
          <th>結果</th>
        </tr>
      </thead>
      <tbody>
        ${page.rows
          .map((record) => {
            const date = new Date(record.createdAt);
            const forecastError =
              finite(record.expectedReturn) && finite(record.actualReturn)
                ? Number(record.actualReturn) - Number(record.expectedReturn)
                : record.forecastError;

            return `
              <tr>
                <td>${escapeHtml(
                  Number.isNaN(date.getTime())
                    ? "--"
                    : date.toLocaleString("ja-JP"),
                )}</td>
                <td>${escapeHtml(
                  record.companyName || record.symbol,
                )}<br><small>${escapeHtml(record.symbol)}</small></td>
                <td>${number(record.period, 0)}日</td>
                <td>${escapeHtml(
                  record.partition ||
                    (record.source === "live" ? "実運用記録" : "旧形式"),
                )}</td>
                <td>${escapeHtml(record.direction || "--")}</td>
                <td>${number(record.score, 0)}</td>
                <td>${number(record.predictionPrice, 2)}</td>
                <td>${signedPercent(record.expectedReturn)}</td>
                <td class="${returnClass(record.actualReturn)}">${signedPercent(
                  record.actualReturn,
                )}</td>
                <td>${signedPercent(forecastError)}</td>
                <td class="${returnClass(record.strategyReturn)}">${signedPercent(
                  record.strategyReturn,
                )}</td>
                <td>${escapeHtml(record.outcome)}</td>
              </tr>
            `;
          })
          .join("")}
      </tbody>
    </table>
  `;
}

function populateHistorySymbols() {
  const select = document.getElementById("historySymbol");
  const current = select.value;

  select.innerHTML = `
    <option value="">すべて</option>
    ${predictionSymbols(state.records)
      .map(
        (symbol) =>
          `<option value="${escapeHtml(symbol)}">${escapeHtml(symbol)}</option>`,
      )
      .join("")}
  `;
  select.value = current;
}

function render() {
  const records = state.records;
  const testRecords = records.filter(
    (record) => record.status === "resolved" && record.partition === "test",
  );
  const metricRecords = testRecords.length
    ? testRecords
    : records.filter((record) => record.status === "resolved");
  const resolvedCount = records.filter(
    (record) => record.status === "resolved",
  ).length;
  const pendingCount = records.length - resolvedCount;
  const analytics = buildPerformanceAnalytics(records);

  state.analytics = analytics;
  document.getElementById("performanceNotice").textContent = testRecords.length
    ? `全${records.length}件・最終テスト${testRecords.length}件・判定待ち${pendingCount}件。主要指標は最終テスト期間の成績です。`
    : `全${records.length}件・確定${resolvedCount}件・判定待ち${pendingCount}件。最終テストがないため、主要指標は既存確定データの参考値です。`;
  document.getElementById("historyTotalCount").textContent =
    records.length.toLocaleString("ja-JP");

  renderMetrics(metricRecords, analytics.comparison.forecastAll);
  renderImprovementInsights(analytics);
  renderRecentComparison(analytics);
  renderWeights(loadWeights(), state.recommendation);
  renderIndicatorTable(analytics.indicators);
  renderCombinationTable(analytics.combinations);
  renderReasonAnalysis(analytics);
  renderIndustryIndicators(analytics.industryIndicators);

  renderGroupTable(
    "partitionPerformance",
    groupPerformance(
      records.filter((record) => record.source === "walk-forward"),
      (record) =>
        ({
          training: "学習",
          validation: "検証",
          test: "最終テスト",
        })[record.partition] || "旧形式",
    ),
  );
  renderGroupTable("directionPerformance", analytics.dimensions.direction);
  renderGroupTable("regimePerformance", analytics.dimensions.regime);
  renderGroupTable("marketPerformance", analytics.dimensions.market);
  renderGroupTable("industryPerformance", analytics.dimensions.industry);
  renderGroupTable("pricePerformance", analytics.dimensions.price);
  renderGroupTable("scorePerformance", analytics.dimensions.score);
  renderGroupTable("confidencePerformance", analytics.dimensions.confidence);
  renderGroupTable("riskPerformance", analytics.dimensions.risk);
  renderGroupTable("monthlyPerformance", analytics.dimensions.month);
  renderGroupTable("symbolPerformance", analytics.dimensions.symbol);
  renderGroupTable("periodPerformance", analytics.dimensions.period);
  populateHistorySymbols();
  renderPredictionLog();
}

function bindHistoryControls() {
  const controls = [
    "historyScope",
    "historyResult",
    "historySymbol",
    "historyDateFrom",
    "historyDateTo",
  ];

  document
    .getElementById("predictionHistoryDetails")
    .addEventListener("toggle", renderPredictionLog);

  controls.forEach((id) => {
    document.getElementById(id).addEventListener("change", () => {
      state.historyPage = 1;
      renderPredictionLog();
    });
  });

  document.getElementById("historyResetButton").addEventListener("click", () => {
    document.getElementById("historyScope").value = "recent30";
    document.getElementById("historyResult").value = "all";
    document.getElementById("historySymbol").value = "";
    document.getElementById("historyDateFrom").value = "";
    document.getElementById("historyDateTo").value = "";
    state.historyPage = 1;
    renderPredictionLog();
  });

  document
    .getElementById("historyPreviousButton")
    .addEventListener("click", () => {
      state.historyPage -= 1;
      renderPredictionLog();
    });

  document
    .getElementById("historyNextButton")
    .addEventListener("click", () => {
      state.historyPage += 1;
      renderPredictionLog();
    });
}

function bindActions() {
  document
    .getElementById("recommendWeightsButton")
    .addEventListener("click", () => {
      state.recommendation = recommendWeights(state.records, loadWeights());
      document.getElementById("optimizerStatus").textContent =
        state.recommendation.message;
      document.getElementById("weightRecommendationBadge").textContent =
        state.recommendation.ready ? "推奨値あり" : "データ不足";
      document.getElementById("applyWeightsButton").disabled =
        !state.recommendation.ready;
      renderWeights(loadWeights(), state.recommendation);
    });

  document.getElementById("applyWeightsButton").addEventListener("click", () => {
    if (!state.recommendation?.ready) return;

    const weights = saveWeights(state.recommendation.recommended);

    document.getElementById("optimizerStatus").textContent =
      "確認済みの推奨重みをPrediction Scoreへ反映しました。";
    document.getElementById("weightRecommendationBadge").textContent =
      "採用済み";
    document.getElementById("applyWeightsButton").disabled = true;
    state.recommendation = null;
    renderWeights(weights);
  });

  document.getElementById("resetWeightsButton").addEventListener("click", () => {
    state.recommendation = null;
    const weights = resetWeights();

    document.getElementById("optimizerStatus").textContent =
      "重みを初期値へ戻しました。";
    document.getElementById("weightRecommendationBadge").textContent =
      "初期値";
    document.getElementById("applyWeightsButton").disabled = true;
    renderWeights(weights);
  });

  document
    .getElementById("exportRecordsButton")
    .addEventListener("click", async () => {
      downloadText(
        "ark-prediction-records.json",
        await exportPredictionsAsync(),
      );
    });

  document
    .getElementById("exportDatasetButton")
    .addEventListener("click", () => {
      downloadText(
        "ark-ml-dataset.json",
        exportMachineLearningDataset(state.records),
      );
    });
}

async function init() {
  bindHistoryControls();
  bindActions();
  state.records = await getPredictionsAsync();

  const scheduleRender = globalThis.requestIdleCallback || globalThis.setTimeout;

  scheduleRender(render);
}

init();
