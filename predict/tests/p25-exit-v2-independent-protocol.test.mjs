import test from 'node:test';
import assert from 'node:assert/strict';
import {P25_EXIT_V2_INDEPENDENT_PROTOCOL,validateP25ExitV2DevelopmentDates,validateP25ExitV2FreshCandidate} from '../daytrade/phase57-p25-exit-v2-independent-protocol.js';

test('allows development data only through the frozen 2026-08-12 cutoff',()=>{
  assert.equal(validateP25ExitV2DevelopmentDates(['2026-08-01','2026-08-12']).ready,true);
  assert.equal(validateP25ExitV2DevelopmentDates(['2026-08-13']).status,'BLOCKED_V2_POST_CUTOFF_DEVELOPMENT_DATA');
  assert.equal(validateP25ExitV2DevelopmentDates(['2026-08-25']).ready,false);
});

test('requires a frozen candidate and complete immutable fresh session',()=>{
  const ok=validateP25ExitV2FreshCandidate({candidateFrozenAt:'2026-08-26T00:00:00Z',freshSessionDate:'2026-08-26',freshSessionComplete:true,freshSessionImmutable:true});
  assert.equal(ok.ready,true);
  assert.equal(validateP25ExitV2FreshCandidate({candidateFrozenAt:'2026-08-26T00:00:00Z',freshSessionDate:'2026-08-26',freshSessionComplete:false,freshSessionImmutable:true}).status,'BLOCKED_V2_FRESH_SESSION_INCOMPLETE');
  assert.equal(validateP25ExitV2FreshCandidate({candidateFrozenAt:'2026-08-26T00:00:00Z',freshSessionDate:'2026-08-25',freshSessionComplete:true,freshSessionImmutable:true}).ready,false);
});

test('legacy 27 outcomes remain diagnostics-only and cannot tune v2',()=>{
  assert.equal(P25_EXIT_V2_INDEPENDENT_PROTOCOL.existing27AllowedForDiagnosticsOnly,true);
  assert.equal(P25_EXIT_V2_INDEPENDENT_PROTOCOL.existing27AllowedForThresholdTuning,false);
  assert.equal(P25_EXIT_V2_INDEPENDENT_PROTOCOL.existing27AllowedForFeatureTuning,false);
  assert.equal(P25_EXIT_V2_INDEPENDENT_PROTOCOL.existing27AllowedForHorizonTuning,false);
  assert.equal(P25_EXIT_V2_INDEPENDENT_PROTOCOL.existing27AllowedForCoefficientTuning,false);
  assert.equal(P25_EXIT_V2_INDEPENDENT_PROTOCOL.freshHoldoutConsumed,false);
  assert.equal(P25_EXIT_V2_INDEPENDENT_PROTOCOL.automaticPromotionAllowed,false);
});
