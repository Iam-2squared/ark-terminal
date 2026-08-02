import test from "node:test";
import assert from "node:assert/strict";

import {
  createTradeAnalyticsViewModel,
  renderTradeAnalyticsHtml,
  TradeAnalyticsPresenterInternals,
} from "../trading/trade-analytics-presenter.js";

test(
  "詳細分析を表示用ViewModelへ変換",
  () => {
    const viewModel =
      createTradeAnalyticsViewModel({
        tradeCount: 4,
        winCount: 2,
        lossCount: 2,
        flatCount: 0,
        winRate: 50,
        profitFactor: 1.5,
        expectancy: 125,
        payoffRatio: 1.5,
        averageWin: 750,
        averageLoss: -500,
        maximumWin: 1_000,
        maximumLoss: -600,
        averageHoldingBars: 4.5,
        averageMfePercent: 1.2,
        averageMaePercent: -0.8,
        grossPnlBeforeCosts: 800,
        totalTradingCost: 300,
        totalNetPnl: 500,
        costDragPercent: 37.5,
        byExitReason: {
          target: {
            count: 2,
            winCount: 2,
            winRate: 100,
            totalNetPnl: 1_500,
            averageNetPnl: 750,
            averageHoldingBars: 5,
          },
          stop: {
            count: 2,
            winCount: 0,
            winRate: 0,
            totalNetPnl: -1_000,
            averageNetPnl: -500,
            averageHoldingBars: 4,
          },
        },
      });

    assert.equal(
      viewModel.status,
      "ready",
    );

    assert.equal(
      viewModel.summary.headline,
      "4件中 2勝 2敗",
    );

    assert.equal(
      viewModel.summary.diagnosis,
      "1取引期待値はプラスです。",
    );

    assert.equal(
      viewModel.exitReasons.length,
      2,
    );

    const expectancyCard =
      viewModel.cards.find(
        (card) =>
          card.id ===
          "expectancy",
      );

    assert.equal(
      expectancyCard.value,
      "+¥125",
    );

    assert.equal(
      expectancyCard.tone,
      "positive",
    );
  },
);

test(
  "取引0件ではデータ待ち表示",
  () => {
    const viewModel =
      createTradeAnalyticsViewModel({
        tradeCount: 0,
      });

    assert.equal(
      viewModel.status,
      "empty",
    );

    assert.equal(
      viewModel.statusLabel,
      "取引データ待ち",
    );

    assert.equal(
      viewModel.summary.headline,
      "確定取引がありません",
    );
  },
);

test(
  "HTMLに主要指標と決済理由を出力",
  () => {
    const html =
      renderTradeAnalyticsHtml({
        tradeCount: 2,
        winCount: 1,
        lossCount: 1,
        winRate: 50,
        expectancy: -100,
        payoffRatio: 0.8,
        averageWin: 400,
        averageLoss: -600,
        totalTradingCost: 50,
        totalNetPnl: -200,
        byExitReason: {
          stop: {
            count: 1,
            winCount: 0,
            winRate: 0,
            totalNetPnl: -600,
            averageNetPnl: -600,
            averageHoldingBars: 3,
          },
        },
      });

    assert.match(
      html,
      /売買損益分析/,
    );

    assert.match(
      html,
      /1取引期待値/,
    );

    assert.match(
      html,
      /平均損益比/,
    );

    assert.match(
      html,
      /総取引コスト/,
    );

    assert.match(
      html,
      /決済理由別成績/,
    );

    assert.match(
      html,
      /stop/,
    );
  },
);

test(
  "HTML特殊文字をエスケープ",
  () => {
    const escaped =
      TradeAnalyticsPresenterInternals
        .escapeHtml(
          '<script>"x"</script>',
        );

    assert.equal(
      escaped,
      "&lt;script&gt;&quot;x&quot;&lt;/script&gt;",
    );
  },
);

test(
  "符号付き通貨表示",
  () => {
    const internals =
      TradeAnalyticsPresenterInternals;

    assert.equal(
      internals
        .formatSignedCurrency(
          1_250,
        ),
      "+¥1,250",
    );

    assert.equal(
      internals
        .formatSignedCurrency(
          -800,
        ),
      "-¥800",
    );

    assert.equal(
      internals
        .formatSignedCurrency(
          0,
        ),
      "¥0",
    );
  },
);