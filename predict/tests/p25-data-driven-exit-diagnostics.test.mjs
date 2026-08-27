import test from 'node:test';
import assert from 'node:assert/strict';
import {buildP25ExitV1DiagnosticEvidence,P25_EXIT_V1_DIAGNOSTIC_POLICY} from '../daytrade/phase57-p25-data-driven-exit-diagnostics.js';

const pair=(key,fixed,data,exitReason='DATA_DRIVEN_EXPECTED_VALUE_EXIT')=>({
  key,sessionDate:'2026-08-25',symbol:key,fixed:{netReturnPct:fixed},deltaNetReturnPct:data-fixed,
  dataDriven:{netReturnPct:data,exitReason,barsHeld:2,mfePct:3,maePct:-1,givebackPct:1,captureRatio:0.5,
    managementDecisions:[{reason:exitReason==='DATA_DRIVEN_EXPECTED_VALUE_EXIT'?'NO_POSITIVE_REMAINING_EDGE_AT_90CI':'POSITIVE_REMAINING_EDGE_NOT_REJECTED',bestHorizonBars:3,bestUpper90Pct:-0.1,state:{currentReturnPct:data}}]},
});

test('classifies active EXIT failure modes without policy tuning',()=>{
  const out=buildP25ExitV1DiagnosticEvidence([
    pair('loss-rescue',-5,-2),
    pair('win-improved',2,3),
    pair('win-truncated',5,1),
    pair('loss-worsened',-2,-4),
    pair('equal',1,1),
    pair('hold',2,2,'SESSION_END'),
  ]);
  assert.equal(out.counts.paired,6);
  assert.equal(out.counts.activeExit,5);
  assert.equal(out.counts.noActiveExit,1);
  assert.deepEqual(out.counts.classes,{LOSS_RESCUE:1,WIN_IMPROVED:1,WIN_TRUNCATED:1,LOSS_WORSENED:1,ACTIVE_EXIT_EQUAL:1});
  assert.equal(out.rows.find(x=>x.key==='hold').class,'NO_ACTIVE_EXIT');
  assert.equal(out.dataDrivenPath.meanMfePct,3);
  assert.equal(out.dataDrivenPath.meanMaePct,-1);
  assert.equal(out.activeExitPath.meanBarsHeld,2);
  assert.equal(P25_EXIT_V1_DIAGNOSTIC_POLICY.thresholdSearchAllowed,false);
  assert.equal(P25_EXIT_V1_DIAGNOSTIC_POLICY.outcomeTuningAllowed,false);
  assert.equal(P25_EXIT_V1_DIAGNOSTIC_POLICY.changesDecisionSemantics,false);
});

test('diagnostic output is deterministic for the same pair ordering',()=>{
  const rows=[pair('a',1,-1),pair('b',-1,2)];
  assert.deepEqual(buildP25ExitV1DiagnosticEvidence(rows),buildP25ExitV1DiagnosticEvidence(rows));
});
