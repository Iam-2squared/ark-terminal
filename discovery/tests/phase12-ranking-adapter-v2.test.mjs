import test from "node:test";
import assert from "node:assert/strict";

import {
  rankDiscoveryEntry,
  rankDiscoveryEntries,
} from "../ranking-adapter-v2.js";
import {
  createDiscoveryFinalView,
  toggleWatchlistSymbol,
} from "../discovery-final-v1.js";

test("ranking adapter applies confidence, risk, market and sector adjustments", () => {
  const ranked = rankDiscoveryEntry(
    {
      symbol: "7203.T",
      status: "analyzed",
      discoveryScore: 70,
      confidence: 80,
      riskLevel: 1,
      direction: "up",
      sector: "自動車",
    },
    {
      marketRegime: "bull",
      sectorScores: { 自動車: 2 },
    },
  );

  assert.equal(ranked.rankingScore, 81.4);
  assert.equal(ranked.rankingAdjustments.risk, 3);
  assert.equal(ranked.rankingAdjustments.marketRegime, 4);
  assert.equal(ranked.rankingAdjustments.sector, 2);
  assert.equal(ranked.rankingReasons.length, 5);
});

test("ranking remains deterministic for equal scores", () => {
  const ranked = rankDiscoveryEntries([
    { symbol: "B", discoveryScore: 50 },
    { symbol: "A", discoveryScore: 50 },
  ]);
  assert.deepEqual(ranked.map((entry) => entry.symbol), ["A", "B"]);
});

test("discovery final reuses filters and watchlist without mutating input", () => {
  const watchlist = new Set(["A"]);
  const result = createDiscoveryFinalView({
    entries: [
      { symbol: "A", status: "analyzed", discoveryScore: 70, confidence: 80, currentPrice: 100, purchaseAmount: 10000 },
      { symbol: "B", status: "analyzed", discoveryScore: 60, confidence: 70, currentPrice: 120, purchaseAmount: 12000 },
    ],
    filters: { watchlistOnly: true, sort: "scoreDesc" },
    watchlist,
  });

  assert.equal(result.visibleCount, 1);
  assert.equal(result.entries[0].symbol, "A");
  const next = toggleWatchlistSymbol(watchlist, "B");
  assert.equal(watchlist.has("B"), false);
  assert.equal(next.has("B"), true);
});
