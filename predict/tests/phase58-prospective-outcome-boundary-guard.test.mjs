import test from 'node:test';
import assert from 'node:assert/strict';
import {
  validateProspectiveOutcomeBoundaryJoins,
  PHASE58_P31_OUTCOME_POLICY,
  PHASE58_P31_SAFETY,
} from '../scalping/phase58-prospective-outcome-boundary-guard.js';

function report(exitAt){
  return {
    eventAudit:[{
      status:'MATURED',
      key:'7203.T|frozen-h24',
      frozenOutcomeTargetAt:'2026-08-18T03:50:00.000Z',
      baselineExitAt:exitAt,
    }],
  };
}

test('prospective outcome captured near the frozen boundary is accepted',()=>{
  const result=validateProspectiveOutcomeBoundaryJoins(report('2026-08-18T03:50:15.000Z'));
  assert.equal(result.complete,true);
  assert.equal(result.status,'PROSPECTIVE_OUTCOME_BOUNDARY_INTEGRITY_READY');
  assert.equal(result.maturedOutcomeAudit[0].outcomeJoinLagMs,15_000);
  assert.equal(result.maturedOutcomeAudit[0].withinBudget,true);
});

test('late prospective outcome capture is blocked instead of silently substituting a later price',()=>{
  const result=validateProspectiveOutcomeBoundaryJoins(report('2026-08-18T05:10:00.000Z'));
  assert.equal(result.complete,false);
  assert.equal(result.status,'BLOCKED_OUTCOME_CAPTURE_LAG');
  assert.equal(result.maturedOutcomeAudit[0].withinBudget,false);
  assert.ok(result.blockers.some(x=>x.startsWith('OUTCOME_JOIN_TOO_LATE:')));
});

test('pending events do not become blockers before an outcome row exists',()=>{
  const result=validateProspectiveOutcomeBoundaryJoins({eventAudit:[{
    status:'PENDING_OUTCOME',
    key:'7203.T|pending',
    frozenOutcomeTargetAt:'2026-08-18T03:50:00.000Z',
    baselineExitAt:null,
  }]});
  assert.equal(result.complete,true);
  assert.equal(result.maturedOutcomeAudit.length,0);
});

test('P31 policy and safety remain frozen READ ONLY',()=>{
  assert.equal(PHASE58_P31_OUTCOME_POLICY.maxOutcomeJoinLagMs,60_000);
  assert.equal(PHASE58_P31_OUTCOME_POLICY.lateOutcomeJoinAllowed,false);
  assert.equal(PHASE58_P31_OUTCOME_POLICY.historicalOutcomeReconstructionAllowed,false);
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed','transmitted','freshHoldoutConsumed']){
    assert.equal(PHASE58_P31_SAFETY[key],false,key);
  }
});
