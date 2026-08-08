import test from 'node:test';
import assert from 'node:assert/strict';
import { analyzePriceActionFeatures } from '../chart/phase56-price-action.js';

function baseBars() {
  return Array.from({ length: 12 }, (_, i) => ({
    time: i,
    open: 100 + i * 0.2,
    high: 101 + i * 0.2,
    low: 99 + i * 0.2,
    close: 100.4 + i * 0.2,
    volume: 1000,
    vwap: 100 + i * 0.2,
  }));
}

test('Phase56.1 extracts wick, lookback and volume features without execution', () => {
  const bars = baseBars();
  bars.at(-1).open = 102;
  bars.at(-1).close = 104;
  bars.at(-1).high = 104.2;
  bars.at(-1).low = 101.9;
  bars.at(-1).volume = 2000;
  const result = analyzePriceActionFeatures({ bars, swingRadius: 1 });
  assert.equal(result.status, 'PRICE_ACTION_FEATURES_READY');
  assert.ok(result.labels.includes('CLOSE_ABOVE_LOOKBACK_HIGH'));
  assert.equal(result.volume.elevated, true);
  assert.equal(result.descriptiveOnly, true);
  assert.equal(result.executionAllowed, false);
  assert.equal(result.transmitted, false);
});

test('Phase56.1 recognizes long lower wick descriptively', () => {
  const bars = baseBars();
  const last = bars.at(-1);
  last.open = 102;
  last.close = 102.2;
  last.high = 102.3;
  last.low = 100;
  const result = analyzePriceActionFeatures({ bars, swingRadius: 1 });
  assert.ok(result.labels.includes('LONG_LOWER_WICK'));
});

test('Phase56.1 fails closed with too little history', () => {
  const result = analyzePriceActionFeatures({ bars: baseBars().slice(0, 2) });
  assert.equal(result.status, 'OBSERVE');
  assert.ok(result.blockers.includes('INSUFFICIENT_BARS'));
  assert.equal(result.executionAllowed, false);
});
