import assert from "node:assert/strict";
import test from "node:test";

import {
  PHASE57_MSII_ORDER_STYLE,
  createShadowOrderIntent,
  normalizeMarketSpeedReadOnlyEvent,
} from "../realtime/phase57-msii-shadow-execution.js";
import {
  buildCashExecutionIntentFromShadowIntent,
  buildCashExecutionIntentsFromCommittedLedger,
  buildLockedCashRequestFromShadowIntent,
} from "../realtime/phase57-cash-execution-adapter.js";

const AT = "2026-09-03T00:35:00.000Z";
const SAFE = Object.freeze({
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  transmitted: false,
});

function event(symbol = "7203") {
  return normalizeMarketSpeedReadOnlyEvent({
    schemaVersion: 2,
    phase: "58.p9.sync-capture",
    sourceMode: "MARKETSPEED_II_RSS_READ_ONLY",
    capturedAt: AT,
    symbol,
    sourceFunctions: ["RssMarket", "RssTickList"],
    market: { bestBid: 100, bestAsk: 100.2, bestBidSize: 500, bestAskSize: 500 },
    ticks: [],
    phase57Snapshot: {
      direction: 1,
      asOf: AT,
      modelId: "phase57-frozen-fixture",
      artifactSha256: "a".repeat(64),
      frozen: true,
      futureOutcomeUsed: false,
      thresholdSearchAfterCapture: false,
      entryRetunedAfterCapture: false,
    },
    methodology: {
      phase57DirectionIsFrozenBase: true,
      phase58MayConfirmDeferOrAbstainOnly: true,
      phase58MayReverseDirection: false,
      pointInTimeOnly: true,
      sameCaptureBoundary: true,
      futureOutcomeUsed: false,
      historicalDecisionReconstructionAllowed: false,
    },
    safety: SAFE,
  }, { marketSizeUnit: "SHARES", tickSizeUnit: "SHARES" });
}

function shadow({ side = "BUY", intentKind = "ENTRY", requestedQuantity = 500, strategyId = "V1_V3__MAX_3", decisionSequence = 0 } = {}) {
  const referenceEvent = event();
  return createShadowOrderIntent({
    strategyId,
    symbol: "7203",
    side,
    intentKind,
    decisionAt: AT,
    decisionSequence,
    requestedQuantity,
    referencePrice: 100.1,
    referenceEvent,
    orderStyleResearchLabel: PHASE57_MSII_ORDER_STYLE.MARKETABLE_QUOTE,
    ttlMs: 5_000,
    decisionLatencyMs: 100,
    selectorVersion: "SELECTOR_FROZEN",
    entryVersion: "ENTRY_FROZEN",
    exitVersion: "EXIT_FROZEN",
    allocationVersion: "ALLOCATION_FROZEN",
    futureOutcomeUsed: false,
  });
}

test("adapts a frozen LONG entry without re-choosing Selector/Entry/Allocation", () => {
  const source = shadow();
  const out = buildCashExecutionIntentFromShadowIntent(source);
  assert.equal(out.product, "CASH");
  assert.equal(out.direction, "LONG");
  assert.equal(out.symbol, "7203.T");
  assert.equal(out.side, "BUY");
  assert.equal(out.positionEffect, "OPEN");
  assert.equal(out.quantity, 500);
  assert.equal(out.estimatedNotional, 50_100, "BUY cash check must use the causal ask when available");
  assert.equal(out.sourceRequestedNotional, 50_050);
  assert.equal(out.lineage.strategyId, "V1_V3__MAX_3");
  assert.equal(out.lineage.sourceIntentSha256, source.intentSha256);
  assert.equal(out.marginAllowed, false);
  assert.equal(out.shortSellingAllowed, false);
  assert.equal(out.executable, false);
  assert.equal(out.transmitted, false);
  assert.match(out.cashExecutionIntentSha256, /^[a-f0-9]{64}$/);
});

test("adapts only a LONG cash exit SELL and rejects short semantics", () => {
  const exit = buildCashExecutionIntentFromShadowIntent(shadow({ side: "SELL", intentKind: "EXIT" }));
  assert.equal(exit.side, "SELL");
  assert.equal(exit.positionEffect, "CLOSE");
  assert.equal(exit.estimatedNotional, 50_000, "SELL reference uses causal bid when available");

  assert.throws(
    () => buildCashExecutionIntentFromShadowIntent(shadow({ side: "SELL", intentKind: "ENTRY" })),
    /CASH_LONG_ENTRY_BUY_ONLY/,
  );
  assert.throws(
    () => buildCashExecutionIntentFromShadowIntent(shadow({ side: "BUY", intentKind: "EXIT" })),
    /CASH_LONG_EXIT_SELL_ONLY/,
  );
});

test("requires explicit strategy lineage when extracting committed realtime intents", () => {
  const first = shadow({ decisionSequence: 2 });
  const other = shadow({ strategyId: "V1_V3__MAX_2", decisionSequence: 1 });
  const ledger = [
    { eventType: "SHADOW_ORDER_INTENT_COMMITTED", intent: first },
    { eventType: "SHADOW_ORDER_INTENT_COMMITTED", intent: other },
  ];
  assert.throws(() => buildCashExecutionIntentsFromCommittedLedger(ledger), /STRATEGY_ID_REQUIRED/);
  const selected = buildCashExecutionIntentsFromCommittedLedger(ledger, { strategyId: "V1_V3__MAX_3", decisionAt: AT });
  assert.equal(selected.length, 1);
  assert.equal(selected[0].lineage.strategyId, "V1_V3__MAX_3");
  assert.equal(selected[0].quantity, 500);

  const shortForSelected = shadow({ side: "SELL", intentKind: "ENTRY", decisionSequence: 3 });
  const mixed = [...ledger, { eventType: "SHADOW_ORDER_INTENT_COMMITTED", intent: shortForSelected }];
  assert.throws(
    () => buildCashExecutionIntentsFromCommittedLedger(mixed, { strategyId: "V1_V3__MAX_3" }),
    /CASH_LONG_ENTRY_BUY_ONLY/,
    "a short in the explicitly selected strategy must block rather than be silently dropped",
  );
});

test("rejects tampered upstream intent and preserves typed request lineage", () => {
  const source = shadow();
  assert.throws(
    () => buildCashExecutionIntentFromShadowIntent({ ...source, requestedQuantity: 100 }),
    /SHADOW_ORDER_INTENT_HASH_MISMATCH/,
  );

  const request = buildLockedCashRequestFromShadowIntent(source, {
    snapshotPath: "C:/Ark/account-snapshot-live.json",
    externalPositions: [{ symbol: "408A", quantity: 180 }],
  });
  assert.equal(request.schemaId, "ARK_CASH_LOCKED_REQUEST_V1");
  assert.equal(request.intent.symbol, "7203.T");
  assert.equal(request.intent.direction, "LONG");
  assert.equal(request.intent.side, "BUY");
  assert.equal(request.intent.positionEffect, "OPEN");
  assert.equal(request.intent.quantity, 500);
  assert.equal(request.estimatedNotional, 50_100);
  assert.equal(request.upstreamLineage.sourceIntentSha256, source.intentSha256);
  assert.equal(request.inspectionOnly, true);
});
