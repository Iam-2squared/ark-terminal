export const READONLY_BROKER_HTTP_PROVIDER_VERSION =
  "readonly-broker-http-provider-v1";

function clone(value) {
  return structuredClone(value);
}

function normalizeBaseUrl(
  value,
) {
  const url =
    String(
      value ||
      "/api/broker-readonly",
    )
      .trim()
      .replace(
        /\/+$/,
        "",
      );

  if (!url) {
    throw new Error(
      "Read-only broker gateway URL is required.",
    );
  }

  return url;
}

function createUrl({
  baseUrl,
  path,
} = {}) {
  const normalizedPath =
    String(path || "")
      .trim()
      .replace(
        /^\/+/,
        "",
      );

  return (
    normalizeBaseUrl(
      baseUrl,
    ) +
    "/" +
    normalizedPath
  );
}

function createRequestHeaders({
  requestId,
} = {}) {
  return {
    Accept:
      "application/json",

    "X-Ark-Read-Only":
      "true",

    ...(
      requestId
        ? {
            "X-Ark-Request-Id":
              String(
                requestId,
              ),
          }
        : {}
    ),
  };
}

async function parseResponse(
  response,
) {
  const contentType =
    String(
      response.headers
        ?.get?.(
          "content-type",
        ) ||
      "",
    ).toLowerCase();

  let body = null;

  if (
    contentType.includes(
      "application/json",
    )
  ) {
    body =
      await response.json();
  }
  else {
    const text =
      await response.text();

    body =
      text
        ? {
            message:
              text,
          }
        : null;
  }

  if (!response.ok) {
    const error =
      new Error(
        body?.message ||
        `Broker gateway request failed: ${response.status}`,
      );

    error.code =
      body?.code ||
      "BROKER_GATEWAY_REQUEST_FAILED";

    error.status =
      response.status;

    error.details =
      body;

    throw error;
  }

  return body;
}

export function createReadonlyBrokerHttpProvider({
  baseUrl =
    "/api/broker-readonly",

  fetchProvider =
    globalThis.fetch,

  requestIdProvider =
    () =>
      (
        "ark-readonly-" +
        Date.now()
          .toString(36) +
        "-" +
        Math.random()
          .toString(36)
          .slice(2, 10)
      ),
} = {}) {
  if (
    typeof fetchProvider !==
    "function"
  ) {
    throw new Error(
      "Fetch provider is required.",
    );
  }

  const resolvedBaseUrl =
    normalizeBaseUrl(
      baseUrl,
    );

  async function get(
    path,
  ) {
    const requestId =
      requestIdProvider();

    const response =
      await fetchProvider(
        createUrl({
          baseUrl:
            resolvedBaseUrl,

          path,
        }),
        {
          method:
            "GET",

          credentials:
            "same-origin",

          cache:
            "no-store",

          headers:
            createRequestHeaders({
              requestId,
            }),
        },
      );

    const body =
      await parseResponse(
        response,
      );

    return body === null
      ? null
      : clone(body);
  }

  async function connectionProvider() {
    const result =
      await get(
        "connection",
      );

    return {
      connected:
        result?.connected ===
        true,

      authenticated:
        result?.authenticated ===
        true,

      provider:
        result?.provider ||
        "unconfigured",

      accountId:
        result?.accountId ||
        null,

      connectedAt:
        result?.connectedAt ||
        null,

      lastSyncAt:
        result?.lastSyncAt ||
        null,

      message:
        result?.message ||
        null,
    };
  }

  async function accountProvider() {
    const result =
      await get(
        "account",
      );

    return (
      result?.account ??
      result ??
      null
    );
  }

  async function positionsProvider() {
    const result =
      await get(
        "positions",
      );

    const positions =
      result?.positions ??
      result;

    return Array.isArray(
      positions,
    )
      ? positions
      : [];
  }

  async function ordersProvider() {
    const result =
      await get(
        "orders",
      );

    const orders =
      result?.orders ??
      result;

    return Array.isArray(
      orders,
    )
      ? orders
      : [];
  }

  async function healthProvider() {
    return get(
      "health",
    );
  }

  return {
    version:
      READONLY_BROKER_HTTP_PROVIDER_VERSION,

    baseUrl:
      resolvedBaseUrl,

    connectionProvider,
    accountProvider,
    positionsProvider,
    ordersProvider,
    healthProvider,
  };
}

export const ReadonlyBrokerHttpProviderInternals = {
  clone,
  normalizeBaseUrl,
  createUrl,
  createRequestHeaders,
  parseResponse,
};