export const MARKET_AI_V1 = "market-ai-v1";

function finite(value, fallback = null) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function normalize(value, scale = 1) {
  const number = finite(value, 0) ?? 0;
  return Math.max(-1, Math.min(1, number / scale));
}

export function buildMarketAiV1({
  indices = {},
  macro = {},
  breadth = {},
  sectorRotation = [],
  asOf = null,
} = {}) {
  const indexSignals = Object.entries(indices).map(([name, row]) => ({
    name,
    return1d: finite(row?.return1d, 0) ?? 0,
    return5d: finite(row?.return5d, 0) ?? 0,
    trend: String(row?.trend ?? "UNKNOWN").toUpperCase(),
    timestamp: row?.timestamp ?? null,
  }));

  const futureLeakDetected = Boolean(asOf) && indexSignals.some((row) =>
    row.timestamp && Date.parse(row.timestamp) > Date.parse(asOf),
  );

  const advancers = finite(breadth.advancers, 0) ?? 0;
  const decliners = finite(breadth.decliners, 0) ?? 0;
  const breadthScore = advancers + decliners > 0
    ? (advancers - decliners) / (advancers + decliners)
    : 0;

  const indexScore = indexSignals.length
    ? indexSignals.reduce((sum, row) => sum + normalize(row.return1d, 0.03) * 0.6 + normalize(row.return5d, 0.08) * 0.4, 0) / indexSignals.length
    : 0;
  const ratesScore = -normalize(macro.rateChange, 0.5);
  const fxScore = normalize(macro.fxTailwind, 1);
  const commodityScore = normalize(macro.commodityTailwind, 1);
  const riskScore = indexScore * 0.45 + breadthScore * 0.25 + ratesScore * 0.15 + fxScore * 0.1 + commodityScore * 0.05;

  const regime = riskScore >= 0.25 ? "RISK_ON" : riskScore <= -0.25 ? "RISK_OFF" : "NEUTRAL";
  const sectors = [...sectorRotation]
    .map((row) => ({
      sector: row?.sector ?? "UNKNOWN",
      score: finite(row?.score ?? row?.return, 0) ?? 0,
    }))
    .sort((a, b) => b.score - a.score);

  return {
    version: MARKET_AI_V1,
    generatedAt: new Date().toISOString(),
    status: futureLeakDetected ? "BLOCKED" : "READY",
    regime,
    riskScore,
    indexSignals,
    breadth: { advancers, decliners, score: breadthScore },
    macro: { ...macro },
    sectorRotation: sectors,
    leadingSectors: sectors.slice(0, 5),
    laggingSectors: [...sectors].reverse().slice(0, 5),
    quality: { futureLeakDetected },
    advisoryOnly: true,
    brokerExecutionAllowed: false,
  };
}

export default buildMarketAiV1;
