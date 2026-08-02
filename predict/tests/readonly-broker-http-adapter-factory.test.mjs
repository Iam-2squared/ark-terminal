import test from "node:test";
import assert from "node:assert/strict";

import {
  createReadonlyBrokerHttpAdapter,
} from "../broker/readonly-broker-http-adapter-factory.js";

function jsonResponse(
  body,
) {
  return {
    ok:
      true,

    status:
      200,

    headers: {
      get() {
        return "application/json";
      },
    },

    async json() {
      return structuredClone(
        body,
      );
    },

    async text() {
      return JSON.stringify(
        body,
      );
    },
  };
}

test(
  "HTTP GatewayをRead-only Adapterへ接続",
  async () => {
    const adapter =
      createReadonlyBrokerHttpAdapter({
        provider:
          "test-broker",

        fetchProvider:
          async (
            url,
          ) => {
            if (
              url.endsWith(
                "/connection",
              )
            ) {
              return jsonResponse({
                connected:
                  true,

                authenticated:
                  true,

                provider:
                  "test-broker",
              });
            }

            if (
              url.endsWith(
                "/account",
              )
            ) {
              return jsonResponse({
                account: {
                  accountId:
                    "account-1",

                  cash:
                    700_000,
                },
              });
            }

            if (
              url.endsWith(
                "/positions",
              )
            ) {
              return jsonResponse({
                positions: [
                  {
                    symbol:
                      "6758.T",

                    quantity:
                      100,
                  },
                ],
              });
            }

            return jsonResponse({
              orders: [],
            });
          },
      });

    await adapter.connect();

    const snapshot =
      await adapter.sync();

    assert.equal(
      snapshot.account.accountId,
      "account-1",
    );

    assert.equal(
      snapshot.positions.length,
      1,
    );

    assert.equal(
      snapshot.readOnly,
      true,
    );
  },
);

test(
  "HTTP Adapterでも発注を拒否",
  () => {
    const adapter =
      createReadonlyBrokerHttpAdapter({
        fetchProvider:
          async () =>
            jsonResponse({}),
      });

    const result =
      adapter.submitOrder({
        symbol:
          "7203.T",

        side:
          "buy",

        quantity:
          100,
      });

    assert.equal(
      result.status,
      "rejected",
    );

    assert.equal(
      result.reason,
      "readonly_adapter",
    );

    assert.equal(
      result.transmitted,
      false,
    );
  },
);