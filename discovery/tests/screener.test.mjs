import assert from "node:assert/strict";
import test from "node:test";

import { evaluateAlertCandidates } from "../alerts.js";
import { buildScreenerEntry } from "../engine.js";
import {
  applyScreenerFilters,
  FilteringInternals,
} from "../filtering.js";
import {
  loadAlertSettings,
  loadWatchlist,
  saveAlertSettings,
  toggleWatchlist,
} from "../storage.js";
import { ScreenerApiInternals } from "../../api/screener.js";

function memoryStorage() {
  const values = new Map();

  return {
    getItem(key) {
      return values.has(key) ? values.get(key) : null;
    },
    setItem(key, value) {
      values.set(key, String(value));
    },
    removeItem(key) {
      values.delete(key);
    },
  };
}

function syntheticHistory(symbol = "7203.T", count = 520) {
  const candles = [];
  const start = 1_700_000_000;

  for (let index = 0; index < count; index += 1) {
    const trend = 1000 + index * 1.2;
    const wave = Math.sin(index / 8) * 14;
    const close = trend + wave;
    const open = close - Math.sin(index / 5) * 4;
    const high = Math.max(open, close) + 9;
    const low = Math.min(open, close) - 9;

    candles.push({
      time: start + index * 86_400,
      open,
      high,
      low,
      close,
      volume: 1_000_000 + (index % 20) * 20_000,
      rawClose: close,
      adjustedClose: close,
      adjustedCloseProvided: true,
      adjustmentFactor: 1,
      volumeAdjustmentFactor: 1,
    });
  }

  return {
    symbol,
    provider: "test",
    adjustmentMethod: "adjusted-close-price-and-split-adjusted-volume",
    meta: {
      currency: "JPY",
      priceUnit: "JPY",
      volumeUnit: "shares",
    },
    sourceQuality: {
      sourceRowCount: count,
      droppedRowCount: 0,
      adjustedCloseCount: count,
      splitCount: 0,
    },
    corporateActions: {
      splits: [],
    },
    candles,
  };
}

test("Prediction Lab共通ロジックからランキング行を生成する", () => {
  const entry = buildScreenerEntry({
    history: syntheticHistory(),
    metadata: {
      code: "7203",
      name: "テスト自動車",
      market: "プライム",
      sector: "輸送用機器",
      themes: ["自動車"],
      lotSize: 100,
    },
  });

  assert.equal(entry.status, "analyzed");
  assert.equal(entry.symbol, "7203.T");
  assert.ok(entry.aiScore >= 0 && entry.aiScore <= 100);
  assert.ok(entry.confidence >= 0 && entry.confidence <= 100);
  assert.ok(entry.expectedMove > 0);
  assert.equal(entry.purchaseAmount, entry.currentPrice * 100);
  assert.ok(entry.reasons.length > 0);
});

test("価格帯の上限は次の帯と重複しない", () => {
  assert.equal(
    FilteringInternals.inBand(299.99, {
      minimum: 0,
      maximum: 300,
    }),
    true,
  );
  assert.equal(
    FilteringInternals.inBand(300, {
      minimum: 0,
      maximum: 300,
    }),
    false,
  );
});

test("discoveryScore uses decimal precision and sorts deterministically with tie-breakers", () => {
  const entries = [
    {
      symbol: "AAA.T",
      status: "analyzed",
      discoveryScore: 74.12,
      confidence: 70,
      volumeRatio: 1.3,
      riskLevel: 2,
      currentPrice: 1000,
      purchaseAmount: 100000,
      marketCap: 2000000000,
    },
    {
      symbol: "BBB.T",
      status: "analyzed",
      discoveryScore: 74.11,
      confidence: 80,
      volumeRatio: 1.2,
      riskLevel: 1,
      currentPrice: 1000,
      purchaseAmount: 100000,
      marketCap: 2000000000,
    },
    {
      symbol: "CCC.T",
      status: "analyzed",
      discoveryScore: 74.12,
      confidence: 70,
      volumeRatio: 1.1,
      riskLevel: 1,
      currentPrice: 1000,
      purchaseAmount: 100000,
      marketCap: 2000000000,
    },
  ];

  const result = applyScreenerFilters(entries, {
    priceBand: "all",
    market: "all",
    theme: "all",
    marketCap: "all",
    risk: "all",
    sort: "scoreDesc",
  });

  assert.deepEqual(result.map((entry) => entry.symbol), [
    "AAA.T",
    "CCC.T",
    "BBB.T",
  ]);
  assert.equal(result[0].discoveryScore, 74.12);
  assert.equal(result[1].discoveryScore, 74.12);
  assert.equal(result[2].discoveryScore, 74.11);
});

