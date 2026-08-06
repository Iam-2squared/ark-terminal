import assert from "node:assert/strict";
import test from "node:test";

import { ScreenerDataApiInternals } from "../../server/screener-data.js";

test("データ専用ブランチを優先しmainをフォールバックにする", () => {
  const candidates = ScreenerDataApiInternals.buildCandidateUrls(
    "snapshot",
    1_800_000,
  );

  assert.equal(candidates[0].branch, "automation/screener-data");
  assert.match(candidates[0].url, /automation\/screener-data/);
  assert.equal(candidates[1].branch, "main");
  assert.match(candidates[1].url, /refs\/heads\/main/);
});

test("取得データへ自動配信元を付与する", () => {
  const payload = ScreenerDataApiInternals.normalizePayload(
    {
      meta: { generatedAt: "2026-08-01T00:00:00.000Z" },
      entries: [],
    },
    {
      sourceBranch: "automation/screener-data",
      fetchedAt: "2026-08-01T00:03:00.000Z",
    },
  );

  assert.equal(payload.meta.delivery.sourceBranch, "automation/screener-data");
  assert.equal(payload.meta.delivery.mode, "automatic-data-branch");
});

test("不正なデータ種別は拒否する", () => {
  assert.equal(ScreenerDataApiInternals.normalizeType("snapshot"), "snapshot");
  assert.equal(ScreenerDataApiInternals.normalizeType("universe"), "universe");
  assert.equal(ScreenerDataApiInternals.normalizeType("secret"), null);
});

test("データ専用ブランチ失敗時はmainへフォールバックする", async () => {
  const requested = [];
  const fetchImpl = async (url) => {
    requested.push(url);

    if (url.includes("automation/screener-data")) {
      return { ok: false, status: 404 };
    }

    return {
      ok: true,
      status: 200,
      json: async () => ({ entries: [] }),
    };
  };

  const payload = await ScreenerDataApiInternals.loadScreenerData(
    "snapshot",
    fetchImpl,
  );

  assert.equal(requested.length, 2);
  assert.equal(payload.meta.delivery.sourceBranch, "main");
});
