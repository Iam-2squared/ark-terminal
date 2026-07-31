import {
  groupPerformance,
  summarizePerformance,
} from "../backtest/engine.js";
import {
  activeConditionsForRecord,
  FEATURE_DEFINITIONS,
} from "./feature-extractor.js";

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function average(values) {
  const numbers = values.filter(finite).map(Number);

  return numbers.length
    ? numbers.reduce((sum, value) => sum + value, 0) / numbers.length
    : null;
}

function resolved(records) {
  return records.filter(
    (record) =>
      record.status === "resolved" && finite(record.actualReturn),
  );
}

function strategyReturn(record) {
  return finite(record.strategyReturn)
    ? Number(record.strategyReturn)
    : Number(record.actualReturn);
}

function dateOf(record) {
  const date = new Date(record.resolvedAt || record.createdAt);

  return Number.isNaN(date.getTime()) ? null : date;
}

export function recentRecords(records, days = 30, referenceDate = new Date()) {
  const threshold =
    referenceDate.getTime() - Number(days) * 24 * 60 * 60 * 1000;

  return resolved(records).filter((record) => {
    const date = dateOf(record);

    return date && date.getTime() >= threshold;
  });
}

function summarizeReturns(records) {
  const items = resolved(records);
  const returns = items.map(strategyReturn).filter(finite);
  const profits = returns.filter((value) => value > 0);
  const losses = returns.filter((value) => value < 0);

  return {
    sampleCount: items.length,
    winRate: items.length
      ? (items.filter((record) => record.hit).length / items.length) * 100
      : null,
    averageReturn: average(returns),
    averageProfit: average(profits),
    averageLoss: average(losses),
    maximumProfit: profits.length ? Math.max(...profits) : null,
    maximumLoss: losses.length ? Math.min(...losses) : null,
  };
}

export function indicatorAccuracy(records) {
  const groups = new Map();

  resolved(records).forEach((record) => {
    activeConditionsForRecord(record).forEach((condition) => {
      if (!groups.has(condition.key)) {
        groups.set(condition.key, []);
      }

      groups.get(condition.key).push(record);
    });
  });

  return Array.from(groups.entries())
    .map(([key, items]) => ({
      key,
      label: FEATURE_DEFINITIONS[key]?.label || key,
      factorKey: FEATURE_DEFINITIONS[key]?.factorKey || key,
      category: FEATURE_DEFINITIONS[key]?.category || "unknown",
      ...summarizeReturns(items),
    }))
    .sort(
      (first, second) =>
        (second.winRate || 0) - (first.winRate || 0) ||
        second.sampleCount - first.sampleCount,
    );
}

function combinations(values, size) {
  const result = [];

  function walk(start, selected) {
    if (selected.length === size) {
      result.push(selected);
      return;
    }

    for (let index = start; index < values.length; index += 1) {
      walk(index + 1, [...selected, values[index]]);
    }
  }

  walk(0, []);

  return result;
}

export function combinationAccuracy(
  records,
  { sizes = [2, 3], minimumSamples = 3, limit = 30 } = {},
) {
  const groups = new Map();

  resolved(records).forEach((record) => {
    const keys = [
      ...new Set(activeConditionsForRecord(record).map((item) => item.key)),
    ]
      .sort()
      .slice(0, 10);

    sizes.forEach((size) => {
      combinations(keys, size).forEach((combination) => {
        const key = combination.join("+");

        if (!groups.has(key)) {
          groups.set(key, []);
        }

        groups.get(key).push(record);
      });
    });
  });

  return Array.from(groups.entries())
    .map(([key, items]) => ({
      key,
      keys: key.split("+"),
      label: key
        .split("+")
        .map((item) => FEATURE_DEFINITIONS[item]?.label || item)
        .join(" ＋ "),
      ...summarizeReturns(items),
    }))
    .filter((item) => item.sampleCount >= minimumSamples)
    .sort(
      (first, second) =>
        (second.winRate || 0) - (first.winRate || 0) ||
        (second.averageReturn || 0) - (first.averageReturn || 0) ||
        second.sampleCount - first.sampleCount,
    )
    .slice(0, limit);
}

