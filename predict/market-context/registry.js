import { getMarketDataDefinition } from "../market-intelligence/market-data-model.js";

function providerSymbol(symbol) {
  return getMarketDataDefinition(symbol)?.providerSymbol ?? null;
}

export const MARKET_CONTEXT_REGISTRY = Object.freeze([
  {
    id: "nikkei225",
    label: "日経平均",
    providerSymbol: providerSymbol("NIKKEI225"),
    region: "JP",
    role: "broad-market",
    status: "enabled",
  },
  {
    id: "topix",
    label: "TOPIX",
    providerSymbol: null,
    region: "JP",
    role: "broad-market",
    status: "adapter-ready",
  },
  {
    id: "growth250",
    label: "グロース250",
    providerSymbol: null,
    region: "JP",
    role: "growth-market",
    status: "adapter-ready",
  },
  {
    id: "nasdaq",
    label: "NASDAQ",
    providerSymbol: providerSymbol("NASDAQ"),
    region: "US",
    role: "growth-market",
    status: "enabled",
  },
  {
    id: "sox",
    label: "SOX",
    providerSymbol: providerSymbol("SOX"),
    region: "US",
    role: "semiconductor",
    status: "enabled",
  },
  {
    id: "usdJpy",
    label: "ドル円",
    providerSymbol: providerSymbol("USDJPY"),
    region: "GLOBAL",
    role: "currency",
    status: "enabled",
  },
  {
    id: "industry",
    label: "業種指数",
    providerSymbol: null,
    region: "DYNAMIC",
    role: "industry",
    status: "adapter-ready",
  },
]);

export function relevantMarketSeries(symbol) {
  const region = String(symbol).endsWith(".T") ? "JP" : "US";

  return MARKET_CONTEXT_REGISTRY.filter(
    (series) =>
      series.status === "enabled" &&
      (series.region === region || series.region === "GLOBAL"),
  );
}
