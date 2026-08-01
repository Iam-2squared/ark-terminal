import assert from "node:assert/strict";
import test from "node:test";

import {
  analyzeIntradayMarket,
  buildIntradayCandles,
  calculateIntradayVolumeRatio,
  calculateIntradayVwapSeries,
  calculateSessionAwareVolumeRatio,
  normalizeIntradaySymbol,
  selectLatestClosedSession,
} from "../trading/intraday-market.js";

const START = 1_700_000_000;

function candle(
  index,
  overrides = {},
) {
  const close =
    overrides.close ??
    100 + index * 0.01;

  return {
    time: START + index * 900,
    open:
      overrides.open ??
      close - 0.05,
    high:
      overrides.high ??
      close + 0.2,
    low:
      overrides.low ??
      close - 0.2,
    close,
    volume:
      overrides.volume ?? 100,
    sessionDate:
      overrides.sessionDate ??
      "2026-08-01",
    isClosed:
      overrides.isClosed ?? true,
  };
}

function candles(
  count = 25,
  overrides = {},
) {
  return Array.from(
    { length: count },
    (_, index) =>
      candle(index, {
        ...overrides,
      }),
  );
}

test("日本株コードを正規化し15分足を生成する", () => {
  assert.equal(
    normalizeIntradaySymbol("7203"),
    "7203.T",
  );

  const built = buildIntradayCandles(
    {
      meta: {
        exchangeTimezoneName:
          "Asia/Tokyo",
      },
      timestamp: [
        1_700_000_000,
        1_700_000_900,
      ],
      indicators: {
        quote: [
          {
            open: [100, 101],
            high: [102, 103],
            low: [99, 100],
            close: [101, 102],
            volume: [1000, 1200],
          },
        ],
      },
    },
    {
      nowSeconds:
        1_700_000_900 + 901,
    },
  );

  assert.equal(
    built.candles.length,
    2,
  );
  assert.equal(
    built.closedRowCount,
    2,
  );
  assert.equal(
    built.candles[0].sessionDate,
    built.candles[1].sessionDate,
  );
});

test("日中VWAPを出来高加重で計算する", () => {
  const series =
    calculateIntradayVwapSeries([
      candle(0, {
        open: 100,
        high: 100,
        low: 100,
        close: 100,
        volume: 1,
      }),
      candle(1, {
        open: 110,
        high: 110,
        low: 110,
        close: 110,
        volume: 3,
      }),
    ]);

  assert.equal(
    series.at(-1).vwap,
    107.5,
  );
});

test("直近出来高を過去平均と比較する", () => {
  const rows = candles(21);

  rows.at(-1).volume = 200;

  assert.equal(
    calculateIntradayVolumeRatio(
      rows,
      20,
    ),
    2,
  );
});

test("出来高を伴う高値突破を買いセットアップにする", () => {
  const rows = candles(25);

  rows.at(-1).open = 101.5;
  rows.at(-1).low = 101.4;
  rows.at(-1).high = 103.2;
  rows.at(-1).close = 103;
  rows.at(-1).volume = 300;

  const result =
    analyzeIntradayMarket(rows, {
      nowSeconds:
        rows.at(-1).time + 901,
    });

  assert.equal(
    result.setup,
    "breakout_long",
  );
  assert.equal(
    result.direction,
    "強気",
  );
  assert.equal(
    result.volumeSurge,
    true,
  );
});

test("出来高を伴う安値下抜けを売りセットアップにする", () => {
  const rows = candles(25);

  rows.at(-1).open = 98;
  rows.at(-1).high = 98.1;
  rows.at(-1).low = 96.8;
  rows.at(-1).close = 97;
  rows.at(-1).volume = 300;

  const result =
    analyzeIntradayMarket(rows, {
      nowSeconds:
        rows.at(-1).time + 901,
    });

  assert.equal(
    result.setup,
    "breakout_short",
  );
  assert.equal(
    result.direction,
    "弱気",
  );
});

test("上昇後のVWAP付近反発を押し目候補にする", () => {
  const rows = candles(25);

  rows[20].high = 102;

  const latest = rows.at(-1);

  latest.open = 100.15;
  latest.low = 100.05;
  latest.high = 100.7;
  latest.close = 100.6;
  latest.volume = 110;

  const result =
    analyzeIntradayMarket(rows, {
      nowSeconds:
        latest.time + 901,
    });

  assert.equal(
    result.setup,
    "pullback_long",
  );
  assert.equal(
    result.direction,
    "強気",
  );
});

