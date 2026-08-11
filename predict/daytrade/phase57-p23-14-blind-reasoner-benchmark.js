export const P23_14_BLIND_REASONER_POLICY = Object.freeze({
  phase: '57.p23.14',
  id: 'BLIND_VISUAL_MANIFEST_REASONER_V1',
  purpose: 'FREEZE_CAUSAL_VISUAL_REASONING_BEFORE_OUTCOME_JOIN',
  externalVisionModelCalled: false,
  outcomeVisibleAtPredictionTime: false,
  outcomeFieldsStrippedBeforeReasoning: true,
  thresholdSearchPerformed: false,
  predictionUsedAsEntryGate: false,
  recommendationAllowed: false,
  edgeClaimAllowed: false,
});

export const PHASE57_P23_14_SAFETY = Object.freeze({
  mode: 'PHASE57_P23_14_BLIND_REASONER_READ_ONLY_RESEARCH',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  overnightHoldingAllowed: false,
  transmitted: false,
});

const finite = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
const clamp = (value, lo = 0, hi = 1) => Math.max(lo, Math.min(hi, Number(value)));

function normalizeDirection(value) {
  if (value === 1 || value === 'UP' || value === 'LONG') return 'UP';
  if (value === -1 || value === 'DOWN' || value === 'SHORT') return 'DOWN';
  return 'NONE';
}

function confidenceBand(score) {
  const s = Number(score);
  if (!finite(s)) return 'UNSCORED';
  if (s >= 0.72) return 'A';
  if (s >= 0.60) return 'B';
  if (s >= 0.48) return 'C';
  return 'D';
}

export function stripOutcomeFields(record = {}) {
  return Object.freeze({
    symbol: String(record.symbol ?? ''),
    sessionDate: record.sessionDate ?? null,
    featureCutoff: record.featureCutoff ?? null,
    setup: String(record.setup ?? 'NO_CLEAR_SETUP'),
    direction: normalizeDirection(record.direction),
    visualScore: finite(record.visualScore) ? Number(record.visualScore) : null,
    visualBand: record.visualBand ?? null,
    visualComponents: record.visualComponents ?? {},
    visualGeometry: record.visualGeometry ?? {},
    visualNarrative: record.visualNarrative ?? {},
    legacyQualityScore: finite(record.legacyQualityScore) ? Number(record.legacyQualityScore) : null,
    legacyQualityBand: record.legacyQualityBand ?? null,
  });
}

export function buildBlindReasoningPrediction(record = {}) {
  const x = stripOutcomeFields(record);
  const c = x.visualComponents ?? {};
  const room = finite(c.spaceToObstacle) ? Number(c.spaceToObstacle) : 0.5;
  const structure = finite(c.structureCoherence) ? Number(c.structureCoherence) : 0.5;
  const pressure = finite(c.directionalPressure) ? Number(c.directionalPressure) : 0.5;
  const wick = finite(c.wickControl) ? Number(c.wickControl) : 0.5;
  const participation = finite(c.participation) ? Number(c.participation) : 0.5;
  const extension = finite(c.extensionHealth) ? Number(c.extensionHealth) : 0.5;
  const volatility = finite(c.volatilityTransition) ? Number(c.volatilityTransition) : 0.5;
  const geometry = finite(c.setupGeometryFit) ? Number(c.setupGeometryFit) : 0.5;

  const evidenceScore = clamp(
    0.20 * structure +
    0.15 * pressure +
    0.10 * wick +
    0.10 * participation +
    0.12 * extension +
    0.15 * room +
    0.08 * volatility +
    0.10 * geometry
  );

  const direction = x.direction;
  return Object.freeze({
    key: `${x.symbol}|${x.featureCutoff}|${x.setup}`,
    symbol: x.symbol,
    sessionDate: x.sessionDate,
    featureCutoff: x.featureCutoff,
    setup: x.setup,
    direction,
    primaryScenario: direction === 'NONE' ? 'OBSERVE' : `CONTINUATION_${direction}`,
    alternativeScenario: direction === 'UP' ? 'FAILED_CONTINUATION_DOWN' : direction === 'DOWN' ? 'FAILED_CONTINUATION_UP' : 'NONE',
    confidenceScore: evidenceScore,
    confidenceBand: confidenceBand(evidenceScore),
    obstacleRisk: clamp(1 - room),
    extensionRisk: clamp(1 - extension),
    rejectionRisk: clamp(1 - wick),
    uncertainty: clamp(1 - Math.abs(evidenceScore - 0.5) * 2),
    visibleStructure: x.visualNarrative?.primary ?? null,
    higherTimeframeContext: structure >= 0.70 ? 'SUPPORTIVE' : structure <= 0.35 ? 'CONFLICT' : 'MIXED',
    nearestObstacle: x.visualGeometry?.nearestObstacle ?? null,
    invalidationEvidence: x.visualNarrative?.observations ?? [],
    causalInputsOnly: true,
    futureOutcomeVisible: false,
    outcomeUsedForPrediction: false,
    predictionUsedAsEntryGate: false,
    thresholdSearchPerformed: false,
    externalVisionModelCalled: false,
    recommendationAllowed: false,
    transmitted: false,
    ...PHASE57_P23_14_SAFETY,
  });
}

export default {
  P23_14_BLIND_REASONER_POLICY,
  PHASE57_P23_14_SAFETY,
  stripOutcomeFields,
  buildBlindReasoningPrediction,
};