export function forecastErrorMetrics(records) {
  const errors = resolved(records)
    .filter(
      (record) =>
        finite(record.expectedReturn) && finite(record.actualReturn),
    )
    .map((record) => Number(record.actualReturn) - Number(record.expectedReturn));

  return {
    sampleCount: errors.length,
    mae: errors.length
      ? average(errors.map((error) => Math.abs(error)))
      : null,
    rmse: errors.length
      ? Math.sqrt(average(errors.map((error) => error ** 2)))
      : null,
    bias: average(errors),
  };
}

export function scoreBucket(record) {
  const score = Number(record.score);

  if (score >= 75) return "75–100";
  if (score >= 60) return "60–74";
  if (score >= 45) return "45–59";
  if (score >= 30) return "30–44";
  return "0–29";
}

export function confidenceBucket(record) {
  const value = Number(record.confidence?.score ?? record.confidence);

  if (!finite(value)) return "未取得";
  if (value >= 75) return "高（75–100）";
  if (value >= 55) return "中（55–74）";
  return "低（0–54）";
}

export function riskBucket(record) {
  const value = Number(record.downsideRisk);

  if (!finite(value)) return "未取得";
  if (value <= 2) return "低（2%以下）";
  if (value <= 5) return "中（2–5%）";
  return "高（5%超）";
}

export function priceBucket(record) {
  const value = Number(record.predictionPrice);

  if (!finite(value)) return "未取得";
  if (value < 300) return "0–299";
  if (value < 500) return "300–499";
  if (value < 1_000) return "500–999";
  if (value < 3_000) return "1,000–2,999";
  return "3,000以上";
}

export function marketBucket(record) {
  return record.market || record.exchange || "未取得";
}

export function regimeBucket(record) {
  const value = record.marketRegime;

  if (["強気", "Bull"].includes(value)) return "Bull";
  if (["弱気", "Bear"].includes(value)) return "Bear";
  if (["中立", "Sideways"].includes(value)) return "Sideways";
  return "未取得";
}

export function recordMonth(record) {
  const date = dateOf(record);

  return date
    ? `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`
    : "不明";
}

function improvementInsights({
  allRecords,
  recent,
  indicatorAll,
  indicatorRecent,
  forecastAll,
  forecastRecent,
}) {
  const insights = [];
  const recentByKey = new Map(
    indicatorRecent.map((indicator) => [indicator.key, indicator]),
  );
  const declining = indicatorAll
    .map((indicator) => {
      const latest = recentByKey.get(indicator.key);

      return {
        ...indicator,
        recentWinRate: latest?.winRate,
        recentSamples: latest?.sampleCount || 0,
        delta:
          finite(latest?.winRate) && finite(indicator.winRate)
            ? latest.winRate - indicator.winRate
            : null,
      };
    })
    .filter(
      (indicator) =>
        indicator.recentSamples >= 5 && finite(indicator.delta),
    )
    .sort((first, second) => first.delta - second.delta);

  if (declining.length && declining[0].delta < -3) {
    const item = declining[0];

    insights.push({
      level: "warning",
      title: `${item.label}の直近精度が低下`,
      detail: `全期間比${item.delta.toFixed(1)}ポイント。直近${item.recentSamples}件を確認してください。`,
    });
  }

  const industryFactor = industryIndicatorRanking(allRecords).find(
    (item) => item.sampleCount >= 5,
  );

  if (industryFactor) {
    insights.push({
      level: "positive",
      title: `${industryFactor.industry}では${industryFactor.label}が有効`,
      detail: `${industryFactor.sampleCount}件・勝率${industryFactor.winRate.toFixed(1)}%。業種別推奨重みの根拠になります。`,
    });
  }

  const regimes = groupPerformance(allRecords, regimeBucket).filter(
    (group) => group.key !== "未取得" && group.sampleCount >= 5,
  );
  const weakestRegime = [...regimes].sort(
    (first, second) => (first.winRate || 0) - (second.winRate || 0),
  )[0];

  if (weakestRegime) {
    insights.push({
      level: "warning",
      title: `${weakestRegime.key}相場の精度を改善`,
      detail: `${weakestRegime.sampleCount}件・勝率${weakestRegime.winRate.toFixed(1)}%。相場環境別の補正候補です。`,
    });
  }

  if (forecastRecent.sampleCount >= 5 && finite(forecastRecent.bias)) {
    insights.push({
      level: Math.abs(forecastRecent.bias) >= 1 ? "warning" : "neutral",
      title:
        forecastRecent.bias < -1
          ? "期待変動幅を過大評価する傾向"
          : forecastRecent.bias > 1
            ? "期待変動幅を過小評価する傾向"
            : "期待変動幅の偏りは小さい",
      detail: `直近30日の誤差バイアス${forecastRecent.bias.toFixed(2)}%、MAE ${forecastRecent.mae?.toFixed(2) ?? "--"}%。`,
    });
  }

  if (!insights.length) {
    insights.push({
      level: "neutral",
      title: "改善判断に必要な検証データを蓄積中",
      detail: `確定${resolved(allRecords).length}件、直近30日${recent.length}件。各条件5件以上から傾向を表示します。`,
    });
  }

  return insights.slice(0, 5);
}