test("古い15分足では取引判断を停止する", () => {
  const rows = candles(25);
  const latest = rows.at(-1);

  const result =
    analyzeIntradayMarket(rows, {
      nowSeconds:
        latest.time + 900 + 5000,
    });

  assert.equal(
    result.marketBlocked,
    true,
  );
  assert.equal(
    result.setup,
    "stale_data",
  );
  assert.equal(
    result.ready,
    false,
  );
});

test("未確定足は短期判断へ使わない", () => {
  const rows = candles(25);

  rows.push(
    candle(25, {
      open: 101,
      high: 110,
      low: 100,
      close: 109,
      volume: 1000,
      isClosed: false,
    }),
  );

  const selected =
    selectLatestClosedSession(rows);

  const result =
    analyzeIntradayMarket(rows, {
      nowSeconds:
        rows.at(-2).time + 901,
    });

  assert.equal(
    selected.at(-1).time,
    rows.at(-2).time,
  );

  assert.notEqual(
    result.setup,
    "breakout_long",
  );
});

test("確定足が不足している場合はデータ待ちにする", () => {
  const rows = candles(10);

  const result =
    analyzeIntradayMarket(rows, {
      nowSeconds:
        rows.at(-1).time + 901,
    });

  assert.equal(
    result.ready,
    false,
  );
  assert.equal(
    result.setup,
    "insufficient_data",
  );
  assert.equal(
    result.direction,
    "中立",
  );
});

function createMultiSessionRows({
  currentSessionBars = 4,
  priorPrice = 90,
  currentPrice = 100,
  priorSlotVolume = 200,
  currentLatestVolume = 400,
} = {}) {
  const rows = [];
  let index = 0;

  [
    "2026-07-29",
    "2026-07-30",
    "2026-07-31",
  ].forEach((sessionDate) => {
    for (
      let slot = 0;
      slot < 7;
      slot += 1
    ) {
      const price =
        priorPrice +
        slot * 0.1;

      rows.push(
        candle(index, {
          sessionDate,
          open: price,
          high: price + 0.2,
          low: price - 0.2,
          close: price,
          volume:
            slot === 3
              ? priorSlotVolume
              : 80,
        }),
      );

      index += 1;
    }
  });

  for (
    let slot = 0;
    slot < currentSessionBars;
    slot += 1
  ) {
    const price =
      currentPrice +
      slot * 0.1;

    rows.push(
      candle(index, {
        sessionDate:
          "2026-08-01",

        open: price,
        high: price + 0.2,
        low: price - 0.2,
        close: price,

        volume:
          slot ===
            currentSessionBars - 1
            ? currentLatestVolume
            : 100,
      }),
    );

    index += 1;
  }

  return rows;
}

test("前日までの履歴があれば当日4本で判定を開始する", () => {
  const rows =
    createMultiSessionRows();

  const latest =
    rows.at(-1);

  const result =
    analyzeIntradayMarket(
      rows,
      {
        nowSeconds:
          latest.time + 901,
      },
    );

  assert.equal(
    result.ready,
    true,
  );

  assert.notEqual(
    result.setup,
    "insufficient_data",
  );

  assert.equal(
    result.sessionBarCount,
    4,
  );

  assert.equal(
    result.historyBarCount,
    25,
  );

  assert.equal(
    result.minimumSessionBars,
    4,
  );

  assert.ok(
    Number.isFinite(
      result.atr,
    ),
  );
});

test("出来高基準は過去の同じ15分枠を優先する", () => {
  const rows =
    createMultiSessionRows();

  const context =
    calculateSessionAwareVolumeRatio(
      rows,
      {
        lookbackSessions: 10,
        minimumSamples: 3,
        fallbackLookback: 20,
      },
    );

  assert.equal(
    context.source,
    "same_session_slot",
  );

  assert.equal(
    context.sampleCount,
    3,
  );

  assert.equal(
    context.baseline,
    200,
  );

  assert.equal(
    context.ratio,
    2,
  );
});

test("前日履歴が十分でも当日3本まではデータ待ちにする", () => {
  const rows =
    createMultiSessionRows({
      currentSessionBars: 3,
      currentLatestVolume: 300,
    });

  const latest =
    rows.at(-1);

  const result =
    analyzeIntradayMarket(
      rows,
      {
        nowSeconds:
          latest.time + 901,
      },
    );

  assert.equal(
    result.ready,
    false,
  );

  assert.equal(
    result.setup,
    "insufficient_data",
  );

  assert.equal(
    result.sessionBarCount,
    3,
  );

  assert.equal(
    result.historyBarCount,
    24,
  );

  assert.equal(
    result.reasons.some(
      (reason) =>
        reason.includes(
          "当日の確定済み15分足",
        ),
    ),
    true,
  );
});
