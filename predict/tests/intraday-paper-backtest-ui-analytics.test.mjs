import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source =
  fs.readFileSync(
    new URL(
      "../trading/intraday-paper-backtest-ui.js",
      import.meta.url,
    ),
    "utf8",
  );

test(
  "Trade Analytics UIを読み込む",
  () => {
    assert.match(
      source,
      /from\s+"\.\/trade-analytics-ui\.js"/,
    );
  },
);

test(
  "Analytics表示rootを生成する",
  () => {
    assert.match(
      source,
      /function ensureTradeAnalyticsRoot\(/,
    );

    assert.match(
      source,
      /intraday-trade-analytics/,
    );
  },
);

test(
  "結果描画後にAnalyticsを表示する",
  () => {
    assert.match(
      source,
      /renderTradeAnalytics\(\s*result,\s*\);/,
    );
  },
);

test(
  "既存描画処理を維持する",
  () => {
    assert.match(
      source,
      /renderEquityCurve\(result\)/,
    );

    assert.match(
      source,
      /renderTrades\(result\)/,
    );

    assert.match(
      source,
      /renderWarnings\(/,
    );
  },
);
