import { validateHistoryData } from "../analysis/data-quality.js";
import { MARKET_CONTEXT_REGISTRY, relevantMarketSeries } from "./registry.js";

function mean(values) {
  return values.length
    ? values.reduce((sum, value) => sum + Number(value), 0) / values.length
    : null;
}

function simpleAverage(values, period) {
  return values.length >= period ? mean(values.slice(-period)) : null;
}

function analyzeSeries(definition, history) {
  const quality = validateHistoryData(history, {
    minimumHistory: 75,
    requireVolume: false,
    requireOhlcIntegrity: false,
  });

  if (!quality.canScore) {
    return {
      ...definition,
      available: false,
      quality,
      reason: "市場環境データの品質検証に失敗しました。",
    };
  }

  const closes = quality.candles.map((candle) => candle.close);
  const current = closes.at(-1);
  const ma25 = simpleAverage(closes, 25);
  const ma75 = simpleAverage(closes, 75);
  const previous20 = closes.at(-21);
  const return20 =
    previous20 > 0 ? ((current - previous20) / previous20) * 100 : null;
  const checks = [current >= ma25, ma25 >= ma75, return20 >= 0];
  const score = Math.round(
    (checks.filter(Boolean).length / checks.length) * 100,
  );

  return {
    ...definition,
    available: true,
    score,
    current,
    ma25,
    ma75,
    return20,
    quality,
    regime: score >= 67 ? "強気" : score <= 33 ? "弱気" : "中立",
    reason: `${definition.label}は25日線 ${
      current >= ma25 ? "上" : "下"
    }、25日線は75日線${ma25 >= ma75 ? "上" : "下"}です。`,
  };
}

export async function fetchMarketEnvironment({ symbol, fetchHistory, signal }) {
  const relevant = relevantMarketSeries(symbol);
  const settled = await Promise.allSettled(
    relevant.map(async (definition) => {
      const history = await fetchHistory(definition.providerSymbol, {
        range: "1y",
        interval: "1d",
        signal,
      });

      return analyzeSeries(definition, history);
    }),
  );
  const series = settled.map((result, index) =>
    result.status === "fulfilled"
      ? result.value
      : {
          ...relevant[index],
          available: false,
          reason: result.reason?.message || "市場環境データを取得できません。",
        },
  );
  const directional = series.filter(
    (item) => item.available && item.role !== "currency",
  );
  const score = directional.length
    ? Math.round(mean(directional.map((item) => item.score)))
    : null;

  return {
    score,
    regime:
      score === null
        ? "データなし"
        : score >= 67
          ? "強気"
          : score <= 33
            ? "弱気"
            : "中立",
    availableCount: series.filter((item) => item.available).length,
    requestedCount: relevant.length,
    series,
    registry: MARKET_CONTEXT_REGISTRY.map((item) => ({
      id: item.id,
      label: item.label,
      status: item.status,
    })),
  };
}
