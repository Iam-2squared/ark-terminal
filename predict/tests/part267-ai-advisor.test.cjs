const test =
  require("node:test");

const assert =
  require("node:assert/strict");

const {
  createAdvisorService,
} = require(
  "../../server/ai-advisor/service.js"
);

test(
  "Advisor produces safe WATCH_BUY recommendation",
  () => {
    const service =
      createAdvisorService();

    const result =
      service.analyze({
        symbol: "7203.T",

        ai: {
          score: {
            score: 82,
          },

          confidence: {
            score: 90,
          },

          decision: {
            action: "WATCH_BUY",
          },

          policy: {
            analysisAllowed: true,
            recommendationAllowed: true,
          },
        },

        market: {
          connected: true,

          regime: {
            regime: "bull",
          },

          globalScore: {
            score: 78,
          },

          confidence: {
            score: 80,
          },
        },

        portfolio: {
          risk: {
            level: "low",
          },

          score: {
            score: 75,
          },

          confidence: {
            score: 80,
          },
        },

        broker: {
          connected: true,
          status: "ready",

          score: {
            score: 95,
          },
        },
      });

    assert.equal(
      result.recommendation.recommendation,
      "WATCH_BUY"
    );

    assert.equal(
      result.orderSubmissionAllowed,
      false
    );

    assert.equal(
      result.safety.allowed,
      true
    );
  }
);

test(
  "Disconnected broker blocks recommendation",
  () => {
    const service =
      createAdvisorService();

    const result =
      service.analyze({
        broker: {
          connected: false,
        },

        market: {
          connected: true,
        },
      });

    assert.equal(
      result.safety.allowed,
      false
    );

    assert.equal(
      result.recommendation.recommendation,
      "BLOCK"
    );
  }
);

test(
  "Conflicting signals require review",
  () => {
    const service =
      createAdvisorService();

    const result =
      service.analyze({
        ai: {
          decision: {
            action: "WATCH_BUY",
          },

          confidence: {
            score: 90,
          },

          policy: {
            analysisAllowed: true,
            recommendationAllowed: true,
          },
        },

        market: {
          connected: true,

          regime: {
            regime: "risk_off",
          },
        },

        portfolio: {
          risk: {
            level: "low",
          },
        },

        broker: {
          connected: true,
        },
      });

    assert.equal(
      result.conflicts.hasConflict,
      true
    );

    assert.equal(
      result.recommendation.recommendation,
      "REVIEW"
    );
  }
);

test(
  "Advisor audit is stored",
  () => {
    const service =
      createAdvisorService();

    service.analyze({});

    assert.equal(
      service.getAudit().length,
      1
    );

    assert.ok(
      service.getLatestAudit()
    );
  }
);