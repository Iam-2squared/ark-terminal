import test from "node:test";
import assert from "node:assert/strict";

import {
  createReadonlyBrokerHttpProvider,
} from "../broker/readonly-broker-http-provider.js";

function jsonResponse(
  body,
  status = 200,
) {
  return {
    ok:
      status >= 200 &&
      status < 300,

    status,

    headers: {
      get(name) {
        return (
          String(name)
            .toLowerCase() ===
          "content-type"
        )
          ? "application/json"
          : null;
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
  "GETのみでGatewayへアクセス",
  async () => {
    const calls = [];

    const provider =
      createReadonlyBrokerHttpProvider({
        baseUrl:
          "/api/broker-readonly/",

        requestIdProvider:
          () =>
            "request-1",

        fetchProvider:
          async (
            url,
            options,
          ) => {
            calls.push({
              url,
              options,
            });

            return jsonResponse({
              connected:
                true,

              authenticated:
                true,

              provider:
                "test-broker",
            });
          },
      });

    const result =
      await provider
        .connectionProvider();

    assert.equal(
      result.connected,
      true,
    );

    assert.equal(
      calls[0].url,
      "/api/broker-readonly/connection",
    );

    assert.equal(
      calls[0].options.method,
      "GET",
    );

    assert.equal(
      calls[0].options.headers[
        "X-Ark-Read-Only"
      ],
      "true",
    );

    assert.equal(
      calls[0].options.credentials,
      "same-origin",
    );
  },
);

test(
  "口座レスポンスを取り出す",
  async () => {
    const provider =
      createReadonlyBrokerHttpProvider({
        fetchProvider:
          async () =>
            jsonResponse({
              account: {
                accountId:
                  "account-1",

                cash:
                  500_000,
              },
            }),
      });

    const account =
      await provider
        .accountProvider();

    assert.equal(
      account.accountId,
      "account-1",
    );

    assert.equal(
      account.cash,
      500_000,
    );
  },
);

test(
  "保有株と注文履歴を配列へ正規化",
  async () => {
    const provider =
      createReadonlyBrokerHttpProvider({
        fetchProvider:
          async (
            url,
          ) => {
            if (
              url.endsWith(
                "/positions",
              )
            ) {
              return jsonResponse({
                positions: [
                  {
                    symbol:
                      "7203.T",
                  },
                ],
              });
            }

            return jsonResponse({
              orders: [
                {
                  orderId:
                    "order-1",
                },
              ],
            });
          },
      });

    const positions =
      await provider
        .positionsProvider();

    const orders =
      await provider
        .ordersProvider();

    assert.equal(
      positions.length,
      1,
    );

    assert.equal(
      orders.length,
      1,
    );
  },
);

test(
  "Gatewayエラーを例外化",
  async () => {
    const provider =
      createReadonlyBrokerHttpProvider({
        fetchProvider:
          async () =>
            jsonResponse(
              {
                code:
                  "BROKER_NOT_CONNECTED",

                message:
                  "Broker is not connected.",
              },
              503,
            ),
      });

    await assert.rejects(
      () =>
        provider
          .accountProvider(),
      (
        error,
      ) => {
        assert.equal(
          error.code,
          "BROKER_NOT_CONNECTED",
        );

        assert.equal(
          error.status,
          503,
        );

        return true;
      },
    );
  },
);