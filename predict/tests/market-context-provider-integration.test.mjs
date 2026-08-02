import assert from "node:assert/strict";
import test from "node:test";

import { loadMarketContext } from "../../api/context.js";

test("Market context isolates and combines Finnhub and J-Quants providers", async () => {
  const requests = [];
  const fetchImpl = async (input) => {
    const url = new URL(input);
    requests.push(url);

    if (url.hostname === "api.jquants.com") {
      return {
        ok: true,
        async json() {
          return {
            data: [
              {
                DiscNo: "disc-1",
                Code: "285A0",
                DiscDate: "2026-08-01",
                DiscTime: "15:00",
                Title: "適時開示テスト",
              },
            ],
          };
        },
      };
    }

    if (url.pathname.endsWith("/stock/profile2")) {
      return {
        ok: true,
        async json() {
          return { name: "Example JP", ticker: "285A.T" };
        },
      };
    }

    return {
      ok: true,
      async json() {
        return [
          {
            id: "news-1",
            headline: "企業ニューステスト",
            source: "Example",
            datetime: 1_775_260_800,
          },
        ];
      },
    };
  };
  const context = await loadMarketContext("285A", {
    finnhubApiKey: "finnhub-key",
    jquantsApiKey: "jquants-key",
    fetchImpl,
    now: () => new Date("2026-08-02T00:00:00.000Z"),
  });

  assert.equal(context.symbol, "285A.T");
  assert.equal(context.company.name, "Example JP");
  assert.equal(context.news.length, 1);
  assert.equal(context.disclosures.length, 1);
  assert.deepEqual(context.status, {
    company: "available",
    news: "available",
    disclosures: "available",
    sentiment: "not_configured",
  });
  assert.equal(context.executionAllowed, false);
  assert.equal(requests.length, 3);
});

test("Market context reports absent providers without making neutral data", async () => {
  let fetchCount = 0;
  const context = await loadMarketContext("285A", {
    fetchImpl: async () => {
      fetchCount += 1;
      throw new Error("should not fetch");
    },
  });

  assert.equal(fetchCount, 0);
  assert.equal(context.status.company, "not_configured");
  assert.equal(context.status.news, "not_configured");
  assert.equal(context.status.disclosures, "not_configured");
  assert.deepEqual(context.news, []);
  assert.deepEqual(context.disclosures, []);
  assert.equal(context.sentiment, null);
  assert.match(context.errors.join(" "), /FINNHUB_API_KEY/);
  assert.match(context.errors.join(" "), /JQUANTS_API_KEY/);
});

test("Market context marks TDnet not applicable for non-Japanese symbols", async () => {
  const context = await loadMarketContext("AAPL", {
    jquantsApiKey: "jquants-key",
  });

  assert.equal(context.status.disclosures, "not_applicable");
});
