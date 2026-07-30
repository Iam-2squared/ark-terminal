function finite(value) {
  return Number.isFinite(Number(value));
}

function clamp(value, minimum = 0, maximum = 100) {
  return Math.min(maximum, Math.max(minimum, Number(value)));
}

function directionFromScore(score) {
  if (Number(score) >= 55) {
    return "強気";
  }

  if (Number(score) <= 45) {
    return "弱気";
  }

  return "中立";
}

function factorDirection(score) {
  if (Number(score) >= 55) {
    return "強気";
  }

  if (Number(score) <= 45) {
    return "弱気";
  }

  return "中立";
}

function indicatorAgreement(analysis, direction) {
  const available = analysis.factors.filter(
    (factor) => factor.available && factor.category !== "external",
  );

  if (!available.length) {
    return null;
  }

  const aligned = available.filter(
    (factor) => factorDirection(factor.score) === direction,
  ).length;

  return (aligned / available.length) * 100;
}

function reliableHistoryScore(records) {
  if (!records.length) {
    return null;
  }

  const wins = records.filter((record) => record.hit).length;
  const winRate = (wins / records.length) * 100;
  const shrinkage = records.length / (records.length + 30);

  return 50 + (winRate - 50) * shrinkage;
}

function resolvedRecords(records) {
  const resolved = records.filter(
    (record) =>
      record.status === "resolved" && Number.isFinite(Number(record.hit)),
  );
  const testRecords = resolved.filter((record) => record.partition === "test");

  return testRecords.length ? testRecords : resolved;
}

function confidenceLabel(score) {
  if (score >= 75) {
    return "高";
  }

  if (score >= 55) {
    return "中";
  }

  return "低";
}

export function createPredictionOutput({
  analysis,
  indicators,
  quality,
  period,
  records = [],
  symbol,
  marketEnvironment,
}) {
  const direction = directionFromScore(analysis.totalScore);
  const atrPercent = Number(indicators.atr?.percent);
  const expectedAmplitude = finite(atrPercent)
    ? atrPercent * Math.sqrt(Math.max(1, Number(period) || 1))
    : null;
  const scoreBias =
    ((Number(analysis.totalScore) - 50) / 50) * (expectedAmplitude || 0) * 0.35;
  const lower = finite(expectedAmplitude)
    ? scoreBias - expectedAmplitude
    : null;
  const upper = finite(expectedAmplitude)
    ? scoreBias + expectedAmplitude
    : null;
  const relevantRecords = resolvedRecords(records);
  const symbolRecords = relevantRecords.filter(
    (record) => record.symbol === symbol,
  );
  const regime = marketEnvironment?.regime;
  const regimeRecords =
    regime && regime !== "データなし"
      ? relevantRecords.filter((record) => record.marketRegime === regime)
      : [];
  const agreement = indicatorAgreement(analysis, direction);
  const components = [
    {
      key: "historyCount",
      label: "履歴件数",
      score: clamp((Number(indicators.candleCount) / 504) * 100),
      detail: `${indicators.candleCount}営業日`,
      weight: 20,
    },
    {
      key: "missingRate",
      label: "欠損・品質",
      score: quality?.canScore ? quality.qualityScore : 0,
      detail: `欠損率${Number(quality?.missingRate || 0).toFixed(2)}%`,
      weight: 25,
    },
    {
      key: "indicatorAgreement",
      label: "指標一致度",
      score: agreement,
      detail: finite(agreement) ? `${Math.round(agreement)}%一致` : "未算出",
      weight: 25,
    },
    {
      key: "symbolPerformance",
      label: "銘柄別実績",
      score: reliableHistoryScore(symbolRecords),
      detail: `${symbolRecords.length}件`,
      weight: 20,
    },
    {
      key: "regimePerformance",
      label: "相場環境別実績",
      score: reliableHistoryScore(regimeRecords),
      detail:
        regime && regime !== "データなし"
          ? `${regime}・${regimeRecords.length}件`
          : "環境未取得",
      weight: 10,
    },
  ].map((component) => ({
    ...component,
    available: finite(component.score),
  }));
  const available = components.filter((component) => component.available);
  const weightTotal = available.reduce(
    (sum, component) => sum + component.weight,
    0,
  );
  const confidenceScore = weightTotal
    ? Math.round(
        available.reduce(
          (sum, component) => sum + component.score * component.weight,
          0,
        ) / weightTotal,
      )
    : 0;

  return {
    direction,
    expectedMoveRange: finite(lower)
      ? {
          lower,
          upper,
          amplitude: expectedAmplitude,
          method: `ATR×√${Math.max(1, Number(period) || 1)}の概算`,
        }
      : null,
    downsideRisk: finite(lower) ? Math.abs(Math.min(0, lower)) : null,
    confidence: {
      score: confidenceScore,
      label: confidenceLabel(confidenceScore),
      components,
      method:
        "履歴件数・欠損率・指標一致度・銘柄別実績・相場環境別実績の加重平均",
      isProbability: false,
    },
  };
}

export const PredictionOutputInternals = {
  directionFromScore,
  factorDirection,
  indicatorAgreement,
  reliableHistoryScore,
};
