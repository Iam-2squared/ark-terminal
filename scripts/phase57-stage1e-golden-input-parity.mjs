import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {gunzipSync} from 'node:zlib';
import {buildDirectionFeatures, CONTRACT_SHA256, FEATURES, sha256} from './lib/phase57-minimal-stateful-entry.mjs';
import {ALLOWED_SESSIONS, SAFETY} from './lib/phase57-stage1e-controlled-zip-extractor.mjs';

const readGzipJson = (file) => JSON.parse(gunzipSync(fs.readFileSync(file)));
const ms = (value) => { const parsed = Date.parse(value); assert(Number.isFinite(parsed), 'INVALID_TIMESTAMP'); return parsed; };
const timeJst = (value) => new Date(ms(value) + 32400000).toISOString().slice(11, 16);
const dateJst = (value) => new Date(ms(value) + 32400000).toISOString().slice(0, 10);

function sameNumber(a, b) {
  return typeof a === 'number' && Number.isFinite(a) && typeof b === 'number' && Number.isFinite(b) && a === b;
}

function originalOrderFeatureSha(row) {
  return sha256({
    contractSha256: row.contractSha256,
    symbol: row.symbol,
    sessionDate: row.sessionDate,
    decisionTimestamp: row.decisionTimestamp,
    direction: row.direction,
    features: Object.fromEntries(FEATURES.map((key) => [key, row.features[key]])),
    prefixSha256: row.prefixSha256,
    latestAvailableAt: row.latestAvailableAt,
    selectorModelDigest: row.selectorModelDigest,
    selectorFreezeSHA: row.selectorFreezeSHA,
  });
}

function compareExactFeatureRow(golden, recomputed) {
  const mismatches = [];
  for (const key of ['contractSha256', 'symbol', 'sessionDate', 'decisionTimestamp', 'direction', 'prefixSha256', 'latestAvailableAt', 'selectorModelDigest', 'selectorFreezeSHA']) {
    if (golden[key] !== recomputed[key]) mismatches.push(key);
  }
  if (golden.featureSha256 !== originalOrderFeatureSha(golden)) mismatches.push('goldenFeatureShaIntegrity');
  if (golden.featureSha256 !== recomputed.featureSha256) mismatches.push('featureSha256');
  if (JSON.stringify(Object.keys(golden.features).sort()) !== JSON.stringify(Object.keys(recomputed.features).sort())) mismatches.push('featureKeys');
  for (const key of FEATURES) if (!sameNumber(golden.features[key], recomputed.features[key])) mismatches.push(`feature:${key}`);
  return mismatches;
}

