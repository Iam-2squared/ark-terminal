import assert from "node:assert/strict";
import test from "node:test";
import { buildPhase57MsiiDynamicWatchlist, PHASE57_MSII_DYNAMIC_WATCHLIST_SAFETY } from "../realtime/phase57-msii-dynamic-watchlist.js";

function snapshot(at = "2026-09-04T00:05:00.000Z") {
  return {
    meta: { observedAt: at },
    entries: Array.from({ length: 3200 }, (_, i) => ({
      symbol: `${1000 + i}.T`,
      sector: `S${i % 40}`,
      status: "analyzed",
      currentPrice: 100 + (i % 500),
      volume: 100000 + i * 100,
      volumeRatio: 1 + (i % 20) / 10,
      dailyChangePercent: ((i % 31) - 15) / 4,
      atrPercent: 1 + (i % 12) / 4,
      discoveryScore: 40 + (i % 21),
      technicalScore: 40 + ((i * 3) % 21),
      confidence: 0.5 + (i % 40) / 100,
      qualityScore: 50 + (i % 45),
    })),
  };
}

test("dynamic watchlist uses frozen V1/V2 selection and fits the current 50 in slots", () => {
  const result = buildPhase57MsiiDynamicWatchlist({ snapshot: snapshot(), slotCount: 80, retentionPoints: 3 });
  assert.equal(result.complete, true);
  assert.equal(result.currentV1Symbols.length, 50);
  assert.equal(result.currentV2Symbols.length, 30);
  assert.ok(result.currentV2Symbols.every((symbol) => result.currentV1Symbols.includes(symbol)));
  assert.ok(result.assignedSymbols.length <= 80);
  assert.equal(result.methodology.laterYahooBarUsed, false);
  assert.equal(result.futureOutcomeUsed, false);
});

test("pinned Lane M inventory is hard-required and retention is best-effort only", () => {
  const first = buildPhase57MsiiDynamicWatchlist({ snapshot: snapshot(), slotCount: 80, retentionPoints: 3 });
  const second = buildPhase57MsiiDynamicWatchlist({
    snapshot: snapshot("2026-09-04T00:10:00.000Z"),
    slotCount: 80,
    retentionPoints: 3,
    priorV2Selections: first.v2PriorSelectionsNext,
    recentV1Selections: first.recentV1SelectionsNext,
    pinnedSymbols: ["7203.T", "8306.T"],
  });
  assert.equal(second.complete, true);
  assert.ok(second.assignedSymbols.includes("7203.T"));
  assert.ok(second.assignedSymbols.includes("8306.T"));
  assert.ok(second.assignedSymbols.length <= 80);
});

test("hard-required symbols fail closed instead of silently truncating", () => {
  const pinned = Array.from({ length: 40 }, (_, i) => `${7000 + i}.T`);
  const result = buildPhase57MsiiDynamicWatchlist({ snapshot: snapshot(), slotCount: 50, pinnedSymbols: pinned });
  assert.equal(result.complete, false);
  assert.equal(result.status, "BLOCKED_DYNAMIC_SLOT_CAPACITY");
  assert.ok(result.overflowRequiredSymbols.length > 0);
  assert.deepEqual(result.assignedSymbols, []);
});

test("dynamic watchlist keeps order/trading safety false while market-data query writes are explicitly scoped", () => {
  for (const key of ["executionAllowed","brokerWriteAllowed","excelOrderWriteAllowed","rssOrderFunctionAllowed","liveTradingAllowed","paperTradingAllowed","automaticPromotionAllowed","productionUpdateAllowed"]) {
    assert.equal(PHASE57_MSII_DYNAMIC_WATCHLIST_SAFETY[key], false);
  }
  assert.equal(PHASE57_MSII_DYNAMIC_WATCHLIST_SAFETY.excelMarketDataQueryWriteAllowed, true);
});
