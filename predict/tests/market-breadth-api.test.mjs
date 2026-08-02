import assert from "node:assert/strict";
import test from "node:test";

import { loadMarketBreadth } from "../../api/market-breadth.js";
import { buildMarketIntelligenceInput } from "../analysis/ai-analysis-input-builder.js";

test("Market breadth API reuses the automatic screener data branch", async () => {
  const requests = [];
  const payload = await loadMarketBreadth({
    fetchImpl: async (input) => {
      requests.push(String(input));
      return {
        ok: true,
        async json() {
          return {
            meta: {
              generatedAt: "2026-08-01T00:00:00.000Z",
              universeCount: 100,
              provider: "yahoo-finance",
            },
            entries: [
              {
                symbol: "7203.T",
                sector: "輸送用機器",
                dailyChangePercent: 1.2,
                volume: 10000,
                volumeRatio: 1.1,
                qualityScore: 90,
                scannedAt: "2026-08-01T01:00:00.000Z",
                status: "analyzed",
                source: "yahoo-finance",
              },
            ],
          };
        },
      };
    },
    now: () => new Date("2026-08-02T00:00:00.000Z"),
  });

  assert.match(requests[0], /automation\/screener-data/);
  assert.equal(payload.observations.length, 1);
  assert.equal(payload.expectedObservationCount, 100);
  assert.equal(payload.sourceBranch, "automation/screener-data");
});

test("AI input forwards observation universe size to existing engines", () => {
  const observations = [
    {
      symbol: "7203.T",
      changePercent: 1.2,
      timestamp: "2026-08-01T01:00:00.000Z",
      confidence: 90,
    },
  ];
  const input = buildMarketIntelligenceInput({
    marketObservations: observations,
    marketBreadthSource: {
      expectedObservationCount: 3709,
    },
  });

  assert.equal(input.observations, observations);
  assert.equal(input.expectedObservationCount, 3709);
});
