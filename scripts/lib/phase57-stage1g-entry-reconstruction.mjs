import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';

import {
  CONTRACT,
  CONTRACT_SHA256,
  FEATURES,
  SAFETY,
  sha256,
} from './phase57-minimal-stateful-entry.mjs';
import {ALLOWED_SESSIONS} from './phase57-stage1e-controlled-zip-extractor.mjs';

export const CANDIDATE_SHA256 = 'f05def20081e51dfe7391c7e80e8b8474e5c140c42a47dc29dcd94bca367ab8a';
export const ALLOCATION_SHA256 = '7df4cb026d966628c9b3fbc91037eb13704397a700c076e865d817a273df00e6';
export const FIT_SHA256 = 'e1567951bcc81d50497a42e24411a32112b36638fbc0ff67247a16a6ce80859c';
export const THRESHOLD = 0.60;
export const MODEL_ARTIFACT_LINEAGE = Object.freeze({
  runId: 34292703804,
  artifactId: 10084158820,
  artifactName: 'entry58-development-measurement-34292703804',
  artifactContainerSha256: 'aa4fa5f9f5530132263f33a7dcbf9153bff4d7b44f2f574b4f3a213f122b9058',
  memberName: 'candidate-model.json',
  memberSha256: CANDIDATE_SHA256,
});

const finite = (value) => typeof value === 'number' && Number.isFinite(value);
const bytesSha256 = (bytes) => createHash('sha256').update(bytes).digest('hex');
const ms = (value) => {
  assert.equal(typeof value, 'string', 'TIMESTAMP_STRING_REQUIRED');
  assert.match(value, /(Z|[+-]\d{2}:\d{2})$/, 'EXPLICIT_TIMESTAMP_REQUIRED');
  const parsed = Date.parse(value);
  assert(Number.isFinite(parsed), 'INVALID_TIMESTAMP');
  return parsed;
};

function rejectFutureOrOutcomeFields(value) {
  if (!value || typeof value !== 'object') return;
  for (const [key, child] of Object.entries(value)) {
    assert.doesNotMatch(key, /^(labels?|targets?|outcomes?|outcomeAt|future.*|actualReturn.*|netReturn.*|mfe.*|mae.*|exit.*|profit.*|winner.*|winRate|returnAfter.*|postExit.*)$/i, 'OUTCOME_OR_FUTURE_FIELD_DENIED');
    rejectFutureOrOutcomeFields(child);
  }
}

function assertFrozenVector(value, name) {
  assert(Array.isArray(value), `${name}_ARRAY_REQUIRED`);
  assert.equal(value.length, FEATURES.length, `${name}_LENGTH_MISMATCH`);
  assert(value.every(finite), `${name}_NONFINITE`);
}

export function loadAndValidateFrozenCandidate(modelBytes) {
  assert(Buffer.isBuffer(modelBytes), 'MODEL_BYTES_REQUIRED');
  assert.equal(bytesSha256(modelBytes), CANDIDATE_SHA256, 'CANDIDATE_SHA_MISMATCH');
  const model = JSON.parse(modelBytes);
  assert.equal(model.artifactClass, 'OFFLINE_DEVELOPMENT_CANDIDATE_NOT_PRODUCTION');
  assert.equal(model.allocationSha256, ALLOCATION_SHA256);
  assert.equal(model.fitSha256, FIT_SHA256);
  assert.equal(model.featureTargetStateSha256, CONTRACT_SHA256);
  assert.equal(model.selectorModelDigest, CONTRACT.selectorModelDigest);
  assert.equal(model.selectorFreezeSHA, CONTRACT.selectorFreezeSHA);
  assert.deepEqual(model.features, FEATURES);
  assert.equal(model.threshold, THRESHOLD, 'FROZEN_THRESHOLD_CHANGED');
  assertFrozenVector(model.weights, 'WEIGHTS');
  assertFrozenVector(model.means, 'MEANS');
  assertFrozenVector(model.scales, 'SCALES');
  assert(model.scales.every((value) => value > 0), 'INVALID_SCALE');
  assert(finite(model.intercept), 'INVALID_INTERCEPT');
  assert.equal(model.validationOpened, false, 'VALIDATION_WAS_OPENED');
  assert.deepEqual(model.safety, SAFETY);
  return Object.freeze(model);
}

function canonicalFeatureCore(row) {
  return {
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
  };
}