test("価格帯を指定しない場合は分析済み銘柄を除外しない", () => {
  const entries = [
    {
      symbol: "7203.T",
      status: "analyzed",
      market: "プライム",
      sector: "輸送用機器",
      themes: ["自動車"],
      currentPrice: 3000,
      purchaseAmount: 300_000,
      marketCap: null,
      aiScore: 65,
      confidence: 60,
      volumeRatio: 1.1,
      risk: "中",
    },
  ];

  const result = applyScreenerFilters(entries, {
    priceBand: "all",
    market: "all",
    theme: "all",
    marketCap: "all",
    risk: "all",
    sort: "scoreDesc",
  });

  assert.equal(result.length, 1);
});

test("予算・市場・テーマ・出来高・信頼度を同時に絞り込める", () => {
  const entries = [
    {
      symbol: "1111.T",
      status: "analyzed",
      market: "グロース",
      sector: "情報・通信業",
      themes: ["AI"],
      currentPrice: 250,
      purchaseAmount: 25_000,
      marketCap: 20_000_000_000,
      aiScore: 72,
      confidence: 61,
      volumeRatio: 1.8,
      risk: "中",
    },
    {
      symbol: "2222.T",
      status: "analyzed",
      market: "プライム",
      sector: "情報・通信業",
      themes: ["AI"],
      currentPrice: 250,
      purchaseAmount: 25_000,
      marketCap: 20_000_000_000,
      aiScore: 80,
      confidence: 75,
      volumeRatio: 2.1,
      risk: "低",
    },
  ];
  const result = applyScreenerFilters(entries, {
    market: "グロース",
    theme: "AI",
    priceBand: "under300",
    budget: 30_000,
    marketCap: "small",
    minimumScore: 70,
    minimumConfidence: 55,
    minimumVolumeRatio: 1.5,
    risk: "中",
  });

  assert.deepEqual(
    result.map((entry) => entry.symbol),
    ["1111.T"],
  );
});

test("ウォッチリストを追加・削除できる", () => {
  const storage = memoryStorage();

  assert.equal(loadWatchlist(storage).size, 0);
  assert.equal(toggleWatchlist("7203.T", storage).has("7203.T"), true);
  assert.equal(toggleWatchlist("7203.T", storage).has("7203.T"), false);
});

test("通知条件を範囲内に正規化して保存する", () => {
  const storage = memoryStorage();

  saveAlertSettings(
    {
      enabled: true,
      minimumScore: 150,
      minimumConfidence: -4,
      watchlistOnly: true,
      cooldownHours: 0,
    },
    storage,
  );

  assert.deepEqual(loadAlertSettings(storage), {
    enabled: true,
    minimumScore: 100,
    minimumConfidence: 0,
    watchlistOnly: true,
    cooldownHours: 1,
  });
});

test("通知は閾値・ウォッチ・クールダウンをすべて満たす時だけ候補になる", () => {
  const now = 2_000_000_000_000;
  const entries = [
    {
      symbol: "7203.T",
      status: "analyzed",
      aiScore: 75,
      confidence: 65,
    },
    {
      symbol: "285A.T",
      status: "analyzed",
      aiScore: 80,
      confidence: 70,
    },
  ];
  const candidates = evaluateAlertCandidates({
    entries,
    settings: {
      enabled: true,
      minimumScore: 70,
      minimumConfidence: 60,
      watchlistOnly: true,
      cooldownHours: 12,
    },
    watchlist: new Set(["7203.T", "285A.T"]),
    history: {
      "285A.T": {
        notifiedAt: now - 1_000,
      },
    },
    now,
  });

  assert.deepEqual(
    candidates.map((entry) => entry.symbol),
    ["7203.T"],
  );
});

test("スキャンAPIは日本株表記を正規化し6銘柄までに制限する", () => {
  assert.deepEqual(
    ScreenerApiInternals.parseSymbols(
      "7203,285A,7203.T,NVDA,6758,9984,8035,6857",
    ),
    ["7203.T", "285A.T", "NVDA", "6758.T", "9984.T", "8035.T"],
  );
});
