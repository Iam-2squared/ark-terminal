import assert from "node:assert/strict";
import test from "node:test";

import {
  fetchFinnhubCompany,
  fetchFinnhubCompanyNews,
} from "../../api/providers/finnhub-news-provider.js";

test("Finnhub provider normalizes company and dated company news", async () => {
  const requests = [];
  const fetchImpl = async (input, options) => {
    const url = new URL(input);
    requests.push({ url, options });

    if (url.pathname.endsWith("/stock/profile2")) {
      return {
        ok: true,
        async json() {
          return {
            name: "Ark Example",
            ticker: "285A.T",
            country: "JP",
            exchange: "TSE",
            finnhubIndustry: "Technology",
            marketCapitalization: 12345,
          };
        },
      };
    }

    return {
      ok: true,
      async json() {
        return [
          {
            id: 2,
            headline: "Newer update",
            source: "Example Wire",
            datetime: 1_775_260_800,
          },
          {
            id: 1,
            headline: "Older update",
            source: "Example Wire",
            datetime: 1_775_174_400,
          },
        ];
      },
    };
  };
  const company = await fetchFinnhubCompany("285A.T", {
    apiKey: "server-token",
    fetchImpl,
  });
  const news = await fetchFinnhubCompanyNews("285A.T", {
    apiKey: "server-token",
    fetchImpl,
    now: () => new Date("2026-04-05T12:00:00.000Z"),
  });

  assert.equal(company.name, "Ark Example");
  assert.equal(company.source, "Finnhub");
  assert.equal(news.length, 2);
  assert.equal(news[0].headline, "Newer update");
  assert.equal(news[0].type, "news");
  assert.equal(requests[0].url.searchParams.get("token"), "server-token");
  assert.equal(requests[1].url.searchParams.get("from"), "2026-03-22");
  assert.equal(requests[1].url.searchParams.get("to"), "2026-04-05");
  assert.equal(requests[1].options.cache, "no-store");
});

test("Finnhub provider rejects missing server credential", async () => {
  await assert.rejects(
    fetchFinnhubCompany("AAPL", {
      apiKey: "",
      fetchImpl: async () => ({ ok: true }),
    }),
    /FINNHUB_API_KEY/,
  );
});
