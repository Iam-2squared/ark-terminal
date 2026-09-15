import { createHash } from "node:crypto";

export const CASH_EXECUTION_INTENT_SCHEMA = "ARK_PHASE57_CASH_EXECUTION_INTENT_V1";

export const CASH_EXECUTION_ADAPTER_SAFETY = Object.freeze({
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  marginTradingAllowed: false,
  shortSellingAllowed: false,
  marginFallbackAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  transmitted: false,
});

const SOURCE_FALSE_KEYS = Object.freeze([
  "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed", "rssOrderFunctionAllowed",
  "liveTradingAllowed", "paperTradingAllowed", "automaticPromotionAllowed", "productionUpdateAllowed",
]);

function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonical(value[key])]));
  }
  return value;
}

function sha256(value) {
  return createHash("sha256").update(JSON.stringify(canonical(value))).digest("hex");
}

function requiredText(value, label) {
  const text = String(value ?? "").trim();
  if (!text) throw new Error(`${label}_REQUIRED`);
  return text;
}

function positiveFinite(value, label) {
  const number = Number(value);
  if (!Number.isFinite(number) || number <= 0) throw new Error(`${label}_REQUIRED`);
  return number;
}

function verifyShadowIntent(intent) {
  if (!intent || intent.type !== "SHADOW_ORDER_INTENT") throw new Error("SHADOW_ORDER_INTENT_REQUIRED");
  const { intentSha256, ...core } = intent;
  if (!/^[a-f0-9]{64}$/i.test(String(intentSha256 ?? "")) || sha256(core) !== intentSha256) {
    throw new Error("SHADOW_ORDER_INTENT_HASH_MISMATCH");
  }
  if (!intent.safety || typeof intent.safety !== "object") throw new Error("SHADOW_ORDER_INTENT_SAFETY_REQUIRED");
  for (const key of SOURCE_FALSE_KEYS) {
    if (intent.safety[key] !== false) throw new Error(`UNSAFE_SHADOW_INTENT:${key}`);
  }
  if (intent.futureOutcomeUsed !== false || intent.transmitted !== false || intent.executable !== false) {
    throw new Error("SHADOW_ORDER_INTENT_NOT_RESEARCH_ONLY");
  }
}

function marketReferencePrice(intent) {
  const side = String(intent.side ?? "").toUpperCase();
  const quote = side === "BUY" ? Number(intent.referenceAsk) : Number(intent.referenceBid);
  if (Number.isFinite(quote) && quote > 0) return quote;
  return positiveFinite(intent.referencePrice, "REFERENCE_PRICE");
}

/**
 * Convert one already-frozen Phase57 ShadowOrderIntent into the cash-only
 * execution contract consumed by the locked G6-G10 path.
 *
 * This adapter never chooses a Selector/Entry/Allocation candidate. It only
 * preserves the upstream decision and rejects any short/margin meaning.
 */
