import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeIntradayFrame } from '../daytrade/phase57-intraday-capture-replay.js';
import { buildIntradayFeatureLabelRows, buildIntradayLabelManifest } from '../daytrade/phase57-intraday-feature-labeling.js';

function frame(minute, close, high = close, low = close) {
  const ts = `2026-08-07T00:${String(minute).padStart(2,'0')}:00Z`;
  return normalizeIntradayFrame({
    symbol: '7203.T', sessionDate: '2026-08-07', capturedAt: ts,
    bar: { timestamp: ts, open: close - .2, high, low, close, volume: 1000 + minute },
    market: { last: close, bid: close - .1, ask: close + .1, volume: 10000 },
    book: { bestBid: close - .1, bestAsk: close + .1, bidSize: 1200, askSize: 900, bidDepth: 6000, askDepth: 4500 },
    ticks: [{ timestamp: ts, price: close, size: 100, side: 'BUY' }],
  });
}

test('P4 builds features only from history and labels from later frames', () => {
  const frames = [
    frame(0,100), frame(1,100.1), frame(2,100.2), frame(3,100.3),
    frame(4,100.35,100.38,100.2), frame(5,100.7,100.8,100.6), frame(6,100.9),
  ];
  const rows = buildIntradayFeatureLabelRows(frames,{horizonFrames:2,barrierBps:20,minHistoryBars:4});
  assert.ok(rows.length >= 1);
  const first = rows[0];
  assert.equal(first.symbol,'7203.T');
  assert.equal(first.label,1);
  assert.equal(first.labelDirection,'UPPER_FIRST');
  assert.ok(Date.parse(first.featureCutoff) < Date.parse(first.outcomeAt));
  assert.equal(first.pointInTimeValid,true);
});

test('P4 excludes same-frame ambiguous barrier touches and timeouts', () => {
  const ambiguous = [frame(0,100),frame(1,100),frame(2,100),frame(3,100),frame(4,100,100.3,99.7)];
  const rows = buildIntradayFeatureLabelRows(ambiguous,{horizonFrames:1,barrierBps:20,minHistoryBars:4});
  assert.equal(rows.length,0);
});

test('P4 manifest preserves all execution and write locks', () => {
  const manifest = buildIntradayLabelManifest([],{});
  for (const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed']) {
    assert.equal(manifest[key],false,key);
  }
  assert.equal(manifest.safety.paperTradingAllowed,false);
  assert.equal(manifest.transmitted,false);
  assert.equal(manifest.humanApprovalRequired,true);
  assert.equal(manifest.pointInTime.featureCutoffBeforeOutcomeRequired,true);
});
