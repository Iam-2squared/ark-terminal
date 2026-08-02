import { scoreMarketSeries } from "./market-score.js";

export const GLOBAL_INDEX_CONFIGURATION = Object.freeze([
  Object.freeze({ symbol: "NIKKEI225", region: "JP", weight: 1, scale: 2 }),
  Object.freeze({ symbol: "TOPIX", region: "JP", weight: 1, scale: 2 }),
  Object.freeze({ symbol: "JPX400", region: "JP", weight: 0.8, scale: 2 }),
  Object.freeze({ symbol: "GROWTH250", region: "JP", weight: 0.8, scale: 3 }),
  Object.freeze({ symbol: "NASDAQ", region: "US", weight: 1, scale: 2.5 }),
  Object.freeze({ symbol: "SP500", region: "US", weight: 1, scale: 2 }),
  Object.freeze({ symbol: "SOX", region: "US", weight: 0.9, scale: 3 }),
  Object.freeze({ symbol: "RUSSELL2000", region: "US", weight: 0.8, scale: 3 }),
]);

function configurationForRegion(region) {
  return GLOBAL_INDEX_CONFIGURATION.filter((entry) => entry.region === region);
}

function ranking(items, direction) {
  return items
    .filter((item) => item.available)
    .sort(
      (first, second) =>
        direction * (second.changePercent - first.changePercent),
    )
    .slice(0, 3)
    .map((item) => ({
      symbol: item.symbol,
      changePercent: item.changePercent,
      score: item.score,
    }));
}

function regionalReport(points, region) {
  const report = scoreMarketSeries(points, configurationForRegion(region));

  return {
    score: report.score,
    confidence: report.confidence,
    coverage: report.coverage,
    availableCount: report.availableCount,
    requestedCount: report.requestedCount,
  };
}

export function analyzeGlobalIndexes(points = []) {
  const report = scoreMarketSeries(points, GLOBAL_INDEX_CONFIGURATION);

  return {
    score: report.score,
    confidence: report.confidence,
    coverage: report.coverage,
    availableCount: report.availableCount,
    requestedCount: report.requestedCount,
    regions: {
      JP: regionalReport(points, "JP"),
      US: regionalReport(points, "US"),
    },
    leaders: ranking([...report.items], 1),
    laggards: ranking([...report.items], -1),
    items: report.items,
  };
}

export class GlobalIndexEngine {
  analyze(points = []) {
    return analyzeGlobalIndexes(points);
  }
}

export const globalIndexEngine = new GlobalIndexEngine();

export default analyzeGlobalIndexes;