export function auditGoldenSession({subsetDir, sessionDate}) {
  assert(ALLOWED_SESSIONS.includes(sessionDate), 'UNAPPROVED_SESSION');
  const features = readGzipJson(path.join(subsetDir, `${sessionDate}.features.json.gz`));
  const entries = readGzipJson(path.join(subsetDir, `${sessionDate}.bars.json.gz`));
  const manifest = JSON.parse(fs.readFileSync(path.join(subsetDir, `${sessionDate}.manifest.json`)));
  assert.equal(features.sessionDate, sessionDate);
  assert.equal(manifest.sessionDate, sessionDate);
  assert.equal(manifest.labelsGenerated, false, 'SOURCE_NOT_PRE_OUTCOME');
  assert.equal(manifest.sourceParity, true, 'SOURCE_PARITY_NOT_DECLARED');
  assert.deepEqual(manifest.safety, SAFETY);

  const barsBySymbol = new Map(entries.map((entry) => [entry.symbol, entry.bars]));
  let barCount = 0;
  let pitViolations = 0;
  let timestampViolations = 0;
  for (const entry of entries) {
    assert.equal(entry.symbol, entry.bars[0]?.symbol ?? entry.symbol);
    let previous = -Infinity;
    for (const bar of entry.bars) {
      barCount += 1;
      const start = ms(bar.timestamp), available = ms(bar.availableAt), clock = timeJst(bar.timestamp);
      if (dateJst(bar.timestamp) !== sessionDate || start <= previous || start % 300000 !== 0) timestampViolations += 1;
      if (!((clock >= '09:00' && clock < '11:30') || (clock >= '12:30' && clock < '15:30'))) timestampViolations += 1;
      if (available !== start + 300000) pitViolations += 1;
      previous = start;
    }
  }

  let featurePairs = 0;
  let featureRows = 0;
  let featureMismatches = 0;
  let jsonNegativeZeroNormalizations = 0;
  const mismatchTaxonomy = {};
  let referencePriceMismatches = 0;
  for (const event of features.events) {
    assert.equal(event.sessionDate, sessionDate);
    if (!event.directionFeatures) continue;
    assert.equal(event.directionFeatures.length, 2);
    const prefix = (barsBySymbol.get(event.symbol) ?? []).filter((bar) => ms(bar.availableAt) <= ms(event.decisionTimestamp) && ms(bar.timestamp) + 300000 <= ms(event.decisionTimestamp));
    const recomputed = [1, -1].map((direction) => buildDirectionFeatures({
      symbol: event.symbol,
      decisionTimestamp: event.decisionTimestamp,
      bars: prefix,
      rank: event.hybridRank,
      score: event.hybridScore,
      priceReference: event.priceReference,
      firstSelectionTimestamp: event.firstSelectionTimestamp,
      priorSelectionCount: event.priorSelectionCount,
      direction,
    }));
    let pairMismatch = false;
    for (let i = 0; i < 2; i += 1) {
      const mismatches = compareExactFeatureRow(event.directionFeatures[i], recomputed[i]);
      pairMismatch ||= mismatches.length > 0;
      for (const mismatch of mismatches) mismatchTaxonomy[mismatch] = (mismatchTaxonomy[mismatch] ?? 0) + 1;
      for (const key of FEATURES) {
        if (sameNumber(event.directionFeatures[i].features[key], recomputed[i].features[key]) && !Object.is(event.directionFeatures[i].features[key], recomputed[i].features[key])) jsonNegativeZeroNormalizations += 1;
      }
    }
    if (pairMismatch) featureMismatches += 1;
    const last = prefix.at(-1);
    if (!last || !sameNumber(last.close, event.priceReference)) referencePriceMismatches += 1;
    featurePairs += 1;
    featureRows += 2;
  }

  const eventsByTime = new Map();
  for (const event of features.events) {
    if (!eventsByTime.has(event.decisionTimestamp)) eventsByTime.set(event.decisionTimestamp, []);
    eventsByTime.get(event.decisionTimestamp).push(event);
  }
  const states = new Map();
  let stateComparisons = 0;
  let stateMismatches = 0;
  let membershipCountComparisons = 0;
  let membershipCountMismatches = 0;
  let rankViolations = 0;
  for (const point of [...features.points].sort((a, b) => ms(a.decisionTimestamp) - ms(b.decisionTimestamp))) {
    const events = eventsByTime.get(point.decisionTimestamp) ?? [];
    membershipCountComparisons += 1;
    if (events.length !== point.selectedCount) membershipCountMismatches += 1;
    const ranks = events.map((event) => event.hybridRank);
    if (new Set(ranks).size !== ranks.length || ranks.some((rank) => !Number.isInteger(rank) || rank < 1)) rankViolations += 1;
    const present = new Set(events.map((event) => event.symbol));
    for (const state of states.values()) if (state.state === 'WATCHING' && !present.has(state.symbol)) state.state = 'EXPIRED';
    for (const event of events) {
      const state = states.get(event.symbol) ?? {symbol: event.symbol, state: 'UNSEEN', count: 0, first: event.decisionTimestamp, previous: null, entered: null};
      const before = state.state;
      let after = before === 'UNSEEN' ? 'WATCHING' : before;
      if (event.decision.action === 'ENTER' && after === 'WATCHING') after = 'ENTERED';
      stateComparisons += 1;
      if (event.stateBefore !== before || event.stateAfter !== after || event.priorSelectionCount !== state.count || event.selectionIndex !== state.count + 1 || event.firstSelectionTimestamp !== state.first || event.previousSelectionTimestamp !== state.previous) stateMismatches += 1;
      state.state = after;
      state.count += 1;
      state.previous = event.decisionTimestamp;
      if (after === 'ENTERED') state.entered = event.firstEnterTimestamp;
      states.set(event.symbol, state);
    }
  }

  const decisions = features.events.filter((event) => event.decision?.action === 'ENTER');
  const modelAppliedRows = features.events.filter((event) => ['ENTER', 'WATCH'].includes(event.decision?.action) && event.decision?.reason !== 'MODEL_UNAVAILABLE' && event.decision?.reason !== 'BLOCKED_FEATURES').length;
  return {
    sessionDate,
    sourceDeclaredPreOutcome: manifest.labelsGenerated === false,
    goldenEventRows: features.events.length,
    usedSymbols: entries.length,
    dataBars: {rows: barCount, timestampViolations, pitViolations, status: timestampViolations === 0 && pitViolations === 0 ? 'PASS' : 'FAIL'},
    hybridOutput: {membershipCountComparisons, membershipCountMismatches, rankViolations, selectionDigestComparisons: 0, status: membershipCountMismatches === 0 && rankViolations === 0 ? 'PARTIAL_EVENT_MEMBERSHIP_AND_RANK_CONSISTENT_NO_INDEPENDENT_FULL_UNIVERSE_REPLAY' : 'FAIL'},
    mshFeatures: {contractSha256: CONTRACT_SHA256, featurePairs, featureRows, featureMismatches, mismatchTaxonomy, jsonNegativeZeroNormalizations, exactNumericTolerance: 0, status: featureMismatches === 0 ? 'PASS_EXACT_NUMERIC_JSON_SEMANTICS' : 'FAIL'},
    mshState: {stateComparisons, stateMismatches, status: stateMismatches === 0 ? 'PASS_EXACT_CHRONOLOGICAL_RECONSTRUCTION' : 'FAIL'},
    entryEvents: {storedFirstEnterRows: decisions.length, modelAppliedRows, referencePriceComparisons: featurePairs, referencePriceMismatches, status: modelAppliedRows > 0 && referencePriceMismatches === 0 ? 'PARTIAL' : 'NOT_RECOVERABLE_PRE_FIT_BUNDLE_HAS_NO_FROZEN_MODEL_DECISIONS'},
    safety: SAFETY,
  };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const root = process.argv[2];
  assert(root, 'SUBSET_ROOT_REQUIRED');
  const sessions = ALLOWED_SESSIONS.map((sessionDate) => auditGoldenSession({subsetDir: path.join(root, `subset-${sessionDate}`), sessionDate}));
  const result = {
    status: sessions.every((row) => row.dataBars.status === 'PASS' && row.mshFeatures.status.startsWith('PASS') && row.mshState.status.startsWith('PASS'))
      ? 'CONTROLLED_EXTRACTION_PARITY_PARTIAL'
      : 'PARITY_FAIL',
    exactFloatTolerance: 0,
    sessions,
    totals: {
      goldenEventRows: sessions.reduce((sum, row) => sum + row.goldenEventRows, 0),
      featureRows: sessions.reduce((sum, row) => sum + row.mshFeatures.featureRows, 0),
      featureMismatches: sessions.reduce((sum, row) => sum + row.mshFeatures.featureMismatches, 0),
      stateComparisons: sessions.reduce((sum, row) => sum + row.mshState.stateComparisons, 0),
      stateMismatches: sessions.reduce((sum, row) => sum + row.mshState.stateMismatches, 0),
      pitViolations: sessions.reduce((sum, row) => sum + row.dataBars.pitViolations, 0),
      entryModelAppliedRows: sessions.reduce((sum, row) => sum + row.entryEvents.modelAppliedRows, 0),
    },
    safety: SAFETY,
  };
  console.log(JSON.stringify(result));
}
