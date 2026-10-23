import assert from 'node:assert/strict';
import test from 'node:test';
import {
  buildCar1ValidationCandidateMetadataFromFixed,
  gateCar1IndependentValidationMetadataCandidate,
  PHASE57_CAR1_VALIDATION_CANDIDATE_SAFETY,
} from '../portfolio/phase57-car1-validation-candidate-metadata.js';
import {
  Car1IndependentValidationInternals,
  PHASE57_CAR1_VALIDATION_PLAN,
} from '../portfolio/phase57-car1-independent-validation.js';

const expected=['2026-09-07','2026-09-08','2026-09-09','2026-09-10','2026-09-11'];
const packetSummaries=dates=>dates.map(sessionDate=>({sessionDate,frozenTradeCount:1,resolvedTradeCount:1,unresolvedTradeCount:0}));

function fixed({expectedDates=expected,readyDates=expected,lineage='b'.repeat(64)}={}){
  return {
    status:'LANE_C_FIXED_CHECKPOINTED_PORTFOLIO_MATRIX_READY',
    managementMode:'FIXED_HORIZON',
    initialEquityJpy:1_000_000,
    lineageManifestHeadSha256:lineage,
    universeVariantOrder:['DYNAMIC_50'],
    inputAudit:{
      readySessionCount:readyDates.length,
      expectedSessionCount:expectedDates.length,
      expectedSessionDates:expectedDates,
      packetSummaries:packetSummaries(readyDates),
      frozenTradeCount:readyDates.length,
      resolvedTradeCount:readyDates.length,
      unresolvedTradeCount:0,
    },
    sourceReconciliation:{
      formalP25EvaluationRequired:true,
      exactCheckpointRecomputationMatch:true,
      sourceEvaluationCanonicalSha256:'c'.repeat(64),
      recomputedEvaluationCanonicalSha256:'c'.repeat(64),
      packetSummariesMatch:true,
    },
    comparisons:{
      DYNAMIC_50:{
        pairedAudit:{candidateKeySha256:'a'.repeat(64),candidateEntryCount:readyDates.length},
      },
    },
  };
}

function developmentLockFor(candidate){
  const configuration=Car1IndependentValidationInternals.configurationSnapshot(candidate);
  return {
    status:'CAR1_DEVELOPMENT_EVIDENCE_LOCKED_BEFORE_VALIDATION',
    lockedBeforeValidationOutcomes:true,
    validationPlan:PHASE57_CAR1_VALIDATION_PLAN,
    configuration,
    configurationSha256:Car1IndependentValidationInternals.sha256(configuration),
    developmentEvidence:{
      lineageManifestHeadSha256:'d'.repeat(64),
      expectedSessionDates:['2026-08-19','2026-08-20','2026-09-03'],
    },
  };
}

test('metadata-only candidate exposes identities and audit but no challenger performance surface',()=>{
  const candidate=buildCar1ValidationCandidateMetadataFromFixed({fixed:fixed()});
  assert.equal(candidate.status,'CAR1_VALIDATION_CANDIDATE_METADATA_READY');
  assert.equal(candidate.methodology.challengerReplayExecuted,false);
  assert.equal(candidate.methodology.challengerPerformanceMaterialized,false);
  assert.equal(candidate.methodology.performanceExtractionAllowed,false);
  assert.equal(candidate.methodology.sameFrozenEntry,true);
  assert.equal(candidate.methodology.sameFrozenExit,true);
  assert.deepEqual(candidate.sizingProfileOrder,['EQUAL_NOTIONAL','INVERSE_ATR','INVERSE_REALIZED_VOL']);
  assert.equal(candidate.candidateIdentity.length,4);
  for(const forbidden of ['matrixRows','attributions','results','challengerResults','closedTrades','equityCurve']){
    assert.equal(forbidden in candidate,false,forbidden);
  }
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted']){
    assert.equal(PHASE57_CAR1_VALIDATION_CANDIDATE_SAFETY[key],false,key);
  }
});

test('metadata-only gate opens exactly the precommitted first five complete sessions without materializing challenger performance',()=>{
  const candidate=buildCar1ValidationCandidateMetadataFromFixed({fixed:fixed()});
  const gate=gateCar1IndependentValidationMetadataCandidate({developmentLock:developmentLockFor(candidate),candidateMetadata:candidate});
  assert.equal(gate.status,'CAR1_INDEPENDENT_VALIDATION_WINDOW_READY_FOR_WINDOWED_REPLAY');
  assert.deepEqual(gate.selectedSessionDates,expected);
  assert.equal(gate.cumulativeChallengerPerformanceMaterialized,false);
  assert.equal(gate.challengerReplayExecuted,false);
  assert.equal(gate.performanceExtractionAllowed,false);
  assert.equal(gate.winnerSelectionAllowed,false);
  assert.equal(gate.promotionEligible,false);
});

test('a missing precommitted session cannot be replaced by a later ready session',()=>{
  const expectedDates=[...expected,'2026-09-14'];
  const readyDates=['2026-09-07','2026-09-08','2026-09-10','2026-09-11','2026-09-14'];
  const candidate=buildCar1ValidationCandidateMetadataFromFixed({fixed:fixed({expectedDates,readyDates})});
  assert.throws(
    ()=>gateCar1IndependentValidationMetadataCandidate({developmentLock:developmentLockFor(candidate),candidateMetadata:candidate}),
    /no replacement\/backfill allowed: 2026-09-09/,
  );
});

test('development lineage reuse is rejected even when metadata are otherwise complete',()=>{
  const candidate=buildCar1ValidationCandidateMetadataFromFixed({fixed:fixed({lineage:'d'.repeat(64)})});
  assert.throws(
    ()=>gateCar1IndependentValidationMetadataCandidate({developmentLock:developmentLockFor(candidate),candidateMetadata:candidate}),
    /development evidence cannot be reused/,
  );
});
