export const EXPLAINABILITY_V3_VERSION = "explainability-v3";

function finite(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function section(name, values = {}) {
  return {
    name,
    score: finite(values.score),
    confidence: finite(values.confidence),
    reasons: Array.isArray(values.reasons) ? values.reasons.filter(Boolean) : [],
    risks: Array.isArray(values.risks) ? values.risks.filter(Boolean) : [],
    sourceVersion: values.version ?? values.sourceVersion ?? null,
  };
}

export function buildExplainabilityV3({
  decision = "NO_TRADE",
  aiScore = null,
  confidence = null,
  technical = {},
  marketIntelligence = {},
  risk = {},
  strategyReasons = [],
} = {}) {
  const normalizedDecision = String(decision ?? "NO_TRADE").toUpperCase();
  const sections = [
    section("TECHNICAL", technical),
    section("MARKET_INTELLIGENCE", marketIntelligence),
    section("RISK", risk),
  ];
  const reasons = [
    ...strategyReasons,
    ...sections.flatMap((entry) => entry.reasons),
  ].filter(Boolean);
  const risks = sections.flatMap((entry) => entry.risks);

  return {
    version: EXPLAINABILITY_V3_VERSION,
    generatedAt: new Date().toISOString(),
    decision: normalizedDecision,
    headline: `WHY_${normalizedDecision}`,
    aiScore: finite(aiScore),
    confidence: finite(confidence),
    reasons,
    risks,
    sections,
    complete: reasons.length > 0,
    safety: {
      advisoryOnly: true,
      brokerExecutionAllowed: false,
    },
  };
}

export default buildExplainabilityV3;
