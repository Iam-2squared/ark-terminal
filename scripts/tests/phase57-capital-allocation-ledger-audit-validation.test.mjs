import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {simulatePhaseB,PHASE_B_SAFETY} from '../lib/phase57-capital-allocation-v3-phase-b.mjs';
import {prepareValidationReadiness,measureAuthorizedValidationBundle,VALIDATION_ARMS} from '../phase57-capital-allocation-validation-runner.mjs';

const digest=b=>createHash('sha256').update(b).digest('hex');
const opportunity=({eventId,symbol,timestamp,direction=-1})=>({eventId,symbol,sessionDate:'2026-09-01',decisionTimestamp:timestamp,direction,entryPrice:100,mshScore:.8,recentRealizedVolatility:.01,outcomeUsed:false,exitUsed:false});
const trade=({eventId,symbol,direction=-1,exitTimestamp,exitPrice})=>({eventId,symbol,direction,causalEligible:true,firstBarDirectionalCloseReturnBps:50,v4:{exitTimestamp,exitPrice,exitReason:'V4_NATIVE',barsHeld:2,netReturnPct:direction*(exitPrice/100-1)*100-.05}});
const mark=(symbol,timestamp,close)=>({symbol,timestamp,sessionDate:'2026-09-01',close});

test('event ledger exposes and asserts all twelve accounting invariants',()=>{
  const t0='2026-09-01T00:00:00.000Z',t1='2026-09-01T00:10:00.000Z',t2='2026-09-01T00:20:00.000Z';
  const result=simulatePhaseB({opportunities:[opportunity({eventId:'short',symbol:'1001.T',timestamp:t0}),opportunity({eventId:'long',symbol:'1002.T',timestamp:t1,direction:1})],trades:[trade({eventId:'short',symbol:'1001.T',exitTimestamp:t1,exitPrice:99}),trade({eventId:'long',symbol:'1002.T',direction:1,exitTimestamp:t2,exitPrice:101})],allocationId:'V3_B_RISK',exitId:'FROZEN_EXIT_V4',initialCapital:100000,maxPositions:1,budgetDivisor:1,marks:[mark('1001.T',t0,100),mark('1001.T',t1,99),mark('1002.T',t1,100),mark('1002.T',t2,101)]});
  assert.equal(result.ledgerAudit.status,'LEDGER_INVARIANTS_PASS');assert.equal(result.ledgerAudit.checks.length,12);
  assert.ok(result.ledgerTrace.every(row=>Object.values(row.invariants).every(Boolean)));
  const sameTimestamp=result.ledgerTrace.find(row=>row.timestamp===t1);assert.ok(sameTimestamp.exitCashReleasedJpy>0);assert.ok(sameTimestamp.entryCashConsumedJpy>0);assert.equal(sameTimestamp.invariants.exitReleaseBeforeSameTimestampEntry,true);
  assert.equal(sameTimestamp.invariants.shortSaleProceedsNotReused,true);assert.equal(sameTimestamp.invariants.unrealizedGainsExcludedFromBuyingPower,true);assert.ok(sameTimestamp.availableCashJpy>=0);
});

test('Validation preparation freezes MAX_5 primary without opening data',()=>{
  const readiness=prepareValidationReadiness();assert.equal(readiness.status,'VALIDATION_READY_NOT_OPENED');assert.equal(readiness.executionPerformed,false);assert.equal(readiness.protectedOrFreshDataRead,false);
  assert.equal(VALIDATION_ARMS.primary.budgetDivisor,5);assert.equal(VALIDATION_ARMS.legacyBaseline.budgetDivisor,10);assert.equal(VALIDATION_ARMS.aggressiveDevelopmentReference.budgetDivisor,3);assert.equal(VALIDATION_ARMS.primary.exitId,'EXIT_V5_DYNAMIC_RECLAIM_BAR_5');
  for(const value of Object.values(readiness.safety))assert.equal(value,false);
});

test('Validation runner rejects execution without a separate hash-bound unlock',()=>{
  assert.throws(()=>measureAuthorizedValidationBundle({},{}),/separate Validation unlock required/);
});

test('authorized materialized runner preserves fixed comparison arms and output shape',()=>{
  const t0='2026-09-01T00:00:00.000Z',t1='2026-09-01T00:10:00.000Z',inputSha='a'.repeat(64),freezeSha=digest(fs.readFileSync('predict/research/phase57-capital-allocation-integrated-candidate-freeze.json'));
  const bundle={schemaId:'PHASE57_CAPITAL_ALLOCATION_VALIDATION_MATERIALIZED_INPUT_V1',evidenceRole:'UNTOUCHED_VALIDATION',sourceIdentity:{validationSourceId:'VALIDATION_SYNTHETIC_CONTRACT_TEST',sourceManifestSha256:'b'.repeat(64),sessionIds:['2026-09-01'],pointInTimeAttestation:true,unopenedBeforeAuthorizationAttestation:true},opportunities:[opportunity({eventId:'x',symbol:'1001.T',timestamp:t0})],trades:[trade({eventId:'x',symbol:'1001.T',exitTimestamp:t1,exitPrice:99})],marks:[mark('1001.T',t0,100),mark('1001.T',t1,99)],barCloses:{},includeAggressiveDevelopmentReference:true};
  const result=measureAuthorizedValidationBundle(bundle,{inputBundleSha256:inputSha,unlock:{status:'AUTHORIZED_VALIDATION_OPEN',candidateFreezeSha256:freezeSha,inputBundleSha256:inputSha}});
  assert.equal(result.status,'VALIDATION_MEASURED_NOT_ADJUDICATED');assert.deepEqual(Object.keys(result.arms),['legacyBaseline','primary','exitComparator','aggressiveDevelopmentReference']);assert.equal(result.arms.primary.budgetDivisor,5);assert.equal(result.arms.primary.exitId,'EXIT_V5_DYNAMIC_RECLAIM_BAR_5');assert.equal(result.arms.legacyBaseline.budgetDivisor,10);assert.equal(result.arms.aggressiveDevelopmentReference.budgetDivisor,3);assert.equal(result.arms.primary.validationMetrics.accepted,1);assert.equal(result.arms.primary.validationMetrics.belowLotSkip,0);assert.equal(result.comparisons.primaryVsLegacyBudget.recomposed,true);assert.equal(result.comparisons.primaryV5VsV4.recomposed,true);for(const value of Object.values(PHASE_B_SAFETY))assert.equal(value,false);
});
