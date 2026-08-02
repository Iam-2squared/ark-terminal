const test =
  require("node:test");

const assert =
  require("node:assert/strict");

const {
  initializeBrokerApi,
} =
  require(
    "../../server/broker-readonly/index.js",
  );

test(
  "Read-only Broker APIを初期化",
  () => {
    const api =
      initializeBrokerApi();

    assert.ok(
      api.runtime,
    );

    assert.ok(
      api.session,
    );

    assert.equal(
      api.runtime.status,
      "ready",
    );

    assert.equal(
      api.runtime.readOnly,
      true,
    );

    assert.equal(
      api.runtime.liveTradingEnabled,
      false,
    );

    assert.equal(
      api.runtime.orderSubmissionAvailable,
      false,
    );
  },
);

test(
  "Broker Sessionは読み取り専用",
  () => {
    const api =
      initializeBrokerApi();

    assert.equal(
      api.session.active,
      true,
    );

    assert.equal(
      api.session.readOnly,
      true,
    );

    assert.equal(
      typeof api.session.id,
      "string",
    );
  },
);

test(
  "APIに発注関数を公開しない",
  () => {
    const api =
      initializeBrokerApi();

    assert.equal(
      typeof api.submitOrder,
      "undefined",
    );

    assert.equal(
      typeof api.cancelOrder,
      "undefined",
    );
  },
);