import {
  createReadonlyBrokerAdapter,
} from "./readonly-broker-adapter.js";

import {
  createReadonlyBrokerHttpProvider,
} from "./readonly-broker-http-provider.js";

export const READONLY_BROKER_HTTP_ADAPTER_FACTORY_VERSION =
  "readonly-broker-http-adapter-factory-v1";

export function createReadonlyBrokerHttpAdapter({
  provider =
    "broker-gateway",

  baseUrl =
    "/api/broker-readonly",

  fetchProvider =
    globalThis.fetch,

  requestIdProvider,

  nowProvider,
} = {}) {
  const http =
    createReadonlyBrokerHttpProvider({
      baseUrl,
      fetchProvider,
      requestIdProvider,
    });

  return createReadonlyBrokerAdapter({
    provider,

    connectionProvider:
      http.connectionProvider,

    accountProvider:
      http.accountProvider,

    positionsProvider:
      http.positionsProvider,

    ordersProvider:
      http.ordersProvider,

    nowProvider,
  });
}