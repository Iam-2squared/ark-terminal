import {
  detectMarketRegime as detectLegacyRegime,
} from "../analysis/market-regime-engine.js";
import { regimeRecommendation } from "../market-context/market-regime.js";

export const SNAPSHOT_REGIMES = Object.freeze({
  BULL: "BULL",
  BEAR: "BEAR",
  RANGE: "RANGE",
  HIGH_VOLATILITY: "HIGH_VOLATILITY",
  LOW_VOLATILITY: "LOW_VOLATILITY",
  UNKNOWN: "UNKNOWN",
});

const REGIME_LABELS = Object.freeze({
  BULL: "強気",
  BEAR: "弱気",
  RANGE: "レンジ",
  HIGH_VOLATILITY: "高ボラティリティ",
  LOW_VOLATILITY: "低ボラティリティ",
  UNKNOWN: "判定不能",
});

const RISK_MULTIPLIERS = Object.freeze({
  BULL: 1.2,
  BEAR: 0.45,
  RANGE: 0.9,
  HIGH_VOLATILITY: 0.65,
  LOW_VOLATILITY: 0.85,
  UNKNOWN: 0,
});

function finiteOrNull(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function clamp(value, minimum = 0, maximum = 100) {
  return Math.min(maximum, Math.max(minimum, value));
}

function findVixLevel(macro) {
  const item = macro?.items?.find((candidate) => candidate.symbol === "VIX");
  return item?.available ? finiteOrNull(item.price ?? macro?.vixLevel) : null;
}

function vixLevelFromMacro(macro) {
  const direct = finiteOrNull(macro?.vixLevel);

  if (direct !== null) {
    return direct;
  }

  return findVixLevel(macro);
}

export function scoreVixVolatility(vix) {
  const level = finiteOrNull(vix);

  if (level === null) return null;
  return clamp(((level - 10) / 30) * 100);
}

function calculateRegimeConfidence(score, indexes, macro, name) {
  const reports = [indexes, macro].filter(
    (report) => finiteOrNull(report?.score) !== null,
  );

  if (!reports.length || score === null) {
    return 0;
  }

  const sourceConfidence =
    reports.reduce(
      (total, report) => total + clamp(finiteOrNull(report.confidence) ?? 0),
      0,
    ) / reports.length;
  const decisive =
    name === SNAPSHOT_REGIMES.HIGH_VOLATILITY
      ? 100
      : Math.min(100, Math.abs(score - 50) * 2);

  return Math.round(sourceConfidence * 0.75 + decisive * 0.25);
}

function reasonsFor({ score, indexes, macro, vix, name }) {
  const reasons = [`総合市場スコアは${Math.round(score)}点です。`];

  if (finiteOrNull(indexes?.score) !== null) {
    reasons.push(`世界株指数スコアは${Math.round(indexes.score)}点です。`);
  }

  if (finiteOrNull(macro?.score) !== null) {
    reasons.push(`マクロスコアは${Math.round(macro.score)}点です。`);
  }

  if (vix !== null) {
    reasons.push(`VIXは${Math.round(vix * 100) / 100}です。`);
  }

  if (name === SNAPSHOT_REGIMES.UNKNOWN) {
    reasons.push("利用可能な市場データが不足しています。");
  }

  return reasons;
}

export function detectSnapshotMarketRegime({
  score,
  indexes = {},
  macro = {},
} = {}) {
  const marketScore = finiteOrNull(score);

  if (marketScore === null) {
    return {
      name: SNAPSHOT_REGIMES.UNKNOWN,
      label: REGIME_LABELS.UNKNOWN,
      confidence: 0,
      riskMultiplier: RISK_MULTIPLIERS.UNKNOWN,
      recommendation: "Neutral",
      reasons: ["利用可能な市場データが不足しています。"],
    };
  }

  const indexScore = finiteOrNull(indexes?.score);
  const vix = vixLevelFromMacro(macro);
  const legacy = detectLegacyRegime({
    trendScore: marketScore,
    breadth: indexScore ?? 50,
    momentum: indexScore ?? 50,
    volatility: scoreVixVolatility(vix) ?? 50,
    vix: vix ?? 20,
  });
  let name =
    legacy.regime === "SIDEWAYS" ? SNAPSHOT_REGIMES.RANGE : legacy.regime;

  if (vix !== null && vix >= 35) {
    name = SNAPSHOT_REGIMES.HIGH_VOLATILITY;
  } else if (
    vix !== null &&
    vix <= 15 &&
    Math.abs(marketScore - 50) <= 10
  ) {
    name = SNAPSHOT_REGIMES.LOW_VOLATILITY;
  }

  if (!Object.values(SNAPSHOT_REGIMES).includes(name)) {
    name = SNAPSHOT_REGIMES.RANGE;
  }

  return {
    name,
    label: REGIME_LABELS[name],
    confidence: calculateRegimeConfidence(
      marketScore,
      indexes,
      macro,
      name,
    ),
    riskMultiplier: RISK_MULTIPLIERS[name],
    recommendation: regimeRecommendation({ regime: name }).recommendation,
    reasons: reasonsFor({
      score: marketScore,
      indexes,
      macro,
      vix,
      name,
    }),
  };
}

export class MarketRegime {
  detect(input = {}) {
    return detectSnapshotMarketRegime(input);
  }
}

export const marketRegime = new MarketRegime();

export default detectSnapshotMarketRegime;
