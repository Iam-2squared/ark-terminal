import {P25_EXIT_V2_STATE_CONDITIONED_POLICY_SHA256} from './phase57-p25-exit-v2-state-conditioned.js';
import {validateP25ExitV2FreshCandidate} from './phase57-p25-exit-v2-independent-protocol.js';

export const P25_EXIT_V2_FROZEN_CANDIDATE=Object.freeze({
  candidateId:'P25_EXIT_V2_STATE_CONDITIONED_20260827',
  candidateFamily:'STATE_CONDITIONED_ANALOG_EXIT',
  candidateCommitSha:'1cec425bea7901439f3ff1329bbf855cc4c37699',
  candidateFrozenAt:'2026-08-27T00:48:00Z',
  policySha256:'127a7ba21698605836e5c4e0c0ad38f0f9d5e743a7e0c708a56a600745f09ace',
  developmentCutoff:'2026-08-12',
  legacy27DiagnosticsOnly:true,
  firstProspectivelyEligibleSession:'2026-08-28',
  exactDynamic50Only:true,
  sameFrozenEntryAsFixed:true,
  resultBasedRetuning:false,
  freshHoldoutConsumed:false,
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

export function validateP25ExitV2FrozenCandidateIdentity(){
  if(P25_EXIT_V2_STATE_CONDITIONED_POLICY_SHA256!==P25_EXIT_V2_FROZEN_CANDIDATE.policySha256){
    return Object.freeze({ready:false,status:'BLOCKED_V2_FROZEN_POLICY_HASH_MISMATCH'});
  }
  const first=validateP25ExitV2FreshCandidate({
    candidateFrozenAt:P25_EXIT_V2_FROZEN_CANDIDATE.candidateFrozenAt,
    freshSessionDate:P25_EXIT_V2_FROZEN_CANDIDATE.firstProspectivelyEligibleSession,
    freshSessionComplete:true,
    freshSessionImmutable:true,
  });
  if(!first.ready)return Object.freeze({ready:false,status:first.status});
  return Object.freeze({ready:true,status:'P25_EXIT_V2_CANDIDATE_FROZEN',candidate:P25_EXIT_V2_FROZEN_CANDIDATE});
}

export default {P25_EXIT_V2_FROZEN_CANDIDATE,validateP25ExitV2FrozenCandidateIdentity};