export const P25_SIGNAL_INTENT_VERSION = "p25-signal-intent-v1";

export const P25_SIGNAL_INTENT_SAFETY = Object.freeze({
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  freshHoldoutConsumed: false,
});

function required(value, name) {
  if (value === null || value === undefined || value === "") {
    throw new Error(`${name} is required.`);
  }
  return value;
}

function normalizeDirection(value) {
  const normalized = String(required(value, "direction")).trim().toUpperCase();
  if (!['UP', 'DOWN'].includes(normalized)) {
    throw new Error('direction must be UP or DOWN.');
  }
  return normalized;
}

function assertResearchOnlySafety() {
  for (const [key, value] of Object.entries(P25_SIGNAL_INTENT_SAFETY)) {
    if (value !== false) throw new Error(`unsafe P25 signal intent flag: ${key}`);
  }
}

export function createP25ResearchIntent({
  signalId,
  evidenceDate,
  sourceTimestamp,
  symbol,
  direction,
  universeVariant,
  modelVersion,
  lineageHeadSha256,
  confidence = null,
  score = null,
  setup = null,
  metadata = {},
} = {}) {
  assertResearchOnlySafety();

  const normalizedSymbol = String(required(symbol, 'symbol')).trim().toUpperCase();
  const normalizedDirection = normalizeDirection(direction);

  return Object.freeze({
    version: P25_SIGNAL_INTENT_VERSION,
    intentId: String(required(signalId, 'signalId')),
    evidenceDate: String(required(evidenceDate, 'evidenceDate')),
    sourceTimestamp: String(required(sourceTimestamp, 'sourceTimestamp')),
    symbol: normalizedSymbol,
    direction: normalizedDirection,
    universeVariant: String(required(universeVariant, 'universeVariant')),
    modelVersion: String(required(modelVersion, 'modelVersion')),
    lineageHeadSha256: String(required(lineageHeadSha256, 'lineageHeadSha256')),
    confidence: confidence === null ? null : Number(confidence),
    score: score === null ? null : Number(score),
    setup: setup === null ? null : String(setup),
    disposition: normalizedDirection === 'UP' ? 'paper_long_candidate' : 'observe_down_only',
    executable: false,
    brokerPayload: null,
    paperOrderPayload: null,
    safety: P25_SIGNAL_INTENT_SAFETY,
    metadata: Object.freeze({ ...(metadata || {}) }),
  });
}

export function toPaperOrderResearchDraft(intent, { quantity = 100 } = {}) {
  assertResearchOnlySafety();
  if (!intent || intent.version !== P25_SIGNAL_INTENT_VERSION) {
    throw new Error('valid P25 research intent is required.');
  }
  if (intent.direction !== 'UP') {
    return Object.freeze({ eligible: false, reason: 'short_disabled', orderInput: null });
  }
  const qty = Number(quantity);
  if (!Number.isInteger(qty) || qty <= 0 || qty % 100 !== 0) {
    throw new Error('quantity must be a positive 100-share lot.');
  }
  return Object.freeze({
    eligible: true,
    reason: null,
    orderInput: Object.freeze({
      symbol: intent.symbol,
      side: 'buy',
      quantity: qty,
      type: 'market',
      metadata: Object.freeze({
        researchOnly: true,
        sourceIntentId: intent.intentId,
        evidenceDate: intent.evidenceDate,
        sourceTimestamp: intent.sourceTimestamp,
        universeVariant: intent.universeVariant,
        modelVersion: intent.modelVersion,
        lineageHeadSha256: intent.lineageHeadSha256,
      }),
    }),
    executable: false,
  });
}

export const P25SignalIntentInternals = Object.freeze({
  assertResearchOnlySafety,
  normalizeDirection,
});
