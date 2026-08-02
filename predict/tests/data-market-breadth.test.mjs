import assert from "node:assert/strict";
import test from "node:test";

import { fetchMarketBreadth } from "../data.js";

test("Prediction data service requests the Market Breadth API", async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = null;

  globalThis.fetch = async (input) => {
    requestedUrl = new URL(input);
    return {
      ok: true,
      async json() {
        return {
          observations: [{ symbol: "7203.T" }],
          expectedObservationCount: 3709,
          status: "available",
          executionAllowed: false,
        };
      },
    };
  };

  try {
    const payload = await fetchMarketBreadth();

    assert.equal(requestedUrl.pathname, "/api/market-breadth");
    assert.equal(payload.observations.length, 1);
    assert.equal(payload.expectedObservationCount, 3709);
    assert.equal(payload.executionAllowed, false);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("Prediction data service fails closed when Breadth is unavailable", async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async () => ({
    ok: false,
    status: 502,
    async json() {
      return { error: "upstream unavailable" };
    },
  });

  try {
    const payload = await fetchMarketBreadth();

    assert.equal(payload.status, "unavailable");
    assert.deepEqual(payload.observations, []);
    assert.equal(payload.expectedObservationCount, 0);
    assert.equal(payload.executionAllowed, false);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
