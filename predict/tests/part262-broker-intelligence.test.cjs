const test =
  require("node:test");

const assert =
  require("node:assert/strict");

const {
  analyzeBrokerIntelligence,
} =
  require(
    "../../server/broker-readonly/intelligence-suite.js",
  );

const {
  createLatencyMonitor,
} =
  require(
    "../../server/broker-readonly/latency-monitor.js",
  );

const {
  calculateAvailability,
} =
  require(
    "../../server/broker-readonly/availability.js",
  );

test(
  "正常なBrokerをread-only利用可能と判定",
  () => {
    const result =
      analyzeBrokerIntelligence({
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
      result.safeForReadOnly,
      true,
    );

    assert.equal(
      result.liveTradingAllowed,
      false,
    );

    assert.equal(
      result.orderSubmissionAllowed,
      false,
    );
  },
);

test(
  "切断状態を安全ガードで拒否",
  () => {
    const result =
      analyzeBrokerIntelligence({
        latency:
          2000,

        uptime:
          90,

        errors:
          12,

        connected:
          false,

        authenticated:
          false,
      });

    assert.equal(
      result.safeForReadOnly,
      false,
    );

    assert.equal(
      result.guard.passed,
      false,
    );

    assert.equal(
      result.anomalies.detected,
      true,
    );
  },
);

test(
  "Latency履歴を集計",
  () => {
    const monitor =
      createLatencyMonitor({
        maximumSamples:
          3,
      });

    monitor.record(
      100,
    );

    monitor.record(
      200,
    );

    const summary =
      monitor.record(
        300,
      );

    assert.equal(
      summary.count,
      3,
    );

    assert.equal(
      summary.average,
      200,
    );

    assert.equal(
      summary.maximum,
      300,
    );
  },
);

test(
  "Availabilityを計算",
  () => {
    const result =
      calculateAvailability({
        successfulChecks:
          999,

        totalChecks:
          1000,
      });

    assert.equal(
      result.availabilityPercent,
      99.9,
    );

    assert.equal(
      result.status,
      "excellent",
    );
  },
);