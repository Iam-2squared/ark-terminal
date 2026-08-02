const test =
  require("node:test");

const assert =
  require("node:assert/strict");

const {
  createAiIntelligenceService,
} = require(
  "../../api/ai-intelligence/service.js"
);

test(
  "AI intelligence produces safe advisory decision",
  () => {
    const service =
      createAiIntelligenceService();

    const result =
      service.analyze({
        symbol: "7203.T",
        technicalScore: 82,
        fundamentalScore: 70,
        marketScore: 75,
        newsScore: 65,
        portfolioFit: 80,
        liquidityScore: 90,
        dataQuality: 95,
        freshness: 95,
        volatilityRisk: 25,
        drawdownRisk: 20,
        eventRisk: 20,
        concentrationRisk: 25,
      });

    assert.equal(
      result.decision.action,
      "WATCH_BUY"
    );

    assert.equal(
      result.orderSubmissionAllowed,
      false
    );

    assert.equal(
      result.policy.humanApprovalRequired,
      true
    );
  }
);

test(
  "Critical risk blocks recommendation",
  () => {
    const service =
      createAiIntelligenceService();

    const result =
      service.analyze({
        technicalScore: 90,
        fundamentalScore: 90,
        marketScore: 90,
        newsScore: 90,
        portfolioFit: 90,
        liquidityScore: 90,
        dataQuality: 95,
        freshness: 95,
        volatilityRisk: 100,
        drawdownRisk: 100,
        eventRisk: 100,
        concentrationRisk: 100,
      });

    assert.equal(
      result.risk.level,
      "critical"
    );

    assert.equal(
      result.policy.recommendationAllowed,
      false
    );

    assert.equal(
      result.decision.action,
      "REVIEW"
    );
  }
);

test(
  "AI analysis history is stored",
  () => {
    const service =
      createAiIntelligenceService();

    service.analyze({});

    assert.equal(
      service.getHistory().length,
      1
    );

    assert.ok(
      service.getLatest()
    );
  }
);