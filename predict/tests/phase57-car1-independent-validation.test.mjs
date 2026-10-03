import assert from 'node:assert/strict';
import test from 'node:test';
import {
  buildCar1DevelopmentEvidenceLock,
  gateCar1IndependentValidationCandidate,
  PHASE57_CAR1_VALIDATION_PLAN,
  PHASE57_CAR1_VALIDATION_SAFETY,
  selectCar1IndependentValidationWindow,
} from '../portfolio/phase57-car1-independent-validation.js';

const FALSE_SAFETY=Object.freeze({
  executionAllowed:false,
  brokerWriteAllowed:false,
  excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,
  paperTradingAllowed:false,
  automaticPromotionAllowed:false,
  productionUpdateAllowed:false,
  transmitted:false,
});
const method=Object.freeze({
  sameFrozenEntry:true,
  sameEntryPrice:true,
  sameDirection:true,
  sameFrozenExit:true,
  sameCostAssumption:true,
  sameCandidatePriority:true,
  baselineBudgetEnvelopeAnchored:true,
  rankingChanged:false,
  selectorChanged:false,
  entryChanged:false,
  exitChanged:false,
  parameterSearchAllowed:false,
  winnerSelectionAllowed:false,
  promotionEligible:false,
  futureOutcomeUsedBySizer:false,
  incompleteProspectiveBackfillAllowed:false,
  formalOos:false,
  prospectiveSampleSufficient:false,
});

function result({
  expectedDates=['2026-09-01','2026-09-02','2026-09-03'],
  readyDates=expectedDates,
  lineage='a'.repeat(64),
  source='b'.repeat(64),
  initialEquityJpy=1_000_000,
}={}){
  return {
    phase:'57.car1.checkpointed-sizing-attribution',
    status:'CAR1_CHECKPOINTED_PAIRED_SIZING_ATTRIBUTION_READY',
    managementMode:'FIXED_HORIZON',
    initialEquityJpy,
    lineageManifestHeadSha256:lineage,
    universeVariantOrder:['DYNAMIC_50'],
    baselineProfileOrder:['MAX_10','MAX_4','MAX_3','MAX_2'],
    sizingProfileOrder:['EQUAL_NOTIONAL','INVERSE_ATR','INVERSE_REALIZED_VOL'],
    inputAudit:{
      readySessionCount:readyDates.length,
      expectedSessionCount:expectedDates.length,
      expectedSessionDates:[...expectedDates],
      packetSummaries:readyDates.map((sessionDate,index)=>({sessionDate,frozenTradeCount:index+1})),
      frozenTradeCount:8,
      resolvedTradeCount:7,
      unresolvedTradeCount:1,
    },
    sourceReconciliation:{sourceEvaluationCanonicalSha256:source},
    baselineParity:{
      DYNAMIC_50:Object.fromEntries(['MAX_10','MAX_4','MAX_3','MAX_2'].map((baseline,index)=>[
        baseline,
        {passed:true,candidateKeySha256:String(index+1).repeat(64),candidateEntryCount:8},
      ])),
    },
    methodology:{...method},
    safety:{checkpoint:{...FALSE_SAFETY},sizing:{...FALSE_SAFETY},laneCFixed:{...FALSE_SAFETY}},
  };
}

test('CAR-1 independent validation is precommitted, read-only, and cannot promote a winner',()=>{
  assert.equal(PHASE57_CAR1_VALIDATION_PLAN.protocolFreezeDate,'2026-09-05');
  assert.equal(PHASE57_CAR1_VALIDATION_PLAN.requiredSessionCount,5);
  assert.equal(PHASE57_CAR1_VALIDATION_PLAN.incompleteSessionPolicy,'FAIL_CLOSED_NO_REPLACEMENT_NO_BACKFILL');
  assert.equal(PHASE57_CAR1_VALIDATION_PLAN.winnerSelectionAllowed,false);
  assert.equal(PHASE57_CAR1_VALIDATION_PLAN.automaticPromotionAllowed,false);
  assert.equal(PHASE57_CAR1_VALIDATION_PLAN.promotionEligible,false);
  for(const key of Object.keys(FALSE_SAFETY))assert.equal(PHASE57_CAR1_VALIDATION_SAFETY[key],false,key);
});

test('development lock is deterministic and pins lineage, candidate identity, sessions, and sizing configuration',()=>{
  const development=result();
  const left=buildCar1DevelopmentEvidenceLock({result:development});
  const right=buildCar1DevelopmentEvidenceLock({result:structuredClone(development)});
  assert.deepEqual(left,right);
  assert.equal(left.status,'CAR1_DEVELOPMENT_EVIDENCE_LOCKED_BEFORE_VALIDATION');
  assert.equal(left.lockedBeforeValidationOutcomes,true);
  assert.equal(left.developmentEvidence.lineageManifestHeadSha256,'a'.repeat(64));
  assert.deepEqual(left.developmentEvidence.expectedSessionDates,['2026-09-01','2026-09-02','2026-09-03']);
  assert.equal(left.developmentEvidence.candidateIdentity.length,4);
  assert.match(left.configurationSha256,/^[0-9a-f]{64}$/);
  assert.match(left.developmentEvidenceSha256,/^[0-9a-f]{64}$/);
});

