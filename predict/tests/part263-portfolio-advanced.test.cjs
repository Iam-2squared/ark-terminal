const test =
  require("node:test");

const assert =
  require("node:assert/strict");

const {
  calculateSectorExposure,
} =
  require(
    "../../server/portfolio/sector-exposure.js",
  );

const {
  calculateDiversificationScore,
} =
  require(
    "../../server/portfolio/diversification.js",
  );

const {
  analyzeDrawdown,
} =
  require(
    "../../server/portfolio/drawdown.js",
  );

const {
  createPortfolioIntelligenceReport,
} =
  require(
    "../../server/portfolio/report.js",
  );

const holdings = [
  {
    symbol:
      "AAA",

    sector:
      "Technology",

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

    sector:
      "Finance",

    quantity:
      100,

    averagePrice:
      100,

    currentPrice:
      100,
  },
];

test(
  "セクター比率を計算",
  () => {
    const result =
      calculateSectorExposure(
        holdings,
      );

    assert.equal(
      result.sectors.length,
      2,
    );

    assert.equal(
      Math.round(
        result.sectors.reduce(
          (total, sector) =>
            total +
            sector.weightPercent,
          0,
        ),
      ),
      100,
    );
  },
);

test(
  "分散スコアを生成",
  () => {
    const result =
      calculateDiversificationScore(
        holdings,
      );

    assert.equal(
      Number.isFinite(
        result.score,
      ),
      true,
    );

    assert.ok(
      result.score >= 0 &&
      result.score <= 100,
    );
  },
);

test(
  "最大ドローダウンを計算",
  () => {
    const result =
      analyzeDrawdown([
        100,
        120,
        90,
        110,
      ]);

    assert.equal(
      result
        .maximumDrawdownPercent,
      -25,
    );

    assert.equal(
      result.peakValue,
      120,
    );

    assert.equal(
      result.troughValue,
      90,
    );
  },
);

test(
  "高度Portfolioレポートは発注不可",
  () => {
    const report =
      createPortfolioIntelligenceReport({
        holdings,

        returns: [
          1,
          -0.5,
          0.8,
        ],

        values: [
          100,
          105,
          102,
          110,
        ],
      });

    assert.equal(
      report.simulationOnly,
      true,
    );

    assert.equal(
      report.liveTradingAllowed,
      false,
    );

    assert.equal(
      report.orderSubmissionAllowed,
      false,
    );

    assert.ok(
      report.diversification,
    );

    assert.ok(
      report.performance,
    );

    assert.ok(
      report.rebalance,
    );
  },
);