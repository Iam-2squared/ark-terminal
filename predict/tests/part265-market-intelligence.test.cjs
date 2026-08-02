const test =
  require("node:test");

const assert =
  require("node:assert/strict");

const {
  createMarketIntelligenceService,
} =
  require(
    "../../server/market-intelligence/service.js",
  );

test(
  "強気市場を判定",
  () => {
    const service =
      createMarketIntelligenceService();

    const result =
      service.analyze({
        trendScore:
          80,

        breadthScore:
          60,

        momentumScore:
          70,

        volumeScore:
          50,

        newsScore:
          40,

        atrPercent:
          1,

        realizedVolatility:
          12,

        volatilityIndex:
          15,
      });

    assert.equal(
      result.regime.regime,
      "bull",
    );

    assert.equal(
      result.orderSubmissionAllowed,
      false,
    );
  },
);

test(
  "高ボラ弱気市場をRisk-off判定",
  () => {
    const service =
      createMarketIntelligenceService();

    const result =
      service.analyze({
        trendScore:
          -80,

        breadthScore:
          -70,

        momentumScore:
          -70,

        volumeScore:
          -30,

        newsScore:
          -60,

        atrPercent:
          5,

        realizedVolatility:
          45,

        volatilityIndex:
          40,
      });

    assert.equal(
      result.regime.regime,
      "risk_off",
    );

    assert.ok(
      [
        "high",
        "critical",
      ].includes(
        result.risk.level,
      ),
    );
  },
);

test(
  "市場分析履歴を保存",
  () => {
    const service =
      createMarketIntelligenceService();

    service.analyze({});

    assert.equal(
      service
        .getHistory()
        .length,
      1,
    );

    assert.ok(
      service.getLatest(),
    );
  },
);