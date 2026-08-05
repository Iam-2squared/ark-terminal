import test from "node:test";
import assert from "node:assert/strict";

import { buildUnifiedDashboardV1 } from "../control/unified-dashboard-v1.js";
import { buildUiStateV1 } from "../ui/ui-state-v1.js";
import { RequestCacheV1 } from "../performance/request-cache-v1.js";

test("unified dashboard aggregates module health safely", () => {
  const result = buildUnifiedDashboardV1({
    modules: {
      prediction: { status: "READY", href: "/predict/" },
      discovery: { status: "READY", href: "/discovery/" },
      paperTrading: { status: "BLOCKED" },
    },
  });
  assert.equal(result.overallStatus, "BLOCKED");
  assert.ok(result.blocked.includes("paperTrading"));
  assert.equal(result.mobileReady, true);
  assert.equal(result.safety.liveExecutionAllowed, false);
});

test("shared UI state distinguishes loading error empty and ready", () => {
  assert.equal(buildUiStateV1({ loading: true }).status, "LOADING");
  assert.equal(buildUiStateV1({ error: new Error("boom") }).status, "ERROR");
  assert.equal(buildUiStateV1({ data: [] }).status, "EMPTY");
  assert.equal(buildUiStateV1({ data: [1] }).status, "READY");
});

test("request cache reuses cached results and deduplicates inflight work", async () => {
  let now = 1000;
  let calls = 0;
  const cache = new RequestCacheV1({ ttlMs: 100, now: () => now });
  const loader = async () => {
    calls += 1;
    await Promise.resolve();
    return { ok: true };
  };

  const [a, b] = await Promise.all([
    cache.getOrLoad("x", loader),
    cache.getOrLoad("x", loader),
  ]);
  assert.equal(calls, 1);
  assert.deepEqual(a.value, { ok: true });
  assert.deepEqual(b.value, { ok: true });

  const cached = await cache.getOrLoad("x", loader);
  assert.equal(cached.source, "CACHE");
  assert.equal(calls, 1);

  now += 101;
  const refreshed = await cache.getOrLoad("x", loader);
  assert.equal(refreshed.source, "LOADER");
  assert.equal(calls, 2);
});
