import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { buildHybridP21Input, P21_OPTIONS, P21_HORIZONS } from '../lib/phase57-hybrid-p21-adapter.mjs';
import { MODEL_DIGEST, FREEZE_DIGEST } from '../lib/phase57-hybrid-p21-baseline.mjs';
import { buildProspectiveP21FeatureFeed } from '../../predict/daytrade/phase57-p21-prospective-feature-feed.js';
import { buildProspectiveP21FrozenDecision } from '../../predict/daytrade/phase57-p21-prospective-frozen-base.js';

// Entirely invented OHLCV. No archives, labels, fitted models or historical outputs.
function fixture() {
  const start = Date.parse('2026-08-13T09:00:00+09:00');
  const contextBars = Array.from({ length: 6 }, (_, i) => ({
    timestamp: new Date(start + i * 300000).toISOString(), availableAt: new Date(start + (i + 1) * 300000).toISOString(),
    open: 100 + i, high: 102 + i, low: 99 + i, close: 101 + i, volume: 1000 + i,
  }));
  return { symbol: '1234.T', sessionDate: '2026-08-13', decisionTimestamp: '2026-08-13T09:30:00+09:00',
    contextBars, selectorFreezeSHA: FREEZE_DIGEST, sourceClass: 'SYNTHETIC_CONTRACT_TEST',
    selection: { modelDigest: MODEL_DIGEST, featureCutoff: '2026-08-13T00:30:00.000Z', selected: [
      { symbol: '1234.T', hybridRank: 2, hybridScore: 0.75, currentPrice: 106 },
    ] },
  };
}
const directFeed = f => buildProspectiveP21FeatureFeed({ symbol: f.symbol, sessionDate: f.sessionDate, bars5m: f.contextBars, horizons: P21_HORIZONS, latestBarClosed: true });
test('input mapping matches the unchanged feature feed at every horizon', () => {
  const f = fixture(), before = structuredClone(f), mapped = buildHybridP21Input(f);
  assert.deepEqual(mapped.currentRowsByHorizon, directFeed(f).currentRowsByHorizon);
  assert.deepEqual(f, before);
  assert.equal(mapped.lineage.p21LegacyFeatureCutoff, '2026-08-13T00:25:00.000Z');
  assert.equal(mapped.lineage.contextAvailableAt, '2026-08-13T00:30:00.000Z');
  assert.equal(mapped.lineage.hybridRank, 2);
  assert.equal(mapped.lineage.hybridScore, 0.75);
  assert.equal(mapped.lineage.sourceClass, 'SYNTHETIC_CONTRACT_TEST');
  assert.ok(Object.values(mapped.safety).every(x => x === false));
});
test('rank and score remain lineage only; no injection into P21 features', () => {
  const a = fixture(), b = fixture(); b.selection.selected[0].hybridRank = 8; b.selection.selected[0].hybridScore = -2;
  assert.deepEqual(buildHybridP21Input(a).currentRowsByHorizon, buildHybridP21Input(b).currentRowsByHorizon);
});
test('unchanged P21 blocks both direct and mapped input without prior history', () => {
  const f = fixture(), mapped = buildHybridP21Input(f);
  const direct = buildProspectiveP21FrozenDecision({ currentRowsByHorizon: directFeed(f).currentRowsByHorizon, options: P21_OPTIONS });
  const adapted = buildProspectiveP21FrozenDecision(mapped);
  assert.deepEqual(adapted, direct);
  assert.equal(adapted.status, 'BLOCKED_NO_FULLY_REALIZED_PRIOR_HISTORY');
});
// An explicitly synthetic cached bundle isolates output mapping. It is NOT proof
// of causal prior selection/refit and cannot satisfy Gate 2 or historical parity.
function contractCache(cutoff, probability) {
  const picked = { horizonBars: 3, featureFamily: 'SYNTHETIC_CONTRACT', featureKeys: ['returnFromOpen'], modelType: 'SYNTHETIC_NO_FIT', configId: 'SYNTHETIC_NO_FIT', threshold: 0.6 };
  return new Map([[cutoff, { status: 'PRIOR_ONLY_MODEL_READY', complete: true, selection: { selected: picked }, picked,
    trainRows: [], predictor: () => probability, maxPriorOutcomeAt: null, artifactSha256: 'SYNTHETIC_NOT_A_PRIOR_PACK', modelId: 'SYNTHETIC_NO_FIT' }]]);
}
for (const [name, probability, direction] of [['LONG', 0.8, 1], ['SHORT', 0.2, -1], ['ABSTAIN', 0.5, 0]]) {
  test(`synthetic output-stage ${name} parity, all decision fields unchanged`, () => {
    const f = fixture(), feed = directFeed(f), mapped = buildHybridP21Input(f);
    const direct = buildProspectiveP21FrozenDecision({ currentRowsByHorizon: feed.currentRowsByHorizon, options: P21_OPTIONS, priorOnlyCache: contractCache(feed.featureCutoff, probability) });
    const adapted = buildProspectiveP21FrozenDecision({ ...mapped, priorOnlyCache: contractCache(feed.featureCutoff, probability) });
    assert.deepEqual(adapted, direct);
    assert.equal(adapted.decision.direction, direction);
    for (const key of ['signalEligible', 'probability', 'selectedHorizonBars', 'selectedFeatureFamily', 'selectedModelType', 'selectedConfigId', 'selectedThreshold']) assert.ok(Object.hasOwn(adapted.decision.context, key));
    assert.ok(Object.hasOwn(adapted.decision, 'confidence'));
  });
}
const bad = [
  ['future bar', f => { f.contextBars.at(-1).timestamp = f.decisionTimestamp; }, /BAR_NOT_COMPLETED/],
  ['unavailable completed bar', f => { f.contextBars.at(-1).availableAt = '2026-08-13T09:31:00+09:00'; }, /BAR_NOT_COMPLETED/],
  ['availability before close', f => { f.contextBars[0].availableAt = f.contextBars[0].timestamp; }, /BAR_NOT_COMPLETED/],
  ['missing volume', f => { delete f.contextBars[0].volume; }, /INVALID_OHLCV/],
  ['duplicate bar', f => { f.contextBars[1] = { ...f.contextBars[0] }; }, /UNSORTED_OR_DUPLICATE/],
  ['wrong symbol', f => { f.symbol = '9999.T'; }, /NOT_A_HYBRID/],
  ['wrong selection time', f => { f.selection.featureCutoff = '2026-08-13T09:35:00+09:00'; }, /TIME_MISMATCH/],
  ['price mismatch', f => { f.selection.selected[0].currentPrice = 107; }, /PRICE_REFERENCE_MISMATCH/],
  ['changed model digest', f => { f.selection.modelDigest = 'other'; }, /FROZEN_SELECTOR_MISMATCH/],
  ['changed freeze', f => { f.selectorFreezeSHA = 'other'; }, /FROZEN_SELECTOR_MISMATCH/],
  ['hidden future label', f => { f.selection.selected[0].diagnostics = { label: 1 }; }, /CURRENT_INPUT_HAS_OUTCOME/],
  ['cross-session bar', f => { f.contextBars[0].timestamp = '2026-08-12T09:00:00+09:00'; }, /CROSS_SESSION/],
  ['no source classification', f => { delete f.sourceClass; }, /SOURCE_CLASS_REQUIRED/],
];
for (const [name, mutate, pattern] of bad) test(`reject ${name}`, () => { const f = fixture(); mutate(f); assert.throws(() => buildHybridP21Input(f), pattern); });
test('legacy implementation and options remain pinned to audited source blobs', () => {
  const pins = {
    'predict/daytrade/phase57-p21-prospective-frozen-base.js': '406ee8121a7b7b2b61ca18853fa51c1569c71cd0',
    'predict/daytrade/phase57-p21-prospective-feature-feed.js': '65a93fa56c89c08fcf82deeaf068513d028d20ec',
    'predict/scalping/phase58-phase57-prospective-pipeline.js': 'a79789b9bc25559ec63ed28f19f281eb563ace35',
  };
  for (const [path, expected] of Object.entries(pins)) {
    const bytes = readFileSync(new URL('../../' + path, import.meta.url));
    assert.equal(createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex'), expected, path);
  }
  const text = readFileSync(new URL('../../predict/scalping/phase58-phase57-prospective-pipeline.js', import.meta.url), 'utf8');
  const policy = text.split('export const PHASE58_P13_FROZEN_POLICY=Object.freeze({')[1].split('export const PHASE58_TARGET_MODES')[0];
  for (const [key, value] of Object.entries(P21_OPTIONS)) {
    const match = policy.match(new RegExp(key + ':([^\\n]+)'));
    assert.ok(match, key);
    const expression = match[1].trim().replace(/,$/, '').replace(/^Object\.freeze\((.*)\)$/, '$1');
    assert.deepEqual(JSON.parse(expression), value);
  }
});