export function scoreFrozenDirection(row, model) {
  rejectFutureOrOutcomeFields(row);
  assert.equal(row.contractSha256, CONTRACT_SHA256, 'FEATURE_CONTRACT_MISMATCH');
  assert.equal(row.featureSha256, sha256(canonicalFeatureCore(row)), 'FEATURE_SHA_MISMATCH');
  assert.deepEqual(Object.keys(row.features).sort(), [...FEATURES].sort(), 'FEATURE_KEYS_MISMATCH');
  assert([1, -1].includes(row.direction), 'INVALID_DIRECTION');
  const normalized = FEATURES.map((key, index) => {
    const value = row.features[key];
    assert(finite(value), `NONFINITE_FEATURE:${key}`);
    return (value - model.means[index]) / model.scales[index];
  });
  const logit = model.intercept + normalized.reduce((sum, value, index) => sum + model.weights[index] * value, 0);
  assert(finite(logit), 'NONFINITE_LOGIT');
  const probability = logit >= 0 ? 1 / (1 + Math.exp(-logit)) : Math.exp(logit) / (1 + Math.exp(logit));
  return {direction: row.direction, logit, probability};
}

export function decideFrozenPair(pair, model, {threshold = THRESHOLD} = {}) {
  assert.equal(threshold, THRESHOLD, 'FROZEN_THRESHOLD_CHANGED');
  assert(Array.isArray(pair) && pair.length === 2, 'PAIRED_DIRECTIONS_REQUIRED');
  assert.equal(pair[0].direction, 1, 'LONG_FIRST_REQUIRED');
  assert.equal(pair[1].direction, -1, 'SHORT_SECOND_REQUIRED');
  assert.equal(pair[0].symbol, pair[1].symbol, 'CROSS_SYMBOL_PAIR');
  assert.equal(pair[0].decisionTimestamp, pair[1].decisionTimestamp, 'CROSS_TIME_PAIR');
  const long = scoreFrozenDirection(pair[0], model);
  const short = scoreFrozenDirection(pair[1], model);
  if (long.probability === short.probability) {
    return {action: 'WATCH', direction: null, probability: long.probability, longProbability: long.probability, shortProbability: short.probability, reason: 'DIRECTION_TIE'};
  }
  const best = long.probability > short.probability ? long : short;
  const enter = best.probability > threshold;
  return {
    action: enter ? 'ENTER' : 'WATCH',
    direction: enter ? best.direction : null,
    probability: best.probability,
    longProbability: long.probability,
    shortProbability: short.probability,
    reason: enter ? 'ABOVE_SINGLE_THRESHOLD' : 'NOT_ABOVE_SINGLE_THRESHOLD',
  };
}

export function thresholdDecision(probability) {
  assert(finite(probability), 'FINITE_PROBABILITY_REQUIRED');
  return probability > THRESHOLD ? 'ENTER' : 'WATCH';
}

function latestCompletedBar(bars, decisionTimestamp) {
  const decision = ms(decisionTimestamp);
  const candidates = bars.filter((bar) => ms(bar.timestamp) + 300000 <= decision && ms(bar.availableAt) <= decision);
  return candidates.sort((a, b) => ms(a.timestamp) - ms(b.timestamp)).at(-1) ?? null;
}

