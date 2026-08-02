import test from "node:test";
import assert from "node:assert/strict";

import {
  createPaperBroker,
} from "../paper/paper-broker.js";

import {
  createDryRunBrokerAdapter,
} from "../broker/dry-run-broker-adapter.js";

import {
  createDisabledLiveBrokerAdapter,
} from "../broker/disabled-live-broker-adapter.js";

import {
  validateBrokerExecutionSystem,
  validatePaperTradingSystem,
  validatePart260,
} from "../broker/part260-validation.js";

test(
  "Paper Trading基盤を検証",
  () => {
    const result =
      validatePaperTradingSystem({
        broker:
          createPaperBroker(),
      });

    assert.equal(
      result.passed,
      true,
    );

    assert.equal(
      result.status,
      "warning",
    );

    assert.equal(
      result.errors.length,
      0,
    );
  },
);

test(
  "Dry Run Adapterを検証",
  () => {
    const result =
      validateBrokerExecutionSystem({
        adapter:
          createDryRunBrokerAdapter(),
      });

    assert.equal(
      result.passed,
      true,
    );

    assert.equal(
      result.adapterInfo.mode,
      "dry-run",
    );

    assert.equal(
      result.adapterInfo
        .liveTradingEnabled,
      false,
    );
  },
);

test(
  "未設定Live Adapterは準備未完了",
  () => {
    const result =
      validateBrokerExecutionSystem({
        adapter:
          createDisabledLiveBrokerAdapter(),

        livePolicy: {
          allowLiveTrading:
            false,
        },
      });

    assert.equal(
      result.passed,
      true,
    );

    assert.equal(
      result.status,
      "warning",
    );

    assert.equal(
      result.readiness.ready,
      false,
    );
  },
);

test(
  "Part260統合検証",
  () => {
    const result =
      validatePart260({
        broker:
          createPaperBroker(),

        adapter:
          createDryRunBrokerAdapter(),
      });

    assert.equal(
      result.passed,
      true,
    );

    assert.equal(
      result.liveTradingAllowed,
      false,
    );
  },
);

test(
  "Live取引は既定で許可しない",
  () => {
    const result =
      validatePart260({
        broker:
          createPaperBroker(),

        adapter:
          createDisabledLiveBrokerAdapter(),
      });

    assert.equal(
      result.liveTradingAllowed,
      false,
    );
  },
);