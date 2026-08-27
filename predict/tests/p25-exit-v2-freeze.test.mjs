import test from 'node:test';
import assert from 'node:assert/strict';
import {P25_EXIT_V2_STATE_CONDITIONED_POLICY_SHA256} from '../daytrade/phase57-p25-exit-v2-state-conditioned.js';
import {P25_EXIT_V2_FROZEN_CANDIDATE,validateP25ExitV2FrozenCandidateIdentity} from '../daytrade/phase57-p25-exit-v2-freeze.js';
import {validateP25ExitV2FreshCandidate} from '../daytrade/phase57-p25-exit-v2-independent-protocol.js';

test('frozen v2 identity matches the implemented state-conditioned policy',()=>{
  assert.equal(P25_EXIT_V2_STATE_CONDITIONED_POLICY_SHA256,P25_EXIT_V2_FROZEN_CANDIDATE.policySha256);
  const checked=validateP25ExitV2FrozenCandidateIdentity();
  assert.equal(checked.ready,true);
  assert.equal(checked.status,'P25_EXIT_V2_CANDIDATE_FROZEN');
});

test('8/27 is not prospective because candidate froze after 09:00 JST open; 8/28 is first eligible',()=>{
  const sameDay=validateP25ExitV2FreshCandidate({candidateFrozenAt:P25_EXIT_V2_FROZEN_CANDIDATE.candidateFrozenAt,freshSessionDate:'2026-08-27',freshSessionComplete:true,freshSessionImmutable:true});
  assert.equal(sameDay.ready,false);
  assert.equal(sameDay.status,'BLOCKED_V2_CANDIDATE_NOT_FROZEN_BEFORE_SESSION_OPEN');
  const nextDay=validateP25ExitV2FreshCandidate({candidateFrozenAt:P25_EXIT_V2_FROZEN_CANDIDATE.candidateFrozenAt,freshSessionDate:'2026-08-28',freshSessionComplete:true,freshSessionImmutable:true});
  assert.equal(nextDay.ready,true);
});

test('frozen candidate preserves all research-only safety boundaries',()=>{
  assert.equal(P25_EXIT_V2_FROZEN_CANDIDATE.legacy27DiagnosticsOnly,true);
  assert.equal(P25_EXIT_V2_FROZEN_CANDIDATE.resultBasedRetuning,false);
  assert.equal(P25_EXIT_V2_FROZEN_CANDIDATE.freshHoldoutConsumed,false);
  for(const k of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted'])assert.equal(P25_EXIT_V2_FROZEN_CANDIDATE[k],false);
});