export function buildCashExecutionIntentFromShadowIntent(shadowIntent, {
  orderType = "MARKET",
  limitPrice = null,
  timeInForce = "DAY",
} = {}) {
  verifyShadowIntent(shadowIntent);

  const symbol = requiredText(shadowIntent.symbol, "SYMBOL").toUpperCase();
  if (!/^[0-9A-Z]{4}\.T$/.test(symbol)) throw new Error("CASH_TSE_SYMBOL_REQUIRED");

  const kind = requiredText(shadowIntent.intentKind, "INTENT_KIND").toUpperCase();
  const side = requiredText(shadowIntent.side, "SIDE").toUpperCase();
  if (kind === "ENTRY" && side !== "BUY") throw new Error("CASH_LONG_ENTRY_BUY_ONLY");
  if (kind === "EXIT" && side !== "SELL") throw new Error("CASH_LONG_EXIT_SELL_ONLY");
  if (!["ENTRY", "EXIT"].includes(kind)) throw new Error("ENTRY_OR_EXIT_REQUIRED");

  const quantity = Number(shadowIntent.requestedQuantity);
  if (!Number.isInteger(quantity) || quantity <= 0 || quantity % 100 !== 0) {
    throw new Error("CASH_100_SHARE_LOT_REQUIRED");
  }

  const normalizedOrderType = requiredText(orderType, "ORDER_TYPE").toUpperCase();
  if (!['MARKET', 'LIMIT'].includes(normalizedOrderType)) throw new Error("CASH_ORDER_TYPE_REQUIRED");
  let normalizedLimitPrice = null;
  if (normalizedOrderType === "LIMIT") normalizedLimitPrice = positiveFinite(limitPrice, "LIMIT_PRICE");
  else if (limitPrice !== null && limitPrice !== undefined) throw new Error("MARKET_LIMIT_PRICE_MUST_BE_NULL");
  if (String(timeInForce).toUpperCase() !== "DAY") throw new Error("CASH_DAY_ONLY");

  const referencePrice = marketReferencePrice(shadowIntent);
  const estimatedNotional = quantity * referencePrice;
  const sourceRequestedNotional = positiveFinite(shadowIntent.requestedNotional, "SOURCE_REQUESTED_NOTIONAL");
  const lineage = Object.freeze({
    sourceIntentId: requiredText(shadowIntent.intentId, "SOURCE_INTENT_ID"),
    sourceIntentSha256: shadowIntent.intentSha256,
    strategyId: requiredText(shadowIntent.strategyId, "STRATEGY_ID"),
    matrixCell: requiredText(shadowIntent.matrixCell, "MATRIX_CELL"),
    allocationProfile: requiredText(shadowIntent.allocationProfile, "ALLOCATION_PROFILE"),
    decisionAt: requiredText(shadowIntent.decisionAt, "DECISION_AT"),
    selectorVersion: requiredText(shadowIntent.selectorVersion, "SELECTOR_VERSION"),
    entryVersion: requiredText(shadowIntent.entryVersion, "ENTRY_VERSION"),
    exitVersion: requiredText(shadowIntent.exitVersion, "EXIT_VERSION"),
    allocationVersion: requiredText(shadowIntent.allocationVersion, "ALLOCATION_VERSION"),
    sourceEventId: requiredText(shadowIntent.sourceEventId, "SOURCE_EVENT_ID"),
    sourceSnapshotHash: requiredText(shadowIntent.sourceSnapshotHash, "SOURCE_SNAPSHOT_HASH"),
  });

  const core = {
    schemaId: CASH_EXECUTION_INTENT_SCHEMA,
    product: "CASH",
    direction: "LONG",
    symbol,
    side,
    positionEffect: kind === "ENTRY" ? "OPEN" : "CLOSE",
    quantity,
    orderType: normalizedOrderType,
    limitPrice: normalizedLimitPrice,
    timeInForce: "DAY",
    estimatedNotional,
    sourceRequestedNotional,
    referencePrice,
    lineage,
    cashOnly: true,
    marginAllowed: false,
    shortSellingAllowed: false,
    marginFallbackAllowed: false,
    executable: false,
    transmitted: false,
    safety: CASH_EXECUTION_ADAPTER_SAFETY,
  };
  return Object.freeze({ ...core, cashExecutionIntentSha256: sha256(core) });
}

export function buildLockedCashRequestFromShadowIntent(shadowIntent, {
  snapshotPath,
  externalPositions = [],
  orderType = "MARKET",
  limitPrice = null,
  timeInForce = "DAY",
} = {}) {
  const cashIntent = buildCashExecutionIntentFromShadowIntent(shadowIntent, { orderType, limitPrice, timeInForce });
  const path = requiredText(snapshotPath, "SNAPSHOT_PATH");
  return Object.freeze({
    schemaId: "ARK_CASH_LOCKED_REQUEST_V1",
    snapshotPath: path,
    intent: Object.freeze({
      symbol: cashIntent.symbol,
      direction: "LONG",
      side: cashIntent.side,
      positionEffect: cashIntent.positionEffect,
      quantity: cashIntent.quantity,
      orderType: cashIntent.orderType,
      limitPrice: cashIntent.limitPrice,
      timeInForce: cashIntent.timeInForce,
    }),
    externalPositions: Object.freeze(externalPositions.map((row) => Object.freeze({ ...row }))),
    estimatedNotional: cashIntent.estimatedNotional,
    upstreamLineage: cashIntent.lineage,
    sourceCashExecutionIntentSha256: cashIntent.cashExecutionIntentSha256,
    inspectionOnly: true,
  });
}
