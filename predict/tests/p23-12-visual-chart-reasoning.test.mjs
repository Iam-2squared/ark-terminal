import assert from 'node:assert/strict';
import {
  P23_12_VISUAL_REASONING_POLICY,
  PHASE57_P23_12_SAFETY,
  deriveVisualChartReasoning,
  renderMultiTimeframeChartSvg,
  buildMultimodalChartReasoningManifest,
} from '../daytrade/phase57-visual-chart-reasoning.js';

for (const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed','transmitted']) {
  assert.equal(PHASE57_P23_12_SAFETY[key], false, `${key} must remain false`);
}
assert.equal(P23_12_VISUAL_REASONING_POLICY.outcomeTuned, false);
assert.equal(P23_12_VISUAL_REASONING_POLICY.futureOutcomeUsed, false);
assert.equal(P23_12_VISUAL_REASONING_POLICY.scoreUsedAsEntryGate, false);
assert.equal(P23_12_VISUAL_REASONING_POLICY.externalVisionCallEnabled, false);

function makeBars() {
  const out = [];
  let price = 100;
  for (let day = 0; day < 34; day += 1) {
    const base = Date.UTC(2026, 5, 1 + day, 0, 0, 0);
    for (let i = 0; i < 24; i += 1) {
      const wave = Math.sin((day * 24 + i) / 9) * 0.08;
      const drift = 0.045;
      const open = price;
      const close = Math.max(1, open + drift + wave);
      const high = Math.max(open, close) + 0.10 + (i % 4) * 0.01;
      const low = Math.min(open, close) - 0.07;
      out.push({
        timestamp: new Date(base + i * 5 * 60 * 1000).toISOString(),
        open, high, low, close,
        volume: 1000 + i * 15 + day * 10,
      });
      price = close;
    }
  }
  return out;
}

const bars = makeBars();
const setupInfo = { setup: 'BREAKOUT_CONTINUATION_UP', directionSign: 1 };
const reasoning = deriveVisualChartReasoning({ symbol: 'TEST.T', bars5m: bars, setupInfo });
assert.equal(reasoning.status, 'VISUAL_REASONING_READY');
assert.equal(reasoning.symbol, 'TEST.T');
assert.equal(reasoning.direction, 'UP');
assert.ok(reasoning.score >= 0 && reasoning.score <= 1);
assert.ok(['V_A_CLEAN','V_B_GOOD','V_C_MIXED','V_D_WEAK'].includes(reasoning.band));
assert.equal(reasoning.futureBarsUsed, false);
assert.equal(reasoning.outcomeUsed, false);
assert.equal(reasoning.scoreUsedAsEntryGate, false);
assert.equal(reasoning.externalVisionCallUsed, false);
assert.ok(reasoning.sourceCounts.bars15m > 0);
assert.ok(reasoning.sourceCounts.bars60m >= 24);
assert.ok(reasoning.sourceCounts.bars1d >= 24);
assert.ok(Number.isFinite(reasoning.components.structureCoherence));
assert.ok(Number.isFinite(reasoning.components.spaceToObstacle));
assert.ok(Object.prototype.hasOwnProperty.call(reasoning.geometry, 'nearestObstacle'));

const repeated = deriveVisualChartReasoning({ symbol: 'TEST.T', bars5m: bars, setupInfo });
assert.equal(repeated.score, reasoning.score, 'visual score must be deterministic for the same causal prefix');
assert.deepEqual(repeated.components, reasoning.components);

const svg = renderMultiTimeframeChartSvg({ symbol: 'TEST.T', bars5m: bars, setupInfo, width: 800, height: 600 });
assert.match(svg, /^<svg /);
assert.match(svg, /5m/);
assert.match(svg, /15m/);
assert.match(svg, /60m/);
assert.match(svg, /1d completed only/);
assert.match(svg, /BREAKOUT_CONTINUATION_UP/);

const manifest = buildMultimodalChartReasoningManifest({ symbol: 'TEST.T', bars5m: bars, setupInfo });
assert.equal(manifest.schema, 'ARK_MULTIMODAL_CHART_REASONING_MANIFEST_V1');
assert.equal(manifest.externalVisionCallEnabled, false);
assert.equal(manifest.externalModelBinding, 'UNBOUND_UNTIL_CURRENT_API_IS_VERIFIED');
assert.equal(manifest.futureDataIncluded, false);
assert.equal(manifest.executableTradingInstructionAllowed, false);
assert.equal(manifest.recommendationAllowed, false);
assert.equal(manifest.transmitted, false);
assert.ok(manifest.reasoningOrder.indexOf('DESCRIBE_VISIBLE_MARKET_STRUCTURE') < manifest.reasoningOrder.indexOf('ONLY_AFTER_DESCRIPTION_COMPARE_HISTORICAL_EVIDENCE'));

console.log('P23.12 visual chart reasoning tests passed');