export function industryIndicatorRanking(records) {
  const groups = new Map();

  resolved(records).forEach((record) => {
    const industry = record.industry || "未分類";

    activeConditionsForRecord(record).forEach((condition) => {
      const key = `${industry}::${condition.key}`;

      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(record);
    });
  });

  return Array.from(groups.entries())
    .map(([key, items]) => {
      const [industry, featureKey] = key.split("::");

      return {
        industry,
        featureKey,
        label: FEATURE_DEFINITIONS[featureKey]?.label || featureKey,
        ...summarizeReturns(items),
      };
    })
    .sort(
      (first, second) =>
        (second.winRate || 0) - (first.winRate || 0) ||
        second.sampleCount - first.sampleCount,
    );
}

let analyticsCache = {
  key: null,
  value: null,
};

function cacheKey(records) {
  const last = records.at(-1);

  return [
    records.length,
    last?.id || "",
    last?.resolvedAt || last?.createdAt || "",
    records.filter((record) => record.status === "resolved").length,
  ].join(":");
}

export function buildPerformanceAnalytics(records, now = new Date()) {
  const key = `${cacheKey(records)}:${now.toISOString().slice(0, 10)}`;

  if (analyticsCache.key === key) {
    return analyticsCache.value;
  }

  const all = resolved(records);
  const recent = recentRecords(all, 30, now);
  const indicatorAll = indicatorAccuracy(all);
  const indicatorRecent = indicatorAccuracy(recent);
  const forecastAll = forecastErrorMetrics(all);
  const forecastRecent = forecastErrorMetrics(recent);
  const value = {
    all,
    recent,
    comparison: {
      all: summarizePerformance(all),
      recent: summarizePerformance(recent),
      forecastAll,
      forecastRecent,
    },
    indicators: indicatorAll,
    recentIndicators: indicatorRecent,
    combinations: combinationAccuracy(all),
    industryIndicators: industryIndicatorRanking(all),
    dimensions: {
      industry: groupPerformance(all, (record) => record.industry || "未分類"),
      market: groupPerformance(all, marketBucket),
      price: groupPerformance(all, priceBucket),
      score: groupPerformance(all, scoreBucket),
      confidence: groupPerformance(all, confidenceBucket),
      risk: groupPerformance(all, riskBucket),
      regime: groupPerformance(all, regimeBucket),
      month: groupPerformance(all, recordMonth),
      symbol: groupPerformance(all, (record) => record.symbol || "不明"),
      period: groupPerformance(all, (record) => `${record.period}営業日`),
      direction: groupPerformance(all, (record) => record.direction || "不明"),
    },
  };

  value.insights = improvementInsights({
    allRecords: all,
    recent,
    indicatorAll,
    indicatorRecent,
    forecastAll,
    forecastRecent,
  });

  analyticsCache = {
    key,
    value,
  };

  return value;
}

export const AnalyticsInternals = {
  summarizeReturns,
  combinations,
  strategyReturn,
  dateOf,
};
