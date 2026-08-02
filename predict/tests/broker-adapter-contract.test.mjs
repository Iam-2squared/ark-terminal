import test from "node:test";
import assert from "node:assert/strict";

import {
  assertBrokerAdapter,
  normalizeBrokerSymbol,
  validateBrokerOrder,
} from "../broker/broker-adapter-contract.js";

test(
  "銘柄コードを正規化",
  () => {
    assert.equal(
      normalizeBrokerSymbol(
        " 7203.t ",
      ),
      "7203.T",
    );
  },
);

test(
  "正しい注文を検証",
  () => {
    const result =
      validateBrokerOrder({
        symbol:
          "7203.t",

        side:
          "buy",

        quantity:
          100,

        type:
          "market",
      });

    assert.equal(
      result.valid,
      true,
    );

    assert.equal(
      result.normalizedOrder
        .symbol,
      "7203.T",
    );
  },
);

test(
  "不正数量を拒否",
  () => {
    const result =
      validateBrokerOrder({
        symbol:
          "7203.T",

        side:
          "buy",

        quantity:
          0,
      });

    assert.equal(
      result.valid,
      false,
    );

    assert.ok(
      result.errors.includes(
        "quantity_invalid",
      ),
    );
  },
);

test(
  "Adapter契約違反を検出",
  () => {
    assert.throws(
      () =>
        assertBrokerAdapter({
          getInfo() {},
        }),
      /method is missing/,
    );
  },
);