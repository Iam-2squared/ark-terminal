import { loadWeights } from "./analysis/weights.js";
import { runWalkForwardBacktest } from "./backtest/engine.js";
import {
  getPredictions,
  setPredictions,
} from "./backtest/storage.js";
import { fetchAnalysisBundle } from "./data.js";
import {
  mergeGlobalEvaluationRecords,
  parseGlobalEvaluationSymbols,
  runGlobalEvaluation,
} from "./global-evaluation.js";

const elements = {};
const resultRows = new Map();

let evaluationController = null;

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function formatNumber(value, digits = 1) {
  return finite(value)
    ? Number(value).toLocaleString("ja-JP", {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      })
    : "--";
}

function formatPercent(value) {
  return finite(value) ? `${formatNumber(value, 1)}%` : "--";
}

function formatSignedPercent(value) {
  if (!finite(value)) {
    return "--";
  }

  return `${Number(value) >= 0 ? "+" : ""}${formatNumber(value, 1)}%`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function setStatus(label, state = "") {
  elements.globalEvaluationStatus.textContent = label;
  elements.globalEvaluationStatus.className =
    `dataSourceBadge ${state}`.trim();
}

function setRunning(running) {
  elements.runGlobalEvaluationButton.disabled = running;
  elements.stopGlobalEvaluationButton.disabled = !running;
  elements.globalEvaluationSymbols.disabled = running;
  elements.globalEvaluationPeriod.disabled = running;
}

function setMetric(id, value) {
  elements[id].textContent = value;
}

function modelLabel(item) {
  if (item.selectedModel === "continuous") {
    return item.selectedCandidateId
      ? `連続値モデル「${item.selectedCandidateId}」`
      : "連続値モデル";
  }

  if (item.selectedModel === "rule") {
    return "現行ルールモデル";
  }

  return "モデル不明";
}

function renderResultRows() {
  if (!resultRows.size) {
    elements.globalEvaluationResults.innerHTML =
      '<p class="emptyState">実行後に銘柄ごとの結果を表示します。</p>';
    return;
  }

  elements.globalEvaluationResults.innerHTML = Array.from(
    resultRows.values(),
  )
    .map((item) => {
      const failed = item.status === "failed";
      const detail = failed
        ? item.error || "評価に失敗しました。"
        : `最終テスト${item.testSampleCount}件・${modelLabel(item)}`;

      return `
        <article class="globalEvaluationResult ${failed ? "failed" : "completed"}">
          <div>
            <strong>${escapeHtml(item.symbol)}</strong>
            <small>${escapeHtml(detail)}</small>
          </div>
          <span>${failed ? "失敗" : "完了"}</span>
        </article>
      `;
    })
    .join("");
}

function updateProgress(progress) {
  const total = Math.max(1, Number(progress.total) || 1);
  const completed = Math.min(
    total,
    Math.max(0, Number(progress.completed) || 0),
  );

  elements.globalEvaluationProgress.value =
    (completed / total) * 100;

  if (progress.result) {
    resultRows.set(progress.result.symbol, progress.result);
    renderResultRows();
  }

  if (progress.status === "loading") {
    elements.globalEvaluationProgressText.textContent =
      `${completed} / ${total}銘柄完了。` +
      `${progress.symbol}を取得・検証しています。`;
    return;
  }

  elements.globalEvaluationProgressText.textContent =
    `${completed} / ${total}銘柄完了。` +
    `${progress.symbol}は${progress.status === "failed" ? "失敗" : "完了"}しました。`;
}

function renderWarnings(result) {
  const warnings = [...result.summary.warnings];

  if (result.parsed.duplicates.length) {
    warnings.push(
      `重複銘柄を除外しました: ${result.parsed.duplicates.join(", ")}`,
    );
  }

  if (result.parsed.invalid.length) {
    warnings.push(
      `無効な入力を除外しました: ${result.parsed.invalid.join(", ")}`,
    );
  }

  if (result.parsed.omitted.length) {
    warnings.push(
      `上限超過のため除外しました: ${result.parsed.omitted.join(", ")}`,
    );
  }

  warnings.push(
    "各テストは期間が重なる場合があるため、資産曲線や複利運用の実績ではありません。",
  );

  elements.globalEvaluationWarnings.hidden = !warnings.length;
  elements.globalEvaluationWarnings.innerHTML = warnings
    .map((warning) => `<p>${escapeHtml(warning)}</p>`)
    .join("");
}

function renderSummary(result) {
  const summary = result.summary;

  elements.globalEvaluationSummary.hidden = false;

  setMetric(
    "globalMetricSymbols",
    summary.symbolCount.toLocaleString("ja-JP"),
  );
  setMetric(
    "globalMetricSamples",
    summary.sampleCount.toLocaleString("ja-JP"),
  );
  setMetric(
    "globalMetricWinRate",
    formatPercent(summary.winRate),
  );
  setMetric(
    "globalMetricCoverage",
    formatPercent(summary.coverageRate),
  );
  setMetric(
    "globalMetricStrategyReturn",
    formatSignedPercent(summary.strategy.averageReturn),
  );
  setMetric(
    "globalMetricBenchmarkReturn",
    formatSignedPercent(summary.benchmark.averageReturn),
  );
  setMetric(
    "globalMetricExcessReturn",
    formatSignedPercent(summary.averageExcessReturn),
  );
  setMetric(
    "globalMetricDrawdown",
    formatPercent(summary.strategy.maximumDrawdown),
  );

  renderWarnings(result);
}

async function startGlobalEvaluation() {
  const parsed = parseGlobalEvaluationSymbols(
    elements.globalEvaluationSymbols.value,
  );

  if (!parsed.symbols.length) {
    setStatus("入力エラー", "failed");
    elements.globalEvaluationProgressText.textContent =
      "有効な銘柄コードを1件以上入力してください。";
    return;
  }

  evaluationController?.abort();
  evaluationController = new AbortController();

  resultRows.clear();
  renderResultRows();

  elements.globalEvaluationSummary.hidden = true;
  elements.globalEvaluationWarnings.hidden = true;
  elements.globalEvaluationProgress.value = 0;
  elements.globalEvaluationProgressText.textContent =
    `0 / ${parsed.symbols.length}銘柄完了。準備しています。`;

  setRunning(true);
  setStatus("実行中");

  try {
    const result = await runGlobalEvaluation({
      symbols: elements.globalEvaluationSymbols.value,
      period: Number(elements.globalEvaluationPeriod.value),
      weights: loadWeights(),
      fetchBundle: fetchAnalysisBundle,
      runBacktest: runWalkForwardBacktest,
      signal: evaluationController.signal,
      onProgress: updateProgress,
    });

    const merged = mergeGlobalEvaluationRecords(
      getPredictions(),
      result.records,
    );

    setPredictions(merged.records);
    renderSummary(result);

    elements.globalEvaluationProgress.value = 100;
    elements.globalEvaluationProgressText.textContent =
      `${result.completedCount}銘柄成功・${result.failedCount}銘柄失敗。` +
      `最終テスト${result.summary.sampleCount}件を成績へ保存しました。`;

    setStatus(
      result.failedCount ? "部分完了" : "完了",
      result.failedCount ? "" : "passed",
    );
  } catch (error) {
    if (error?.name === "AbortError") {
      setStatus("停止");
      elements.globalEvaluationProgressText.textContent =
        "一括検証を停止しました。完了済み銘柄は今回は保存していません。";
    } else {
      console.error("Global evaluation:", error);
      setStatus("失敗", "failed");
      elements.globalEvaluationProgressText.textContent =
        error?.message || "一括検証に失敗しました。";
    }
  } finally {
    setRunning(false);
    evaluationController = null;
  }
}

function stopGlobalEvaluation() {
  evaluationController?.abort();
}

export function initGlobalEvaluation() {
  [
    "globalEvaluationSymbols",
    "globalEvaluationPeriod",
    "runGlobalEvaluationButton",
    "stopGlobalEvaluationButton",
    "globalEvaluationStatus",
    "globalEvaluationProgress",
    "globalEvaluationProgressText",
    "globalEvaluationSummary",
    "globalEvaluationWarnings",
    "globalEvaluationResults",
    "globalMetricSymbols",
    "globalMetricSamples",
    "globalMetricWinRate",
    "globalMetricCoverage",
    "globalMetricStrategyReturn",
    "globalMetricBenchmarkReturn",
    "globalMetricExcessReturn",
    "globalMetricDrawdown",
  ].forEach((id) => {
    elements[id] = document.getElementById(id);
  });

  if (Object.values(elements).some((element) => !element)) {
    console.warn("Global evaluation UI elements are incomplete.");
    return;
  }

  elements.runGlobalEvaluationButton.addEventListener(
    "click",
    startGlobalEvaluation,
  );
  elements.stopGlobalEvaluationButton.addEventListener(
    "click",
    stopGlobalEvaluation,
  );

  setRunning(false);
  renderResultRows();
}