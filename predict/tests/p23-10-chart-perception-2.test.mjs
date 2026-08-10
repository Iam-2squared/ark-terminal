import assert from 'node:assert/strict';
import {
  PHASE57_CHART_PERCEPTION_SAFETY,
  resampleBars,
  perceiveSingleTimeframe,
  buildMultiTimeframeChartPerception,
  buildChartReasoningPacket,
} from '../daytrade/phase57-chart-perception-2.js';

function barsFrom(values, { start = '2026-01-05T00:00:00.000Z', volume = 1000 } = {}) {
  const base = Date.parse(start);
  return values.map((close, index) => {
    const previous = index ? values[index - 1] : close;
    const open = Number(previous);
    const c = Number(close);
    const spread = Math.max(0.2, Math.abs(c - open) * 0.4 + 0.1);
    return {
      timestamp: new Date(base + index * 5 * 60 * 1000).toISOString(),
      open,
      high: Math.max(open, c) + spread,
      low: Math.min(open, c) - spread,
      close: c,
      volume: volume + index * 3,
    };
  });
}

function trendWithSwings({ start = 100, steps = 80, direction = 1 } = {}) {
  const values = [];
  for (let i = 0; i < steps; i += 1) {
    const trend = direction * i * 0.08;
    const wave = direction * Math.sin(i / 2.2) * 1.8;
    values.push(start + trend + wave);
  }
  return barsFrom(values);
}

{
  const source = barsFrom([100, 101, 102, 103, 104, 105]);
  const resampled = resampleBars(source, 3);
  assert.equal(resampled.length, 2);
  assert.equal(resampled[0].open, source[0].open);
  assert.equal(resampled[0].close, source[2].close);
  assert.equal(resampled[0].high, Math.max(...source.slice(0, 3).map(row => row.high)));
  assert.equal(resampled[0].volume, source.slice(0, 3).reduce((sum, row) => sum + row.volume, 0));
}

{
  const up = perceiveSingleTimeframe({ bars: trendWithSwings({ direction: 1 }), timeframe: '5m' });
  assert.equal(up.status, 'CHART_PERCEPTION_READY');
  assert.equal(up.structure.regime, 'UPTREND');
  assert.match(up.narrative, /UPTREND/);
  assert.equal(up.pointInTimeOnly, true);
  assert.equal(up.futureBarsUsed, false);
  assert.equal(up.outcomeUsed, false);
}

{
  const down = perceiveSingleTimeframe({ bars: trendWithSwings({ direction: -1 }), timeframe: '5m' });
  assert.equal(down.status, 'CHART_PERCEPTION_READY');
  assert.equal(down.structure.regime, 'DOWNTREND');
  assert.match(down.narrative, /DOWNTREND/);
}

{
  const insufficient = perceiveSingleTimeframe({ bars: barsFrom([100, 101, 102]), timeframe: '5m' });
  assert.equal(insufficient.status, 'OBSERVE');
  assert.deepEqual(insufficient.blockers, ['INSUFFICIENT_COMPLETED_BARS']);
}

{
  const longHistory = trendWithSwings({ direction: 1, steps: 420 });
  const mtf = buildMultiTimeframeChartPerception({ bars5m: longHistory });
  assert.equal(mtf.status, 'MULTI_TIMEFRAME_PERCEPTION_READY');
  assert.equal(mtf.timeframes['5m'].status, 'CHART_PERCEPTION_READY');
  assert.equal(mtf.timeframes['15m'].status, 'CHART_PERCEPTION_READY');
  assert.equal(mtf.timeframes['60m'].status, 'CHART_PERCEPTION_READY');
  assert.equal(mtf.completedBarsOnly, true);
  assert.equal(mtf.futureBarsUsed, false);
  assert.equal(mtf.outcomeUsed, false);
  assert.equal(mtf.alignment.direction, 'UP');
}

{
  const history = trendWithSwings({ direction: 1, steps: 420 });
  const packet = buildChartReasoningPacket({ symbol: 'TEST.T', bars5m: history });
  assert.equal(packet.schema, 'ARK_CHART_REASONING_PACKET_V1');
  assert.equal(packet.symbol, 'TEST.T');
  assert.equal(packet.futureDataIncluded, false);
  assert.equal(packet.executableTradingInstructionAllowed, false);
  assert.equal(packet.recommendationAllowed, false);
  assert.ok(packet.instructionsForReasoner.some(line => line.includes('chart state')));
  assert.ok(packet.instructionsForReasoner.some(line => line.includes('Do not output an executable order')));
}

for (const key of [
  'executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed', 'rssOrderFunctionAllowed',
  'liveTradingAllowed', 'paperTradingAllowed', 'automaticPromotionAllowed', 'productionUpdateAllowed',
  'overnightHoldingAllowed',
]) assert.equal(PHASE57_CHART_PERCEPTION_SAFETY[key], false, `${key} must remain false`);

console.log('P23.10 chart perception 2 tests passed');
