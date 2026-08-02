import assert from "node:assert/strict";
import test from "node:test";

import {
  fetchJquantsTdnetDisclosures,
  normalizeJquantsCode,
} from "../../server/providers/jquants-tdnet-provider.js";

test("J-Quants provider normalizes Tokyo issue codes", () => {
  assert.equal(normalizeJquantsCode("285A.T"), "285A0");
  assert.equal(normalizeJquantsCode("7203"), "72030");
  assert.equal(normalizeJquantsCode("72030"), "72030");
  assert.equal(normalizeJquantsCode("AAPL"), null);
});

test("J-Quants provider follows bounded pagination and normalizes TDnet", async () => {
  const requests = [];
  const fetchImpl = async (input, options) => {
    const url = new URL(input);
    requests.push({ url, options });

    if (!url.searchParams.has("pagination_key")) {
      return {
        ok: true,
        async json() {
          return {
            data: [
              {
                DiscNo: "20260401001",
                Code: "285A0",
                DiscDate: "20260401",
                DiscTime: "153000",
                Title: "決算情報のお知らせ",
                DiscStatus: "new",
                RevNo: 0,
                DiscItems: ["earnings"],
                Docs: [{ Url: "https://example.test/disclosure-1.pdf" }],
              },
            ],
            pagination_key: "page-2",
          };
        },
      };
    }

    return {
      ok: true,
      async json() {
        return {
          data: [
            {
              DiscNo: "20260331001",
              Code: "285A0",
              DiscDate: "2026-03-31",
              DiscTime: "1500",
              Title: "組織変更のお知らせ",
            },
          ],
        };
      },
    };
  };
  const disclosures = await fetchJquantsTdnetDisclosures("285A.T", {
    apiKey: "server-jquants-key",
    fetchImpl,
    limit: 2,
  });

  assert.equal(disclosures.length, 2);
  assert.equal(disclosures[0].id, "20260401001");
  assert.equal(disclosures[0].type, "tdnet");
  assert.equal(disclosures[0].publishedAt, "2026-04-01T06:30:00.000Z");
  assert.equal(disclosures[0].url, "https://example.test/disclosure-1.pdf");
  assert.equal(requests.length, 2);
  assert.equal(requests[0].url.pathname, "/v2/td/list");
  assert.equal(requests[0].url.searchParams.get("code"), "285A0");
  assert.equal(
    requests[1].url.searchParams.get("pagination_key"),
    "page-2",
  );
  assert.equal(requests[0].options.headers["x-api-key"], "server-jquants-key");
});

test("J-Quants provider rejects missing server credential", async () => {
  await assert.rejects(
    fetchJquantsTdnetDisclosures("285A.T", {
      apiKey: "",
      fetchImpl: async () => ({ ok: true }),
    }),
    /JQUANTS_API_KEY/,
  );
});