test('validation window is the first five formal expected sessions after the freeze date, never a favorable subset',()=>{
  const lock=buildCar1DevelopmentEvidenceLock({result:result()});
  const expected=['2026-09-03','2026-09-07','2026-09-08','2026-09-09','2026-09-10','2026-09-11','2026-09-14'];
  const ready=[...expected];
  const window=selectCar1IndependentValidationWindow({expectedSessionDates:expected,readySessionDates:ready,developmentLock:lock});
  assert.deepEqual(window.selectedSessionDates,['2026-09-07','2026-09-08','2026-09-09','2026-09-10','2026-09-11']);
  assert.equal(window.replacementAllowed,false);
  assert.equal(window.backfillAllowed,false);
});

test('an incomplete precommitted session fails closed and a later ready session cannot replace it',()=>{
  const lock=buildCar1DevelopmentEvidenceLock({result:result()});
  const expected=['2026-09-07','2026-09-08','2026-09-09','2026-09-10','2026-09-11','2026-09-14'];
  const ready=['2026-09-07','2026-09-09','2026-09-10','2026-09-11','2026-09-14'];
  assert.throws(
    ()=>selectCar1IndependentValidationWindow({expectedSessionDates:expected,readySessionDates:ready,developmentLock:lock}),
    /2026-09-08/,
  );
});

test('the development artifact itself cannot be relabelled as independent validation',()=>{
  const development=result();
  const lock=buildCar1DevelopmentEvidenceLock({result:development});
  assert.throws(()=>gateCar1IndependentValidationCandidate({developmentLock:lock,candidateResult:development}),/cannot be reused/);
});

test('configuration drift fails before validation performance can be inspected',()=>{
  const lock=buildCar1DevelopmentEvidenceLock({result:result()});
  const candidate=result({
    expectedDates:['2026-09-01','2026-09-02','2026-09-03','2026-09-07','2026-09-08','2026-09-09','2026-09-10','2026-09-11'],
    lineage:'c'.repeat(64),source:'d'.repeat(64),initialEquityJpy:2_000_000,
  });
  assert.throws(()=>gateCar1IndependentValidationCandidate({developmentLock:lock,candidateResult:candidate}),/configuration drift/);
});

test('a new complete cumulative candidate only opens the windowed-replay gate; it does not expose performance or promotion',()=>{
  const lock=buildCar1DevelopmentEvidenceLock({result:result()});
  const expected=['2026-09-01','2026-09-02','2026-09-03','2026-09-07','2026-09-08','2026-09-09','2026-09-10','2026-09-11'];
  const candidate=result({expectedDates:expected,readyDates:expected,lineage:'c'.repeat(64),source:'d'.repeat(64)});
  const gate=gateCar1IndependentValidationCandidate({developmentLock:lock,candidateResult:candidate});
  assert.equal(gate.status,'CAR1_INDEPENDENT_VALIDATION_WINDOW_READY_FOR_WINDOWED_REPLAY');
  assert.deepEqual(gate.selectedSessionDates,['2026-09-07','2026-09-08','2026-09-09','2026-09-10','2026-09-11']);
  assert.equal(gate.sameFrozenConfiguration,true);
  assert.equal(gate.developmentEvidenceReused,false);
  assert.equal(gate.performanceExtractionAllowed,false);
  assert.equal(gate.winnerSelectionAllowed,false);
  assert.equal(gate.promotionEligible,false);
});

test('candidate safety or causal-lock regressions fail closed',()=>{
  const lock=buildCar1DevelopmentEvidenceLock({result:result()});
  const unsafe=result({
    expectedDates:['2026-09-07','2026-09-08','2026-09-09','2026-09-10','2026-09-11'],
    lineage:'c'.repeat(64),source:'d'.repeat(64),
  });
  unsafe.safety.checkpoint.liveTradingAllowed=true;
  assert.throws(()=>gateCar1IndependentValidationCandidate({developmentLock:lock,candidateResult:unsafe}),/liveTradingAllowed/);

  const leaked=result({
    expectedDates:['2026-09-07','2026-09-08','2026-09-09','2026-09-10','2026-09-11'],
    lineage:'e'.repeat(64),source:'f'.repeat(64),
  });
  leaked.methodology.futureOutcomeUsedBySizer=true;
  assert.throws(()=>gateCar1IndependentValidationCandidate({developmentLock:lock,candidateResult:leaked}),/futureOutcomeUsedBySizer/);
});
