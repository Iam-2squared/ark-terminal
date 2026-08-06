import { ScreenerDataApiInternals } from "./screener.js";
import { createScreenerBreadthPayload } from "../server/providers/screener-breadth-provider.js";

export async function loadMarketBreadth({
  fetchImpl = globalThis.fetch,
  now = Date.now,
} = {}) {
  const snapshot = await ScreenerDataApiInternals.loadScreenerData(
    "snapshot",
    fetchImpl,
  );

  return createScreenerBreadthPayload(snapshot, { now });
}

export default async function handler(request, response) {
  response.setHeader("Access-Control-Allow-Origin", "*");
  response.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
  response.setHeader(
    "Cache-Control",
    "public, max-age=0, s-maxage=180, stale-while-revalidate=900",
  );

  if (request.method === "OPTIONS") {
    return response.status(204).end();
  }

  if (request.method !== "GET") {
    return response.status(405).json({
      error: "GETのみ利用できます。",
    });
  }

  try {
    return response.status(200).json(await loadMarketBreadth());
  } catch (error) {
    console.error("Market breadth API:", error);

    return response.status(502).json({
      observations: [],
      expectedObservationCount: 0,
      availableCount: 0,
      coverage: 0,
      timestamp: null,
      source: "ark-screener:unavailable",
      status: "unavailable",
      executionAllowed: false,
      errors: [error.message || "市場Breadthデータを取得できませんでした。"],
    });
  }
}

export const MarketBreadthApiInternals = Object.freeze({
  createScreenerBreadthPayload,
});