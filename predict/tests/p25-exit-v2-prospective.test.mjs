import test from 'node:test';
import assert from 'node:assert/strict';
import {runP25ExitV2ProspectivePaired,P25_EXIT_V2_PROSPECTIVE_SAFETY} from '../daytrade/phase57-p25-exit-v2-prospective.js';
import {P25_EXIT_V2_FROZEN_CANDIDATE} from '../daytrade/phase57-p25-exit-v2-freeze.js';
import {P25_EXIT_V2_STATE_CONDITIONED_POLICY_SHA256} from '../daytrade/phase57-p25-exit-v2-state-conditioned.js';

test('prospective evaluator blocks 2026-08-27 before touching evidence because candidate froze after session open',()=>{
  assert.throws(()=>runP25ExitV2ProspectivePaired({freshSessionDate:'2026-08-27'}),/BLOCKED_V2_CANDIDATE_NOT_FROZEN_BEFORE_SESSION_OPEN/);
});

test('frozen prospective identity remains bound to exact v2 policy and first eligible session',()=>{
  assert.equal(P25_EXIT_V2_FROZEN_CANDIDATE.policySha256,P25_EXIT_V2_STATE_CONDITIONED_POLICY_SHA256);
  assert.equal(P25_EXIT_V2_FROZEN_CANDIDATE.firstProspectivelyEligibleSession,'2026-08-28');
  assert.equal(P25_EXIT_V2_FROZEN_CANDIDATE.developmentCutoff,'2026-08-12');
  assert.equal(P25_EXIT_V2_FROZEN_CANDIDATE.legacy27DiagnosticsOnly,true);
  assert.equal(P25_EXIT_V2_FROZEN_CANDIDATE.resultBasedRetuning,false);
});

test('prospective evaluator preserves research-only safety boundaries',()=>{
  for(const k of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed'])assert.equal(P25_EXIT_V2_PROSPECTIVE_SAFETY[k],false);
});
