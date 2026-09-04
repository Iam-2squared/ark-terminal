import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PHASE57_ENTRY_QUALITY_V2_LABEL_POLICY,
  buildEntryQualityV2PathLabels,
} from '../daytrade/phase57-entry-quality-v2-labels.js';

const entryTimestamp = '2026-09-04T01:00:00.000Z';
const bars = [
  { timestamp: '2026-09-04T01:05:00.000Z', high: 102, low: 99, close: 101 },
  { timestamp: '2026-09-04T01:10:00.000Z', high: 104, low: 100, close: 103 },
  { timestamp: '2026-09-04T01:15:00.000Z', high: 103, low: 97, close: 98 },
];

const assertClose = (actual, expected, tolerance = 1e-12) => {
  assert.ok(
    Math.abs(actual - expected) <= tolerance,
    `expected ${actual} to be within ${tolerance} of ${expected}`,
  );
};

test('future labels are explicitly forbidden from current feature vectors and realtime scorer', () => {
  assert.equal(PHASE57_ENTRY_QUALITY_V2_LABEL_POLICY.mayEnterCurrentFeatureVector, false);
  assert.equal(PHASE57_ENTRY_QUALITY_V2_LABEL_POLICY.mayRunInRealtimeScorer, false);
  assert.equal(PHASE57_ENTRY_QUALITY_V2_LABEL_POLICY.mayChangeExitBehavior, false);
  assert.equal(PHASE57_ENTRY_QUALITY_V2_LABEL_POLICY.automaticPromotionAllowed, false);
});

test('path labels compute asymmetric LONG and SHORT return/MFE/MAE', () => {
  const result = buildEntryQualityV2PathLabels({
    entryTimestamp,
    entryPrice: 100,
    futureBars: bars,
    horizonsBars: [1, 3],
  });

  const h1 = result.labels.find(label => label.horizonBars === 1);
  const h3 = result.labels.find(label => label.horizonBars === 3);

  assert.equal(h1.complete, true);
  assertClose(h1.long.grossReturnPct, 1);
  assertClose(h1.short.grossReturnPct, -1);
  assertClose(h1.long.mfePct, 2);
  assertClose(h1.long.maePct, -1);

  assert.equal(h3.complete, true);
  assertClose(h3.long.grossReturnPct, -2);
  assertClose(h3.long.mfePct, 4);
  assertClose(h3.long.maePct, -3);
  assert.equal(h3.long.timeToMfeBars, 2);
  assert.equal(h3.long.timeToMaeBars, 3);

  assertClose(h3.short.grossReturnPct, 2);
  assertClose(h3.short.mfePct, 3.0927835051546393);
  assertClose(h3.short.maePct, -4);
});

test('cost is reported separately as fixed round-trip bps', () => {
  const result = buildEntryQualityV2PathLabels({
    entryTimestamp,
    entryPrice: 100,
    futureBars: bars,
    horizonsBars: [1],
    roundTripCostBps: 20,
  });
  const h1 = result.labels[0];
  assertClose(h1.long.grossReturnPct, 1);
  assertClose(h1.long.costAdjustedReturnPct, 0.8);
});

test('incomplete horizons are marked incomplete rather than padded', () => {
  const result = buildEntryQualityV2PathLabels({
    entryTimestamp,
    entryPrice: 100,
    futureBars: bars.slice(0, 2),
    horizonsBars: [3],
  });
  assert.equal(result.labels[0].complete, false);
  assert.equal(result.labels[0].long, null);
  assert.equal(result.labels[0].short, null);
});
