export const P25_EXIT_V3_INDEPENDENT_PROTOCOL=Object.freeze({
  phase:'57.p25.exit-v3.independent-protocol',
  candidateFamily:'DUAL_GATE_STATE_CONDITIONED_EXIT',
  objective:'Study loser-rescue timing and winner-protection confirmation without tuning on legacy27 diagnostics.',
  developmentCutoff:'2026-08-12',
  nestedDevelopment:Object.freeze({fitEnd:'2026-07-31',validationStart:'2026-08-01',validationEnd:'2026-08-12'}),
  inheritedFrozenSurfaces:Object.freeze({exactDynamic50Only:true,sameFrozenEntryAsFixed:true,fixedBaselineUntouched:true,analogPoolCutoff:'2026-08-12',forecastHorizonsBars:Object.freeze([1,3,6])}),
  researchQuestions:Object.freeze([
    'LOSER_RESCUE: can causal pre-cutoff evidence distinguish early rescue from late loss deepening?',
    'WINNER_PROTECTION: can causal pre-cutoff evidence require confirmation before truncating a still-healthy winner?'
  ]),
  legacy27Role:'DIAGNOSTIC_HYPOTHESIS_GENERATION_ONLY',
  legacy27UsedForThresholdTuning:false,
  legacy27UsedForFeatureSelection:false,
  legacy27UsedForHorizonSelection:false,
  legacy27UsedForCoefficientSelection:false,
  legacy27UsedForCandidateSelection:false,
  freshOutcomeUsedForFitting:false,
  resultBasedRetuning:false,
  formalOosEvidence:false,
  promotionEligible:false,
  freshHoldoutConsumed:false,
});
export const P25_EXIT_V3_SAFETY=Object.freeze({executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,freshHoldoutConsumed:false});
export function validateP25ExitV3DevelopmentDate(date){const d=String(date??'');if(!/^\d{4}-\d{2}-\d{2}$/.test(d))return Object.freeze({ready:false,status:'BLOCKED_V3_INVALID_DATE'});if(d>P25_EXIT_V3_INDEPENDENT_PROTOCOL.developmentCutoff)return Object.freeze({ready:false,status:'BLOCKED_V3_POST_CUTOFF_DATA'});return Object.freeze({ready:true,status:'V3_PRE_CUTOFF_DEVELOPMENT_ONLY',date:d});}
export function classifyP25ExitV3DevelopmentSplit(date){const v=validateP25ExitV3DevelopmentDate(date);if(!v.ready)return v;const {fitEnd,validationStart,validationEnd}=P25_EXIT_V3_INDEPENDENT_PROTOCOL.nestedDevelopment;if(v.date<=fitEnd)return Object.freeze({ready:true,split:'FIT',date:v.date});if(v.date>=validationStart&&v.date<=validationEnd)return Object.freeze({ready:true,split:'VALIDATION',date:v.date});return Object.freeze({ready:true,split:'GAP_OR_UNUSED',date:v.date});}
export default {P25_EXIT_V3_INDEPENDENT_PROTOCOL,P25_EXIT_V3_SAFETY,validateP25ExitV3DevelopmentDate,classifyP25ExitV3DevelopmentSplit};
