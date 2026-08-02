import test from "node:test";
import assert from "node:assert/strict";

import {
  clearTradeAnalytics,
  createTradeAnalyticsRoot,
  findTradeAnalyticsRoot,
  mountBacktestTradeAnalytics,
  mountTradeAnalytics,
  mountTradeAnalyticsById,
  resolveAnalyticsFromBacktestModes,
} from "../trading/trade-analytics-ui.js";

function createRoot() {
  return {
    innerHTML: "",
    dataset: {},
  };
}

test(
  "分析HTMLをrootへ描画",
  () => {
    const root =
      createRoot();

    const result =
      mountTradeAnalytics({
        root,
        analytics: {
          tradeCount: 2,
          winCount: 1,
          lossCount: 1,
          winRate: 50,
          expectancy: 100,
          averageWin: 500,
          averageLoss: -300,
        },
      });

    assert.equal(
      result.mounted,
      true,
    );

    assert.match(
      root.innerHTML,
      /売買損益分析/,
    );

    assert.match(
      root.innerHTML,
      /1取引期待値/,
    );

    assert.equal(
      root.dataset.mounted,
      "true",
    );
  },
);

test(
  "rootが無ければ安全に終了",
  () => {
    const result =
      mountTradeAnalytics({
        root: null,
        analytics: {},
      });

    assert.deepEqual(
      result,
      {
        mounted: false,
        reason:
          "missing_root",
        root: null,
        html: "",
      },
    );
  },
);

test(
  "rootをクリア",
  () => {
    const root =
      createRoot();

    root.innerHTML =
      "<p>test</p>";

    assert.equal(
      clearTradeAnalytics({
        root,
      }),
      true,
    );

    assert.equal(
      root.innerHTML,
      "",
    );

    assert.equal(
      root.dataset.mounted,
      "false",
    );
  },
);

test(
  "Signal分析を優先して解決",
  () => {
    const signalAnalytics = {
      tradeCount: 5,
    };

    const executableAnalytics = {
      tradeCount: 2,
    };

    const resolved =
      resolveAnalyticsFromBacktestModes({
        signal: {
          analytics:
            signalAnalytics,
        },
        executable: {
          analytics:
            executableAnalytics,
        },
      });

    assert.equal(
      resolved,
      signalAnalytics,
    );
  },
);

test(
  "Executable指定時は実行可能モードを使用",
  () => {
    const executableAnalytics = {
      tradeCount: 3,
    };

    const resolved =
      resolveAnalyticsFromBacktestModes(
        {
          signal: {
            analytics: {
              tradeCount: 8,
            },
          },
          executable: {
            analytics:
              executableAnalytics,
          },
        },
        {
          preferredMode:
            "executable",
        },
      );

    assert.equal(
      resolved,
      executableAnalytics,
    );
  },
);

test(
  "Backtest Modes結果をrootへ描画",
  () => {
    const root =
      createRoot();

    const result =
      mountBacktestTradeAnalytics({
        root,
        result: {
          signal: {
            analytics: {
              tradeCount: 1,
              winCount: 1,
              lossCount: 0,
              winRate: 100,
              expectancy: 500,
              averageWin: 500,
            },
          },
        },
      });

    assert.equal(
      result.mounted,
      true,
    );

    assert.match(
      root.innerHTML,
      /1件中 1勝 0敗/,
    );
  },
);

test(
  "documentからrootを検索",
  () => {
    const expected =
      createRoot();

    const documentRef = {
      getElementById(id) {
        return id ===
          "intraday-trade-analytics"
          ? expected
          : null;
      },
    };

    assert.equal(
      findTradeAnalyticsRoot({
        documentRef,
      }),
      expected,
    );
  },
);

test(
  "ID指定で分析を描画",
  () => {
    const root =
      createRoot();

    const documentRef = {
      getElementById() {
        return root;
      },
    };

    const result =
      mountTradeAnalyticsById({
        documentRef,
        analytics: {
          tradeCount: 0,
        },
      });

    assert.equal(
      result.mounted,
      true,
    );

    assert.match(
      root.innerHTML,
      /確定取引がありません/,
    );
  },
);

test(
  "root要素を新規作成",
  () => {
    const children = [];

    const parent = {
      appendChild(node) {
        children.push(node);
      },
    };

    const documentRef = {
      getElementById() {
        return null;
      },

      createElement() {
        return {
          id: "",
          dataset: {},
          innerHTML: "",
        };
      },
    };

    const root =
      createTradeAnalyticsRoot({
        documentRef,
        parent,
      });

    assert.equal(
      root.id,
      "intraday-trade-analytics",
    );

    assert.equal(
      children.length,
      1,
    );

    assert.equal(
      root.dataset.component,
      "trade-analytics",
    );
  },
);