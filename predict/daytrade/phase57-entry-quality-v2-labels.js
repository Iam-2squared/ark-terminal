export const PHASE57_ENTRY_QUALITY_V2_LABEL_POLICY = Object.freeze({
  mode: 'OFFLINE_FUTURE_LABELS_ONLY',
  allowedHorizonsBars: Object.freeze([1, 2, 3, 6, 12]),
  mayEnterCurrentFeatureVector: false,
  mayRunInRealtimeScorer: false,
  mayChangeExitBehavior: false,
  automaticPromotionAllowed: false,
});

const pct = (a, b) => Number.isFinite(a) && Number.isFinite(b) && b !== 0 ? (a / b - 1) * 100 : 0;

function normalizeFutureBars(bars = [], after) {
  const cutoff = new Date(after).getTime();
  if (!Number.isFinite(cutoff)) throw new Error('ENTRY_V2_LABEL_INVALID_ENTRY_TIMESTAMP');
  return bars
    .map(bar => ({
      timestamp: new Date(bar.timestamp).toISOString(),
      high: Number(bar.high),
      low: Number(bar.low),
      close: Number(bar.close),
    }))
    .filter(bar => [bar.high, bar.low, bar.close].every(Number.isFinite))
    .filter(bar => new Date(bar.timestamp).getTime() > cutoff)
    .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
}

function pathForDirection({ entryPrice, bars, direction, costBps = 0 }) {
  const sign = direction === 'SHORT' ? -1 : 1;
  const closeReturns = bars.map(bar => sign * pct(bar.close, entryPrice));
  const favorable = bars.map(bar => direction === 'SHORT'
    ? pct(entryPrice, bar.low)
    : pct(bar.high, entryPrice));
  const adverse = bars.map(bar => direction === 'SHORT'
    ? -pct(bar.high, entryPrice)
    : pct(bar.low, entryPrice));

  let mfeIndex = 0;
  let maeIndex = 0;
  for (let i = 1; i < bars.length; i += 1) {
    if (favorable[i] > favorable[mfeIndex]) mfeIndex = i;
    if (adverse[i] < adverse[maeIndex]) maeIndex = i;
  }

  const grossReturnPct = closeReturns.at(-1) ?? 0;
  const roundTripCostPct = Number(costBps) / 100;

  return Object.freeze({
    direction,
    grossReturnPct,
    costAdjustedReturnPct: grossReturnPct - roundTripCostPct,
    mfePct: favorable[mfeIndex] ?? 0,
    maePct: adverse[maeIndex] ?? 0,
    timeToMfeBars: bars.length ? mfeIndex + 1 : null,
    timeToMaeBars: bars.length ? maeIndex + 1 : null,
    mfeTimestamp: bars[mfeIndex]?.timestamp ?? null,
    maeTimestamp: bars[maeIndex]?.timestamp ?? null,
  });
}

export function buildEntryQualityV2PathLabels({
  entryTimestamp,
  entryPrice,
  futureBars = [],
  horizonsBars = PHASE57_ENTRY_QUALITY_V2_LABEL_POLICY.allowedHorizonsBars,
  roundTripCostBps = 0,
}) {
  const price = Number(entryPrice);
  if (!(price > 0)) throw new Error('ENTRY_V2_LABEL_INVALID_ENTRY_PRICE');
  const bars = normalizeFutureBars(futureBars, entryTimestamp);
  const horizons = [...new Set(horizonsBars.map(Number))]
    .filter(Number.isInteger)
    .filter(h => h > 0)
    .sort((a, b) => a - b);

  return Object.freeze({
    policy: PHASE57_ENTRY_QUALITY_V2_LABEL_POLICY,
    entryTimestamp: new Date(entryTimestamp).toISOString(),
    entryPrice: price,
    availableFutureBars: bars.length,
    labels: Object.freeze(horizons.map(horizonBars => {
      const path = bars.slice(0, horizonBars);
      if (path.length < horizonBars) {
        return Object.freeze({ horizonBars, complete: false, long: null, short: null });
      }
      return Object.freeze({
        horizonBars,
        complete: true,
        long: pathForDirection({ entryPrice: price, bars: path, direction: 'LONG', costBps: roundTripCostBps }),
        short: pathForDirection({ entryPrice: price, bars: path, direction: 'SHORT', costBps: roundTripCostBps }),
      });
    })),
  });
}

export default { PHASE57_ENTRY_QUALITY_V2_LABEL_POLICY, buildEntryQualityV2PathLabels };
