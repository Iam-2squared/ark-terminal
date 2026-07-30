import { groupPerformance, summarizePerformance } from "./backtest/engine.js";

import { exportPredictions, getPredictions } from "./backtest/storage.js";

import {
  loadWeights,
  optimizeWeights,
  resetWeights,
} from "./analysis/weights.js";

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

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function finite(value) {
  return Number.isFinite(Number(value));
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

function renderMetrics(records) {
  const metrics = summarizePerformance(records);

  const mapping = {
    metricSamples: metrics.sampleCount,
    metricWinRate: percent(metrics.winRate),
    metricAverageReturn: percent(metrics.averageReturn),
    metricAverageProfit: percent(metrics.averageProfit),
    metricAverageLoss: percent(metrics.averageLoss),
    metricWinStreak: metrics.maximumWins,
    metricLossStreak: metrics.maximumLosses,
    metricSharpe: number(metrics.sharpe, 2),
  };

  Object.entries(mapping).forEach(([id, value]) => {
    document.getElementById(id).textContent = value;
  });
}

function renderGroupTable(elementId, groups) {
  const host = document.getElementById(elementId);

  if (!groups.length) {
    host.innerHTML = `
            <p class="emptyState">
                確定済みデータがありません。
            </p>
        `;
    return;
  }

  host.innerHTML = `
        <table class="performanceTable">
            <thead>
                <tr>
                    <th>分類</th>
                    <th>件数</th>
                    <th>勝率</th>
                    <th>平均騰落率</th>
                </tr>
            </thead>
            <tbody>
                ${groups
                  .map(
                    (group) => `
                        <tr>
                            <td>${escapeHtml(group.key)}</td>
                            <td>${group.sampleCount}</td>
                            <td>${percent(group.winRate)}</td>
                            <td class="${
                              Number(group.averageReturn) >= 0
                                ? "positive"
                                : "negative"
                            }">
                                ${percent(group.averageReturn)}
                            </td>
                        </tr>
                    `,
                  )
                  .join("")}
            </tbody>
        </table>
    `;
}

function scoreBucket(record) {
  const score = Number(record.score);

  if (score >= 75) {
    return "75–100";
  }

  if (score >= 60) {
    return "60–74";
  }

  if (score >= 45) {
    return "45–59";
  }

  if (score >= 30) {
    return "30–44";
  }

  return "0–29";
}

function recordMonth(record) {
  const date = new Date(record.resolvedAt || record.createdAt);

  return Number.isNaN(date.getTime())
    ? "不明"
    : `${date.getFullYear()}-` + String(date.getMonth() + 1).padStart(2, "0");
}

function renderPredictionLog(records) {
  const host = document.getElementById("predictionLog");

  if (!records.length) {
    host.innerHTML = `
            <p class="emptyState">
                Prediction Labで分析またはバックテストを実行すると記録されます。
            </p>
        `;
    return;
  }

  const rows = [...records]
    .sort(
      (first, second) => new Date(second.createdAt) - new Date(first.createdAt),
    )
    .slice(0, 100);

  host.innerHTML = `
        <table class="performanceTable wideTable">
            <thead>
                <tr>
                    <th>日時</th>
                    <th>銘柄</th>
                    <th>期間</th>
                    <th>スコア</th>
                    <th>分析時価格</th>
                    <th>実際価格</th>
                    <th>騰落率</th>
                    <th>結果</th>
                </tr>
            </thead>
            <tbody>
                ${rows
                  .map((record) => {
                    const date = new Date(record.createdAt);

                    return `
                            <tr>
                                <td>${escapeHtml(date.toLocaleString("ja-JP"))}</td>
                                <td>${escapeHtml(record.companyName || record.symbol)}<br><small>${escapeHtml(record.symbol)}</small></td>
                                <td>${record.period}日</td>
                                <td>${number(record.score, 0)}</td>
                                <td>${number(record.predictionPrice, 2)}</td>
                                <td>${number(record.actualPrice, 2)}</td>
                                <td class="${
                                  Number(record.actualReturn) >= 0
                                    ? "positive"
                                    : "negative"
                                }">${percent(record.actualReturn)}</td>
                                <td>${escapeHtml(record.outcome)}</td>
                            </tr>
                        `;
                  })
                  .join("")}
            </tbody>
        </table>
    `;
}

function renderWeights(weights) {
  document.getElementById("weightList").innerHTML = Object.entries(weights)
    .map(
      ([key, value]) => `
                <div class="weightItem">
                    <span>${escapeHtml(factorLabels[key] || key)}</span>
                    <strong>${number(value, 2)}%</strong>
                </div>
            `,
    )
    .join("");
}

function render() {
  const records = getPredictions();

  const resolvedCount = records.filter(
    (record) => record.status === "resolved",
  ).length;

  const pendingCount = records.length - resolvedCount;

  document.getElementById("performanceNotice").textContent =
    `全${records.length}件・確定${resolvedCount}件・判定待ち${pendingCount}件。データはこのブラウザ内に保存されています。`;

  renderMetrics(records);
  renderWeights(loadWeights());

  renderGroupTable(
    "symbolPerformance",
    groupPerformance(records, (record) => record.symbol || "不明"),
  );

  renderGroupTable(
    "industryPerformance",
    groupPerformance(records, (record) => record.industry || "未分類"),
  );

  renderGroupTable("scorePerformance", groupPerformance(records, scoreBucket));

  renderGroupTable(
    "periodPerformance",
    groupPerformance(records, (record) => `${record.period}営業日`),
  );

  renderGroupTable(
    "monthlyPerformance",
    groupPerformance(records, recordMonth),
  );

  renderPredictionLog(records);
}

document
  .getElementById("optimizeWeightsButton")
  .addEventListener("click", () => {
    const result = optimizeWeights(getPredictions());

    document.getElementById("optimizerStatus").textContent = result.message;

    renderWeights(result.weights);
  });

document.getElementById("resetWeightsButton").addEventListener("click", () => {
  const weights = resetWeights();

  document.getElementById("optimizerStatus").textContent =
    "重みを初期値へ戻しました。";

  renderWeights(weights);
});

document.getElementById("exportRecordsButton").addEventListener("click", () => {
  const blob = new Blob([exportPredictions()], {
    type: "application/json",
  });

  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");

  link.href = url;
  link.download = "ark-prediction-records.json";

  link.click();

  URL.revokeObjectURL(url);
});

render();
