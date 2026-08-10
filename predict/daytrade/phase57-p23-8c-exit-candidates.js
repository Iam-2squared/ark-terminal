import { DEFAULT_STATE_MACHINE_CONFIG } from './phase57-trade-management-state-machine.js';
import { P23_5_PRESET_CONFIGS } from './phase57-nested-trade-management-selection.js';

export const PHASE57_P23_8C_SAFETY = Object.freeze({
  mode: 'PHASE57_P23_8C_EXIT_IMPROVEMENT_READ_ONLY_RESEARCH',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  overnightHoldingAllowed: false,
  humanApprovalRequired: true,
});

const prior = P23_5_PRESET_CONFIGS.map(candidate => Object.freeze({
  id: candidate.id,
  config: Object.freeze({ ...candidate.config }),
}));

const v2 = [
  Object.freeze({
    id: 'STATE_PATIENT_PROFIT_CAPTURE_V2',
    config: Object.freeze({
      ...DEFAULT_STATE_MACHINE_CONFIG,
      hardStopAtr: 1.4,
      profitProtectActivationAtr: 1.25,
      profitProtectGivebackAtrStrong: 1.10,
      profitProtectGivebackAtrHold: 0.90,
      profitProtectGivebackAtrCaution: 0.65,
      healthyPullbackAtr: 1.85,
      cautionExitDamageVotes: 5,
      cautionConfirmBars: 3,
      severeBreakdownDamageVotes: 5,
      severeBreakdownConfirmBars: 2,
      minBarsBeforeStateExit: 3,
    }),
  }),
  Object.freeze({
    id: 'STATE_ASYMMETRIC_DEFENSE_V2',
    config: Object.freeze({
      ...DEFAULT_STATE_MACHINE_CONFIG,
      hardStopAtr: 1.20,
      profitProtectActivationAtr: 1.25,
      profitProtectGivebackAtrStrong: 1.25,
      profitProtectGivebackAtrHold: 1.00,
      profitProtectGivebackAtrCaution: 0.70,
      healthyPullbackAtr: 1.75,
      cautionEnterDamageVotes: 2,
      cautionExitDamageVotes: 4,
      cautionConfirmBars: 2,
      severeBreakdownDamageVotes: 4,
      severeBreakdownConfirmBars: 1,
      minBarsBeforeStateExit: 2,
    }),
  }),
  Object.freeze({
    id: 'STATE_STRUCTURE_RUNNER_V2',
    config: Object.freeze({
      ...DEFAULT_STATE_MACHINE_CONFIG,
      swingBars: 5,
      hardStopAtr: 1.35,
      profitProtectActivationAtr: 1.50,
      profitProtectGivebackAtrStrong: 1.40,
      profitProtectGivebackAtrHold: 1.10,
      profitProtectGivebackAtrCaution: 0.75,
      healthyPullbackAtr: 2.0,
      cautionEnterDamageVotes: 3,
      cautionExitDamageVotes: 5,
      cautionConfirmBars: 3,
      severeBreakdownDamageVotes: 4,
      severeBreakdownConfirmBars: 1,
      recoveryHealthyVotes: 5,
      minBarsBeforeStateExit: 3,
    }),
  }),
];

export const P23_8C_EXIT_CANDIDATES = Object.freeze([...prior, ...v2]);
export const P23_8C_NEW_CANDIDATE_IDS = Object.freeze(v2.map(candidate => candidate.id));

export const P23_8C_METHOD_POLICY = Object.freeze({
  objective: 'NET_EXPECTANCY_AFTER_EXPLICIT_COST',
  entryThresholdsChanged: false,
  roundTripCostChanged: false,
  futureExtremaUsedForDecision: false,
  futureExtremaUsedForCandidateSelection: false,
  candidateUniverseFrozenBeforeP23_8COuterEvaluation: true,
  p23_8DiagnosticsInformedCandidateDesign: true,
  reusedRecentDevelopmentWindow: true,
  developmentEvidenceOnly: true,
  finalUntouchedOosEdgeClaimAllowed: false,
  rationale: 'P23.8C tests asymmetric exit candidates that are more patient on mild chart damage, tighter on severe failure, and earlier on profit protection. Candidate design was informed by P23.8 development diagnostics, so this reused window cannot be treated as fresh untouched evidence.',
});

export default {
  P23_8C_EXIT_CANDIDATES,
  P23_8C_NEW_CANDIDATE_IDS,
  P23_8C_METHOD_POLICY,
  PHASE57_P23_8C_SAFETY,
};
