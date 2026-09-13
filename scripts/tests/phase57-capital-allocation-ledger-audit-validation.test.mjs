import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {simulatePhaseB,PHASE_B_SAFETY} from '../lib/phase57-capital-allocation-v3-phase-b.mjs';
import {prepareIntegratedOosReadiness,measureAuthorizedIntegratedOosBundle,INTEGRATED_OOS_ARMS} from '../phase57-capital-allocation-validation-runner.mjs';

const digest=b=>createHash('sha256').update(b).digest('hex');
const opportunity=({eventId,symbol,timestamp,direction=-1})=>({eventId,symbol,sessionDate:timestamp.slice(0,10),decisionTimestamp:timestamp,direction,entryPrice:100,mshScore:.8,recentRealizedVolatility:.01,outcomeUsed:false,exitUsed:false});
const trade=({eventId,symbol,direction=-1,exitTimestamp,exitPrice})=>({eventId,symbol,sessionDate:exitTimestamp.slice(0,10),direction,causalEligible:true,firstBarDirectionalCloseReturnBps:50,v4:{exitTimestamp,exitPrice,exitReason:'V4_NATIVE',barsHeld:2,netReturnPct:direction*(exitPrice/100-1)*100-.05}});
const mark=(symbol,timestamp,close)=>({symbol,timestamp,sessionDate:timestamp.slice(0,10),close});
const futureSessions=['2026-10-22','2026-10-23','2026-10-26','2026-10-27','2026-10-28','2026-10-29','2026-10-30','2026-11-02','2026-11-04','2026-11-05','2026-11-06','2026-11-09','2026-11-10','2026-11-11','2026-11-12','2026-11-13','2026-11-16','2026-11-17','2026-11-18','2026-11-19'];

test('event ledger exposes and asserts all twelve accounting invariants',()=>{
  const t0='2026-09-01T00:00:00.000Z',t1='2026-09-01T00:10:00.000Z',t2='2026-09-01T00:20:00.000Z';
  const result=simulatePhaseB({opportunities:[opportunity({eventId:'short',symbol:'1001.T',timestamp:t0}),opportunity({eventId:'long',symbol:'1002.T',timestamp:t1,direction:1})],trades:[trade({eventId:'short',symbol:'1001.T',exitTimestamp:t1,exitPrice:99}),trade({eventId:'long',symbol:'1002.T',direction:1,exitTimestamp:t2,exitPrice:101})],allocationId:'V3_B_RISK',exitId:'FROZEN_EXIT_V4',initialCapital:100000,maxPositions:1,budgetDivisor:1,marks:[mark('1001.T',t0,100),mark('1001.T',t1,99),mark('1002.T',t1,100),mark('1002.T',t2,101)]});
  assert.equal(result.ledgerAudit.status,'LEDGER_INVARIANTS_PASS');assert.equal(result.ledgerAudit.checks.length,12);
  assert.ok(result.ledgerTrace.every(row=>Object.values(row.invariants).every(Boolean)));
  const sameTimestamp=result.ledgerTrace.find(row=>row.timestamp===t1);assert.ok(sameTimestamp.exitCashReleasedJpy>0);assert.ok(sameTimestamp.entryCashConsumedJpy>0);assert.equal(sameTimestamp.invariants.exitReleaseBeforeSameTimestampEntry,true);
  assert.equal(sameTimestamp.invariants.shortSaleProceedsNotReused,true);assert.equal(sameTimestamp.invariants.unrealizedGainsExcludedFromBuyingPower,true);assert.ok(sameTimestamp.availableCashJpy>=0);
});

