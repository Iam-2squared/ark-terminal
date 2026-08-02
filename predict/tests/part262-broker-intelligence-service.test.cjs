const test =
  require("node:test");

const assert =
  require("node:assert/strict");

const {
  createBrokerIntelligenceService,
} =
  require(
    "../../server/broker-readonly/intelligence-service.js",
  );

test(
  "Broker Intelligence Serviceが履歴とレポートを生成",
  () => {
    const service =
      createBrokerIntelligenceService();

    const report =
      service.analyze({
        latency:
          80,

        uptime:
          99.99,

        errors:
          0,

        connected:
          true,

        authenticated:
          true,
      });

    assert.equal(
      report.readOnly,
      true,
    );

    assert.equal(
      report.orderSubmissionAllowed,
      false,
    );

    assert.equal(
      service
        .getHistory()
        .length,
      1,
    );

    assert.ok(
      service.getLatestReport(),
    );
  },
);

test(
  "異常状態ではPolicyをブロック",
  () => {
    const service =
      createBrokerIntelligenceService();

    const report =
      service.analyze({
        latency:
          3000,

        uptime:
          80,

        errors:
          20,

        connected:
          false,

        authenticated:
          false,
      });

    assert.equal(
      report.policy.allowed,
      false,
    );

    assert.equal(
      report.policy.liveTrading,
      false,
    );

    assert.equal(
      report.policy.submitOrder,
      false,
    );
  },
);

test(
  "監査ログを記録",
  () => {
    const service =
      createBrokerIntelligenceService();

    service.analyze({
      latency:
        100,

      uptime:
        99.9,

      errors:
        0,

      connected:
        true,

      authenticated:
        true,
    });

    const audit =
      service.getAuditLog();

    assert.equal(
      audit.length,
      1,
    );

    assert.equal(
      audit[0].event,
      "broker_intelligence_analyzed",
    );

    assert.equal(
      audit[0].readOnly,
      true,
    );
  },
);