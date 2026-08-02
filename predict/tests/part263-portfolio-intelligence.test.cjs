const test =
  require("node:test");

const assert =
  require("node:assert/strict");

const {
  createPortfolioService,
} =
  require(
    "../../api/portfolio/service.js",
  );

test(
  "Portfolio Serviceが評価を生成",
  () => {
    const service =
      createPortfolioService();

    const report =
      service.analyze([
        {
          symbol:
            "AAA",

          quantity:
            100,

          averagePrice:
            100,

          currentPrice:
            120,
        },
        {
          symbol:
            "BBB",

          quantity:
            100,

          averagePrice:
            100,

          currentPrice:
            90,
        },
      ]);

    assert.equal(
      report
        .environment
        .runtime
        .status,
      "ready",
    );

    assert.equal(
      report
        .result
        .orderSubmissionAllowed,
      false,
    );

    assert.equal(
      report
        .liveTradingAllowed,
      false,
    );
  },
);

test(
  "集中ポートフォリオを検知",
  () => {
    const service =
      createPortfolioService();

    const report =
      service.analyze([
        {
          symbol:
            "AAA",

          quantity:
            100,

          averagePrice:
            100,

          currentPrice:
            100,
        },
        {
          symbol:
            "BBB",

          quantity:
            1,

          averagePrice:
            100,

          currentPrice:
            100,
        },
      ]);

    assert.equal(
      report
        .result
        .reasons
        .includes(
          "extreme_concentration",
        ),
      true,
    );
  },
);

test(
  "Portfolio履歴を保存",
  () => {
    const service =
      createPortfolioService();

    service.analyze([]);

    assert.equal(
      service
        .getHistory()
        .length,
      1,
    );

    assert.ok(
      service.latest(),
    );
  },
);