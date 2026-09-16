import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {hash,digest,instant,exposedDate,FREEZE,SAFETY} from './phase57-offline-parity.mjs';
import {applyExternalCashFlow} from './phase57-operational-robustness.mjs';

export const MODES=Object.freeze(['OFFLINE_FIXTURE','SOURCE_SEMANTICS_ONLY','REALTIME_SHADOW','POST_CLOSE_PARITY']);
// A mode name cannot unlock a reserved session or relabel real data as a fixture.
export function admitMode({mode,sourceClass,sessionDate}) {
  assert.ok(MODES.includes(mode),'EXPLICIT_MODE_REQUIRED');
  if(mode==='SOURCE_SEMANTICS_ONLY') {
    assert.ok(['REAL_SOURCE_DIAGNOSTIC','SYNTHETIC_TRANSPORT_TEST'].includes(sourceClass),'SOURCE_CLASS_MISMATCH');
    assert.match(sessionDate,/^2026-\d{2}-\d{2}$/);
    assert.ok(sessionDate<'2026-10-22','FUTURE_OOS_LOCKED');
    return {mode,strategyAllowed:false,sourceOnly:true,safety:SAFETY};
  }
  if(mode==='REALTIME_SHADOW') throw Error('REALTIME_SHADOW_LOCKED_REQUIRES_SOURCE_AND_SESSION_ADMISSION');
  assert.ok(['USED_HISTORICAL_FIXTURE','SYNTHETIC_TRANSPORT_TEST'].includes(sourceClass),'REAL_DATA_CANNOT_BE_FIXTURE');
  exposedDate(sessionDate);
  return {mode,strategyAllowed:mode==='OFFLINE_FIXTURE',sourceOnly:false,safety:SAFETY};
}

// Independent synthetic balance interface: never mutates the frozen historical ledger.
export class SyntheticCashBook {
  constructor(snapshot){this.state=structuredClone(snapshot);this.seen=new Map();this.last=-Infinity;}
  apply(event){
    assert.equal(event.sourceClass,'SYNTHETIC_TRANSPORT_TEST','SYNTHETIC_ONLY');
    assert.ok(typeof event.id==='string'&&event.id.length,'CASH_EVENT_ID_REQUIRED');
    const fingerprint=hash(event);
    if(this.seen.has(event.id)){assert.equal(this.seen.get(event.id),fingerprint,'CONFLICTING_CASH_EVENT');return this.snapshot();}
    const t=instant(event.timestamp);assert.ok(t>=this.last,'NONCAUSAL_CASH_EVENT');
    const next=applyExternalCashFlow(this.state,event);
    this.state=next;this.seen.set(event.id,fingerprint);this.last=t;return this.snapshot();
  }
  snapshot(){return {...structuredClone(this.state),nextSlotBudgetJpy:this.state.equityJpy/3,executionAllowed:false};}
}

// Diagnostic constraints never clamp/change the frozen shadow quantity.
export function capacityBoundary({strategyDesiredQuantity,frozenShadowQuantity,diagnostics={}}){
  for(const n of [strategyDesiredQuantity,frozenShadowQuantity])assert.ok(Number.isInteger(n)&&n>=0&&n%100===0,'INVALID_100_SHARE_QUANTITY');
  assert.ok(frozenShadowQuantity<=strategyDesiredQuantity,'SHADOW_EXCEEDS_DESIRED');
  const required=['cash','lot','positionLimit','orderNotional','symbolEligibility','halt','priceLimit','liquidity','shortAvailability','freshPrice'];
  const unknown=required.filter(k=>!['PASS','FAIL'].includes(diagnostics[k]));
  const failed=required.filter(k=>diagnostics[k]==='FAIL');
  return {strategyDesiredQuantity,constraintAllowedQuantity:unknown.length||failed.length?null:frozenShadowQuantity,
    finalExecutableQuantity:frozenShadowQuantity,quantityMeaning:'HYPOTHETICAL_SHADOW_ONLY',unknownConstraints:unknown,failedConstraints:failed,
    constraintStatus:unknown.length?'UNKNOWN_CONSTRAINT':failed.length?'CONSTRAINT_FAILED':'DIAGNOSTICS_PASS',executionAllowed:false,transmitted:false};
}

export function inspectOosPrecommit(root){
  const file=path.join(root,'predict/research/phase57-capital-allocation-future-integrated-oos-precommit.json');
  const bytes=fs.readFileSync(file),contract=JSON.parse(bytes);
  assert.equal(contract.candidateFreezeSha256,FREEZE);
  assert.equal(contract.window.notBeforeSessionDate,'2026-10-22');
  assert.equal(contract.window.targetEligibleMarketSessions,20);
  assert.deepEqual(Object.values(contract.arms).map(x=>[x.budgetDivisor,x.exit]),[[3,'EXIT_V5_DYNAMIC_RECLAIM_BAR_5'],[5,'EXIT_V5_DYNAMIC_RECLAIM_BAR_5'],[10,'EXIT_V5_DYNAMIC_RECLAIM_BAR_5'],[3,'FROZEN_EXIT_V4']]);
  return {precommitSha256:digest(bytes),freezeSha256:FREEZE,window:contract.window,arms:contract.arms,unlockAllowed:false,outcomesRead:false,
    sourceBoundary:'EXISTING_JQUANTS_CONTRACT_NOT_REPLACED_BY_MSII',safety:SAFETY};
}
