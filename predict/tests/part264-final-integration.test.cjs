const test =
  require("node:test");

const assert =
  require("node:assert/strict");

const {
  createIntegrationService,
} =
  require(
    "../../api/integration/service.js",
  );

test(
  "BrokerとPortfolioを統合分析",
  () => {
    const service =
      createIntegrationService();

    const result =
      service.analyze({
        broker: {
          connected:
            true,

          risk:
            "low",
        },

        portfolio: {
          risk:
            "moderate",
        },

        market: {
          regime:
            "neutral",
        },
      });

    assert.equal(
      result.runtime.status,
      "ready",
    );

    assert.equal(
      result.decision.action,
      "HOLD",
    );

    assert.equal(
      result.orderSubmissionAllowed,
      false,
    );
  },
);

test(
  "重大リスク時は分析をブロック",
  () => {
    const service =
      createIntegrationService();

    const result =
      service.analyze({
        broker: {
          connected:
            false,

          risk:
            "critical",
        },

        portfolio: {
          risk:
            "critical",
        },
      });

    assert.equal(
      result
        .decision
        .policy
        .allowedForAnalysis,
      false,
    );

    assert.equal(
      result.decision.action,
      "BLOCK_ANALYSIS",
    );

    assert.equal(
      result
        .decision
        .orderSubmissionAllowed,
      false,
    );
  },
);

test(
  "統合履歴を保存",
  () => {
    const service =
      createIntegrationService();

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