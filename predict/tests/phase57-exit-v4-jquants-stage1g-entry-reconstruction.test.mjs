import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

import {
  CANDIDATE_SHA256,
  THRESHOLD,
  decideFrozenPair,
  reconstructEntrySession,
  scoreFrozenDirection,
  thresholdDecision,
} from '../../scripts/lib/phase57-stage1g-entry-reconstruction.mjs';
import {CONTRACT, CONTRACT_SHA256, FEATURES, SAFETY, sha256} from '../../scripts/lib/phase57-minimal-stateful-entry.mjs';

const audit = JSON.parse(fs.readFileSync(new URL('../research/phase57-exit-v4-jquants-stage1g-entry-event-evidence-closure-v1.json', import.meta.url)));
const matrix = JSON.parse(fs.readFileSync(new URL('../research/phase57-exit-v4-jquants-stage1g-entry-evidence-matrix-v1.json', import.meta.url)));

const model = {
  features: [...FEATURES], weights: FEATURES.map((key) => key === 'direction' ? 1 : 0),
  means: FEATURES.map(() => 0), scales: FEATURES.map(() => 1), intercept: 0, threshold: THRESHOLD,
};
function feature(symbol, decisionTimestamp, direction) {
  const core = {
    contractSha256: CONTRACT_SHA256, symbol, sessionDate: '2025-08-27', decisionTimestamp, direction,
    features: Object.fromEntries(FEATURES.map((key) => [key, key === 'direction' ? direction : 0])),
    prefixSha256: 'a'.repeat(64), latestAvailableAt: decisionTimestamp,
    selectorModelDigest: CONTRACT.selectorModelDigest, selectorFreezeSHA: CONTRACT.selectorFreezeSHA,
  };
  return {...core, featureSha256: sha256(core)};
}

test('frozen candidate identity, parameter digest, feature ordering and strict threshold are pinned', () => {
  assert.equal(audit.model.sha256, CANDIDATE_SHA256);
  assert.equal(audit.model.parameterSha256, '9f116aee99fb3ffa7047b787d1ad8b1c41addf17eb753349e4b67157e101df14');
  assert.deepEqual(audit.model.featureOrdering, FEATURES);
  assert.equal(audit.model.threshold, 0.60);
  assert.equal(thresholdDecision(0.60), 'WATCH');
  assert.equal(thresholdDecision(0.6000000001), 'ENTER');
});

test('score and paired decision rerun deterministically', () => {
  const pair = [feature('1234.T', '2025-08-27T01:00:00.000Z', 1), feature('1234.T', '2025-08-27T01:00:00.000Z', -1)];
  assert.deepEqual(scoreFrozenDirection(pair[0], model), scoreFrozenDirection(pair[0], model));
  assert.deepEqual(decideFrozenPair(pair, model), decideFrozenPair(pair, model));
  assert.equal(decideFrozenPair(pair, model).action, 'ENTER');
  assert.equal(decideFrozenPair(pair, model).direction, 1);
});

test('chronological replay yields one First ENTER, blocks repeat Entry, and closes reference price', () => {
  const times = ['2025-08-27T01:00:00.000Z', '2025-08-27T01:05:00.000Z'];
  const events = times.map((decisionTimestamp, index) => ({
    sessionDate:'2025-08-27', eventId:`e${index}`, symbol:'1234.T', decisionTimestamp,
    directionFeatures:[feature('1234.T', decisionTimestamp, 1), feature('1234.T', decisionTimestamp, -1)],
    priceReference:100 + index, minutesSinceFirstSelection:index * 5,
  }));
  const points = times.map((decisionTimestamp) => ({decisionTimestamp, complete:true, selectedCount:1}));
  const barsBundle = [{symbol:'1234.T', bars:[
    {timestamp:'2025-08-27T00:55:00.000Z', availableAt:times[0], close:100},
    {timestamp:'2025-08-27T01:00:00.000Z', availableAt:times[1], close:101},
  ]}];
  const result = reconstructEntrySession({featureBundle:{sessionDate:'2025-08-27', events, points}, barsBundle, model});
  assert.equal(result.firstEnterEvents.length, 1);
  assert.equal(result.firstEnterEvents[0].entryReferencePrice, 100);
  assert.equal(result.firstEnterEvents[0].referencePriceTimestamp, '2025-08-27T00:55:00.000Z');
  assert.equal(result.repeatEntryViolations, 0);
  assert.equal(result.pitViolations, 0);
});

test('future/outcome fields and unapproved sessions fail closed', () => {
  const t='2025-08-27T01:00:00.000Z';
  const row=feature('1234.T',t,1);
  assert.throws(()=>scoreFrozenDirection({...row,futureReturn:1},model),/OUTCOME_OR_FUTURE_FIELD_DENIED/);
  assert.throws(()=>reconstructEntrySession({featureBundle:{sessionDate:'2025-08-28',events:[],points:[]},barsBundle:[],model}),/UNAPPROVED_SESSION/);
});

test('Golden Entry absence is distinguished from mismatch and closure remains Tier2-freeze-only', () => {
  assert.equal(matrix.directGoldenEntryRows, 0);
  assert.equal(matrix.goldenMissingIsMismatch, false);
  assert.equal(matrix.criticalAmbiguous, 0);
  assert.equal(matrix.criticalMismatch, 0);
  assert.equal(audit.finalGate, 'ENTRY_EVENT_EVIDENCE_CLOSED_TIER2_FREEZE_READY');
  assert.equal(audit.fullReplayEligibleSessions, 0);
  assert.equal(audit.tier2ConfirmedSessions, 0);
  assert.equal(audit.tier2ContractStatus, 'DRAFT_NOT_ACTIVE_BLOCKED');
  assert.equal(audit.hardStop, 'ACTIVE');
});

test('no EXIT import or invocation, protected/fresh/outcome access, or safety enablement exists', () => {
  const source=fs.readFileSync(new URL('../../scripts/lib/phase57-stage1g-entry-reconstruction.mjs',import.meta.url),'utf8');
  assert.doesNotMatch(source,/from ['"].*exit/i);
  for(const key of ['newRawSessionAccess','newSealedSessions','protected180To282','freshValidationOrOos','exitOutcome','futureLabels','exitInvocations','unapprovedContentReads']) assert.equal(audit.accessLedger[key],0,key);
  assert.deepEqual(audit.safety, SAFETY);
  assert.deepEqual(matrix.safety, SAFETY);
});