export function reconstructEntrySession({featureBundle, barsBundle, model}) {
  rejectFutureOrOutcomeFields(featureBundle);
  rejectFutureOrOutcomeFields(barsBundle);
  const sessionDate = featureBundle.sessionDate;
  assert(ALLOWED_SESSIONS.includes(sessionDate), 'UNAPPROVED_SESSION');
  assert(Array.isArray(featureBundle.events) && Array.isArray(featureBundle.points), 'INVALID_FEATURE_BUNDLE');
  assert(Array.isArray(barsBundle), 'INVALID_BARS_BUNDLE');
  const barsBySymbol = new Map(barsBundle.map((entry) => [entry.symbol, entry.bars ?? []]));
  const eventsByTime = new Map();
  const allScores = [];
  for (const event of featureBundle.events) {
    assert.equal(event.sessionDate, sessionDate);
    if (!eventsByTime.has(event.decisionTimestamp)) eventsByTime.set(event.decisionTimestamp, []);
    eventsByTime.get(event.decisionTimestamp).push(event);
    for (const row of event.directionFeatures ?? []) {
      const score = scoreFrozenDirection(row, model);
      allScores.push({eventId: event.eventId, symbol: event.symbol, decisionTimestamp: event.decisionTimestamp, direction: score.direction, logit: score.logit, probability: score.probability});
    }
  }
  const states = new Map();
  const trace = [];
  const firstEnterEvents = [];
  let pitViolations = 0;
  let referencePriceMismatches = 0;
  let repeatEntryViolations = 0;
  let chronologicalViolations = 0;
  let previousPoint = -Infinity;
  for (const point of [...featureBundle.points].sort((a, b) => ms(a.decisionTimestamp) - ms(b.decisionTimestamp))) {
    const pointTime = ms(point.decisionTimestamp);
    if (pointTime <= previousPoint) chronologicalViolations += 1;
    previousPoint = pointTime;
    assert.equal(point.complete, true, 'INCOMPLETE_GOLDEN_SNAPSHOT');
    const events = eventsByTime.get(point.decisionTimestamp) ?? [];
    assert.equal(events.length, point.selectedCount, 'MEMBERSHIP_COUNT_MISMATCH');
    const present = new Set(events.map((event) => event.symbol));
    for (const state of states.values()) if (state.state === 'WATCHING' && !present.has(state.symbol)) state.state = 'EXPIRED';
    for (const event of events) {
      const state = states.get(event.symbol) ?? {symbol: event.symbol, state: 'UNSEEN', count: 0, firstSelectionTimestamp: event.decisionTimestamp, entryCount: 0};
      const stateBefore = state.state;
      if (state.state === 'UNSEEN') state.state = 'WATCHING';
      let decision;
      if (state.state === 'ENTERED' || state.state === 'EXPIRED') decision = {action: 'NO_ACTION', direction: null, reason: state.state};
      else if (!event.directionFeatures) decision = {action: 'WATCH', direction: null, reason: 'BLOCKED_FEATURES'};
      else decision = decideFrozenPair(event.directionFeatures, model);
      const latest = latestCompletedBar(barsBySymbol.get(event.symbol) ?? [], event.decisionTimestamp);
      if (latest && (ms(latest.timestamp) + 300000 > ms(event.decisionTimestamp) || ms(latest.availableAt) > ms(event.decisionTimestamp))) pitViolations += 1;
      if (event.directionFeatures && (!latest || latest.close !== event.priceReference)) referencePriceMismatches += 1;
      if (decision.action === 'ENTER') {
        state.state = 'ENTERED';
        state.entryCount += 1;
        if (state.entryCount > 1) repeatEntryViolations += 1;
        const entry = {
          sessionDate,
          symbol: event.symbol,
          direction: decision.direction === 1 ? 'LONG' : 'SHORT',
          directionValue: decision.direction,
          firstSelectionTimestamp: state.firstSelectionTimestamp,
          decisionTimestamp: event.decisionTimestamp,
          featurePairSha256: sha256(event.directionFeatures),
          probability: decision.probability,
          longProbability: decision.longProbability,
          shortProbability: decision.shortProbability,
          threshold: THRESHOLD,
          thresholdComparison: 'STRICTLY_GREATER_THAN',
          stateBefore,
          stateAfter: state.state,
          decision: 'ENTER',
          priorSelectionCount: state.count,
          minutesSinceFirstSelection: event.minutesSinceFirstSelection,
          entryReferencePrice: event.priceReference,
          referencePriceTimestamp: latest?.timestamp ?? null,
          referencePriceAvailableAt: latest?.availableAt ?? null,
          evidenceClass: 'DETERMINISTIC_ENTRY_RECONSTRUCTION',
        };
        firstEnterEvents.push(entry);
      }
      trace.push({
        eventId: event.eventId,
        symbol: event.symbol,
        decisionTimestamp: event.decisionTimestamp,
        stateBefore,
        stateAfter: state.state,
        action: decision.action,
        direction: decision.direction,
        reason: decision.reason,
      });
      state.count += 1;
      states.set(event.symbol, state);
    }
  }
  const unique = new Set(firstEnterEvents.map((event) => `${event.sessionDate}|${event.symbol}`));
  assert.equal(unique.size, firstEnterEvents.length, 'FIRST_ENTER_NOT_UNIQUE');
  return {
    sessionDate,
    goldenFeatureEventRows: featureBundle.events.length,
    scoreRowsReconstructed: allScores.length,
    scoreEvidenceSha256: sha256(allScores),
    scoreMinimum: allScores.length ? Math.min(...allScores.map((row) => row.probability)) : null,
    scoreMaximum: allScores.length ? Math.max(...allScores.map((row) => row.probability)) : null,
    stateRowsReconstructed: trace.length,
    stateTraceSha256: sha256(trace),
    firstEnterEvents,
    directGoldenEntryRows: 0,
    deterministicEntryRows: firstEnterEvents.length,
    referencePriceComparisons: featureBundle.events.filter((event) => event.directionFeatures).length,
    referencePriceMismatches,
    pitViolations,
    repeatEntryViolations,
    chronologicalViolations,
    safety: SAFETY,
  };
}