test('Integrated OOS preparation freezes MAX_3 primary without opening future or reserved data',()=>{
  const readiness=prepareIntegratedOosReadiness();assert.equal(readiness.status,'FUTURE_INTEGRATED_OOS_PRECOMMITTED_OOS_NOT_OPENED');assert.equal(readiness.executionPerformed,false);assert.equal(readiness.futureOutcomeDataRead,false);assert.equal(readiness.reservedEntryBlockRead,false);
  assert.equal(INTEGRATED_OOS_ARMS.primary.budgetDivisor,3);assert.equal(INTEGRATED_OOS_ARMS.conservativeSub.budgetDivisor,5);assert.equal(INTEGRATED_OOS_ARMS.legacyBaseline.budgetDivisor,10);assert.equal(INTEGRATED_OOS_ARMS.exitComparator.budgetDivisor,3);assert.equal(INTEGRATED_OOS_ARMS.primary.exitId,'EXIT_V5_DYNAMIC_RECLAIM_BAR_5');
  for(const value of Object.values(readiness.safety))assert.equal(value,false);
});

test('Integrated OOS runner rejects execution without a separate hash-bound unlock',()=>{
  assert.throws(()=>measureAuthorizedIntegratedOosBundle({},{}),/separate Integrated OOS unlock required/);
});

test('authorized materialized runner preserves four precommitted arms and exact attributions',()=>{
  const t0='2026-10-22T00:00:00.000Z',t1='2026-10-22T00:10:00.000Z',inputSha='a'.repeat(64),freezeSha=digest(fs.readFileSync('predict/research/phase57-capital-allocation-integrated-candidate-freeze.json')),precommitSha=digest(fs.readFileSync('predict/research/phase57-capital-allocation-future-integrated-oos-precommit.json')),contractSha=digest(fs.readFileSync('predict/research/phase57-capital-allocation-validation-contract.json'));
  const bundle={schemaId:'PHASE57_CAPITAL_ALLOCATION_INTEGRATED_OOS_MATERIALIZED_INPUT_V2',evidenceRole:'UNTOUCHED_INTEGRATED_OOS',sourceIdentity:{integratedOosSourceId:'INTEGRATED_OOS_SYNTHETIC_CONTRACT_TEST',sourceManifestSha256:'b'.repeat(64),sessionIds:futureSessions,sessionEligibilityLedger:futureSessions.map(sessionDate=>({sessionDate,eligible:true,sourceAvailabilityStatus:'AVAILABLE'})),eligibilityRuleId:'FIRST_20_CHRONOLOGICALLY_ELIGIBLE_SESSIONS_FROM_2026_10_22_V1',pointInTimeAttestation:true,unopenedBeforeAuthorizationAttestation:true,causalEligibilityAttestation:true},opportunities:[opportunity({eventId:'x',symbol:'1001.T',timestamp:t0})],trades:[trade({eventId:'x',symbol:'1001.T',exitTimestamp:t1,exitPrice:99})],marks:[mark('1001.T',t0,100),mark('1001.T',t1,99)],barCloses:{}};
  const result=measureAuthorizedIntegratedOosBundle(bundle,{inputBundleSha256:inputSha,unlock:{status:'AUTHORIZED_INTEGRATED_OOS_OPEN',candidateFreezeSha256:freezeSha,precommitSha256:precommitSha,contractSha256:contractSha,inputBundleSha256:inputSha}});
  assert.equal(result.status,'INTEGRATED_OOS_MEASURED_NOT_ADJUDICATED');assert.deepEqual(Object.keys(result.arms),['primary','conservativeSub','legacyBaseline','exitComparator']);assert.equal(result.arms.primary.budgetDivisor,3);assert.equal(result.arms.conservativeSub.budgetDivisor,5);assert.equal(result.arms.legacyBaseline.budgetDivisor,10);assert.equal(result.arms.exitComparator.budgetDivisor,3);assert.equal(result.arms.primary.validationMetrics.acceptedTrades,1);assert.equal(result.arms.primary.validationMetrics.belowLotSkip,0);assert.equal(result.comparisons.max5ToMax3.recomposition.matchesTotal,true);assert.equal(result.comparisons.max10ToMax3.recomposition.matchesTotal,true);assert.equal(result.comparisons.primaryV5VsV4.recomposed,true);for(const value of Object.values(PHASE_B_SAFETY))assert.equal(value,false);
});
