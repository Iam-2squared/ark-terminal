import {
  AI_ACCURACY_HORIZONS,
  AI_ACCURACY_MONITOR_VERSION,
} from "./ai-accuracy-monitor-engine.js";

function finiteNumber(value) {
  const number = Number(value);

  return value !== null && value !== "" && Number.isFinite(number)
    ? number
    : null;
}

function formatNumber(value, digits = 1) {
  const number = finiteNumber(value);

  return number === null
    ? "--"
    : number.toLocaleString("ja-JP", {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      });
}

function formatPercent(value, digits = 1) {
  const number = finiteNumber(value);

  return number === null ? "--" : `${formatNumber(number, digits)}%`;
}

function formatPoint(value, digits = 2) {
  const number = finiteNumber(value);

  return number === null ? "--" : `${formatNumber(number, digits)}pt`;
}

function formatInterval(interval = {}) {
  const lower = finiteNumber(interval?.lower);
  const upper = finiteNumber(interval?.upper);

  return lower === null || upper === null
    ? "95%信頼区間 --"
    : `95%信頼区間 ${formatNumber(lower, 1)}〜${formatNumber(upper, 1)}%`;
}

function sourceText(report) {
  if (report.source === "observed") {
    return {
      badge: "実績値",
      badgeClass: "observed",
      label: `実績予測・直近${report.recentWindow}件枠`,
      description: "保存後に結果が確定した予測を集計",
    };
  }

  if (report.source === "walk-forward-test") {
    return {
      badge: "検証値",
      badgeClass: "validation",
      label: `Walk Forward 最終テスト・直近${report.recentWindow}件枠`,
      description: "実績予測が未蓄積のため最終テストのみを表示",
    };
  }

  return {
    badge: "未算出",
    badgeClass: "unavailable",
    label: "確定済み評価なし",
    description: "予測結果が確定すると自動で数値化されます",
  };
}

function statusText(report) {
  if (report.status === "ready") {
    return {
      label: "算出済み",
      className: "ready",
    };
  }

  if (report.status === "preliminary") {
    return {
      label: "暫定値",
      className: "preliminary",
    };
  }

  return {
    label: "データ待ち",
    className: "unavailable",
  };
}

function normalizeHorizon(report, horizon) {
  const result = report.horizons?.find(
    (item) => Number(item.horizon) === horizon,
  );

  return {
    horizon,
    label: `${horizon}日`,
    accuracy: formatPercent(result?.accuracy),
    sampleLabel: result?.sampleCount
      ? `${result.sampleCount}件`
      : "データなし",
    intervalLabel: formatInterval(result?.confidenceInterval),
    available: finiteNumber(result?.accuracy) !== null,
  };
}

function evidenceView(evidence, label) {
  return {
    label,
    accuracy: formatPercent(evidence?.accuracy),
    sampleLabel: `採用 ${evidence?.sampleCount ?? 0}件 / 確定 ${
      evidence?.resolvedCount ?? 0
    }件`,
    coverage: formatPercent(evidence?.coverageRate),
    available: finiteNumber(evidence?.accuracy) !== null,
  };
}

function emptyReport() {
  return {
    version: AI_ACCURACY_MONITOR_VERSION,
    status: "unavailable",
    source: "none",
    recentWindow: 30,
    current: {},
    allTime: {},
    horizons: [],
    forecastError: {},
    calibration: {},
    reliability: {
      code: "no-data",
      label: "評価データなし",
    },
    evidence: {},
    audit: {
      pendingCount: 0,
    },
    executionAllowed: false,
  };
}

export function buildAIAccuracyMonitorViewModel(report, { error = null } = {}) {
  const safeReport = report && typeof report === "object" ? report : emptyReport();
  const source = sourceText(safeReport);
  const status = error
    ? {
        label: "読込エラー",
        className: "unavailable",
      }
    : statusText(safeReport);
  const calibrationGap = finiteNumber(safeReport.calibration?.calibrationGap);

  return {
    version: safeReport.version ?? AI_ACCURACY_MONITOR_VERSION,
    title: "AI Accuracy Monitor",
    heading: "現在のAI精度",
    status,
    source,
    accuracy: formatPercent(safeReport.current?.accuracy),
    accuracyAvailable: finiteNumber(safeReport.current?.accuracy) !== null,
    sampleLabel: `採用 ${safeReport.current?.sampleCount ?? 0}件 / 確定 ${
      safeReport.current?.resolvedCount ?? 0
    }件`,
    intervalLabel: formatInterval(safeReport.current?.confidenceInterval),
    reliabilityLabel: safeReport.reliability?.label ?? "評価データなし",
    metrics: [
      {
        label: "評価カバレッジ",
        value: formatPercent(safeReport.current?.coverageRate),
        detail: "確定予測のうち採用判定された割合",
      },
      {
        label: "全期間の精度",
        value: formatPercent(safeReport.allTime?.accuracy),
        detail: `採用 ${safeReport.allTime?.sampleCount ?? 0}件`,
      },
      {
        label: "平均予測誤差 MAE",
        value: formatPoint(safeReport.forecastError?.meanAbsoluteError),
        detail: `算出 ${safeReport.forecastError?.count ?? 0}件`,
      },
      {
        label: "信頼度とのズレ",
        value:
          calibrationGap === null
            ? "--"
            : formatPoint(calibrationGap * 100),
        detail: `較正 ${safeReport.calibration?.count ?? 0}件`,
      },
      {
        label: "判定待ち",
        value: `${safeReport.audit?.pendingCount ?? 0}件`,
        detail: "期間経過後に実績へ移行",
      },
    ],
    horizons: AI_ACCURACY_HORIZONS.map((horizon) =>
      normalizeHorizon(safeReport, horizon),
    ),
    evidence: [
      evidenceView(safeReport.evidence?.observed, "実績予測"),
      evidenceView(
        safeReport.evidence?.validation,
        "Walk Forward 最終テスト",
      ),
    ],
    message: error
      ? "保存済み評価データを読み込めませんでした。再読み込みしてください。"
      : safeReport.current?.sampleCount > 0 && safeReport.current.sampleCount < 30
        ? "評価件数が30件未満のため、この精度は暫定値です。"
        : safeReport.current?.sampleCount >= 30
          ? "精度は確定済み評価だけで算出しています。"
          : "分析を保存し、予測期間が経過すると実績精度が表示されます。",
    notice:
      "精度は過去に確定した方向予測の的中率であり、将来の利益や結果を保証しません。Confidence はデータ品質で、的中確率ではありません。",
    executionAllowed: false,
  };
}

export const AIAccuracyMonitorViewModelInternals = Object.freeze({
  formatNumber,
  formatPercent,
  formatPoint,
  formatInterval,
  sourceText,
  statusText,
});