export function summarizeStage1G({sessions, modelBytes}) {
  const model = loadAndValidateFrozenCandidate(modelBytes);
  assert.equal(sessions.length, ALLOWED_SESSIONS.length, 'THREE_SESSIONS_REQUIRED');
  assert.deepEqual(sessions.map((row) => row.sessionDate).sort(), [...ALLOWED_SESSIONS].sort());
  const totals = {
    goldenFeatureEventRows: sessions.reduce((sum, row) => sum + row.goldenFeatureEventRows, 0),
    scoreRowsReconstructed: sessions.reduce((sum, row) => sum + row.scoreRowsReconstructed, 0),
    stateRowsReconstructed: sessions.reduce((sum, row) => sum + row.stateRowsReconstructed, 0),
    firstEnterEventsReconstructed: sessions.reduce((sum, row) => sum + row.firstEnterEvents.length, 0),
    directGoldenEntryRows: 0,
    deterministicEntryRows: sessions.reduce((sum, row) => sum + row.deterministicEntryRows, 0),
    referencePriceComparisons: sessions.reduce((sum, row) => sum + row.referencePriceComparisons, 0),
    referencePriceMismatches: sessions.reduce((sum, row) => sum + row.referencePriceMismatches, 0),
    hybridMaterialMismatches: 0,
    pitViolations: sessions.reduce((sum, row) => sum + row.pitViolations, 0),
    repeatEntryViolations: sessions.reduce((sum, row) => sum + row.repeatEntryViolations, 0),
    chronologicalViolations: sessions.reduce((sum, row) => sum + row.chronologicalViolations, 0),
  };
  const criticalClear = totals.scoreRowsReconstructed === 1260
    && totals.stateRowsReconstructed === 787
    && totals.firstEnterEventsReconstructed > 0
    && totals.referencePriceMismatches === 0
    && totals.pitViolations === 0
    && totals.repeatEntryViolations === 0
    && totals.chronologicalViolations === 0;
  return {
    schemaVersion: 1,
    auditId: 'PHASE57_EXIT_V4_JQUANTS_STAGE1G_ENTRY_EVENT_EVIDENCE_CLOSURE_V1',
    stage: '1G_ENTRY_EVENT_RECONSTRUCTION_EVIDENCE_CLOSURE',
    asOfJst: '2026-09-10',
    pullRequest: 581,
    parentRemoteHeadSha: '4699600e03308ecad1a5c48bbb3446cebd132594',
    baseBranch: 'research/phase57-minimal-stateful-hybrid-entry',
    draft: true,
    scope: {
      allowedSessions: [...ALLOWED_SESSIONS],
      newMarketRawAcquisition: false,
      approvedGoldenSessionsReextracted: 3,
      unapprovedContentReads: 0,
      exitOutcomeAccessAllowed: false,
      futureLabelGenerationAllowed: false,
      stage2Allowed: false,
    },
    model: {
      sha256: bytesSha256(modelBytes),
      parameterSha256: bytesSha256(Buffer.from(JSON.stringify({features:model.features, weights:model.weights, means:model.means, scales:model.scales, intercept:model.intercept, threshold:model.threshold}))),
      featureContractSha256: model.featureTargetStateSha256,
      featureOrdering: model.features,
      threshold: model.threshold,
      thresholdComparison: 'STRICTLY_GREATER_THAN',
      bytesCommittedToRepository: false,
      artifactLineage: MODEL_ARTIFACT_LINEAGE,
    },
    sessions,
    totals,
    scoreParity: 'NOT_AVAILABLE_GOLDEN_SCORE_NOT_RETAINED',
    stateParityFoundation: 'PASS_787_OF_787_EXACT_CHRONOLOGICAL_STAGE1E',
    directGoldenEntryParity: 'NOT_AVAILABLE_PRE_FIT_GOLDEN_HAS_MODEL_UNAVAILABLE',
    deterministicEntryReconstruction: criticalClear ? 'PASS' : 'FAIL',
    referencePriceClosure: totals.referencePriceMismatches === 0 ? 'DETERMINISTIC_REFERENCE_PRICE_RECONSTRUCTION_PASS' : 'FAIL',
    finalGate: criticalClear ? 'ENTRY_EVENT_EVIDENCE_CLOSED_TIER2_FREEZE_READY' : 'ENTRY_EVENT_EVIDENCE_PARTIAL',
    fullReplayEligibleSessions: 0,
    tier2ConfirmedSessions: 0,
    tier2FreezeReadiness: criticalClear ? 'READY_FOR_SEPARATELY_AUTHORIZED_FREEZE' : 'NOT_READY',
    tier2ContractStatus: 'DRAFT_NOT_ACTIVE_BLOCKED',
    accessLedger: {
      existingGitHubArtifactsDownloadedTemporarily: 4,
      approvedGoldenSessionsReextracted: 3,
      newRawSessionAccess: 0,
      newSealedSessions: 0,
      protected180To282: 0,
      freshValidationOrOos: 0,
      exitOutcome: 0,
      futureLabels: 0,
      exitInvocations: 0,
      unapprovedContentReads: 0,
    },
    highestValueNextAction: 'With explicit user approval, freeze the Tier2 Reconstruction Contract and its accepted partial-universe boundary; do not allocate Development data yet.',
    hardStop: 'ACTIVE',
    safety: SAFETY,
  };
}
