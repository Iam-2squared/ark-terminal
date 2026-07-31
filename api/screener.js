import {
  buildBlockedEntry,
  buildScreenerEntry,
} from "../discovery/engine.js";
import { DEFAULT_WEIGHTS } from "../predict/config.js";
import { HistoryInternals } from "./history.js";

const MAXIMUM_SYMBOLS = 6;

function parseSymbols(value) {
  return [
    ...new Set(
      String(value || "")
        .split(",")
        .map((symbol) => HistoryInternals.normalizeSymbol(symbol))
        .filter(Boolean),
    ),
  ].slice(0, MAXIMUM_SYMBOLS);
}

async function analyzeSymbol(symbol) {
  try {
    const history = await HistoryInternals.fetchYahooHistory({
      symbol,
      range: "2y",
      interval: "1d",
    });

    return buildScreenerEntry({
      history,
      weights: DEFAULT_WEIGHTS,
    });
  } catch (error) {
    console.error(`Screener API (${symbol}):`, error);

    return buildBlockedEntry({
      symbol,
      error,
    });
  }
}

export default async function handler(request, response) {
  response.setHeader("Access-Control-Allow-Origin", "*");
  response.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
  response.setHeader(
    "Cache-Control",
    "s-maxage=120, stale-while-revalidate=600",
  );

  if (request.method === "OPTIONS") {
    return response.status(204).end();
  }

  if (request.method !== "GET") {
    return response.status(405).json({
      error: "GETのみ利用できます。",
    });
  }

  const symbols = parseSymbols(request.query.symbols);

  if (!symbols.length) {
    return response.status(400).json({
      error: "銘柄コードが必要です。",
    });
  }

  const entries = await Promise.all(symbols.map(analyzeSymbol));

  return response.status(200).json({
    entries,
    meta: {
      requested: symbols.length,
      analyzed: entries.filter((entry) => entry.status === "analyzed").length,
      generatedAt: new Date().toISOString(),
      maximumSymbolsPerRequest: MAXIMUM_SYMBOLS,
    },
  });
}

export const ScreenerApiInternals = {
  parseSymbols,
  analyzeSymbol,
};
