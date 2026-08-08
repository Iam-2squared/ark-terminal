import test from 'node:test';
import assert from 'node:assert/strict';
import { analyzeChartSetupContext, PHASE56_2_SAFETY } from '../chart/phase56-setup-context.js';

function baseBars() {
  return Array.from({ length: 14 }, (_, i) => ({
    time: i,
    open: 100 + i * 0.2,
    high: 101 + i * 0.2,
    low: 99 + i * 0.2,
    close: 100.4 + i * 0.2,
    volume: 1000,
    vwap: 100.2 + i * 0.2,
  }));
}

test('Phase56.2 detects descriptive breakout context without execution', () => {
  const bars = baseBars();
  const last = bars.at(-1);
  last.open = 102.4;
  last.low = 102.3;
  last.high = 106;
  last.close = 105.5;
  last.volume = 2200;
  const result = analyzeChartSetupContext({ bars, swingRadius: 1 });
  assert.equal(result.status, 'SETUP_CONTEXT_READY');
  assert.ok(result.labels.includes('BREAKOUT_ABOVE_LOOKBACK'));
  assert.equal(result.descriptiveOnly, true);
  assert.equal(result.executionAllowed, false);
  assert.equal(result.transmitted, false);
});

test('Phase56.2 can flag VWAP proximity as context only', () => {
  const bars = baseBars();
  const last = bars.at(-1);
  last.vwap = last.close * 0.999;
  const result = analyzeChartSetupContext({ bars, swingRadius: 1, proximityPct: 0.004 });
  assert.equal(result.status, 'SETUP_CONTEXT_READY');
  assert.ok(result.labels.includes('NEAR_VWAP'));
  assert.equal(result.liveTradingAllowed, false);
});

test('Phase56.2 fails closed when price action is not ready', () => {
  const result = analyzeChartSetupContext({ bars: baseBars().slice(0, 2) });
  assert.equal(result.status, 'OBSERVE');
  assert.ok(result.blockers.includes('PRICE_ACTION_NOT_READY'));
  assert.equal(result.executionAllowed, false);
});

test('Phase56.2 safety boundary stays read only', () => {
  assert.equal(PHASE56_2_SAFETY.brokerWriteAllowed, false);
  assert.equal(PHASE56_2_SAFETY.excelOrderWriteAllowed, false);
  assert.equal(PHASE56_2_SAFETY.rssOrderFunctionAllowed, false);
  assert.equal(PHASE56_2_SAFETY.automaticPromotionAllowed, false);
});
