export const P23_10B_FRESH_HOLDOUT_SYMBOLS=Object.freeze([
  '1605.T','5020.T','5401.T','5411.T','5803.T','6301.T','6503.T','6701.T','6702.T','6723.T',
  '6762.T','6857.T','6971.T','6981.T','7012.T','7013.T','7735.T','7751.T','8801.T','8802.T',
  '9020.T','9022.T','9101.T','9104.T','9107.T','9201.T','9202.T','6146.T','3382.T','8591.T',
]);

export const P23_10B_FRESH_HOLDOUT_POLICY=Object.freeze({
  phase:'57.p23.10b-fresh-persistence-holdout',
  status:'PRE_REGISTERED_BEFORE_HOLDOUT_OUTCOME_RETRIEVAL',
  symbolCount:30,
  overlapWithDevelopment30Forbidden:true,
  selectionDescription:'Pre-registered distinct Japanese-equity historical holdout basket; not claimed to be a current index or liquidity ranking.',
  entryMechanism:'P21_1_CAUSAL_ADAPTIVE_ENTRY_PLUS_P23_5_NESTED_STATE_OUTER_ROW_SELECTION',
  exitMechanism:'P23_8D_STATE_MONOTONIC_RATCHET_V1',
  persistenceRule:Object.freeze({
    requiredSameDirectionSignals:3,
    lookbackMinutes:15,
    sameSymbolSameSessionOnly:true,
    currentSignalCountsTowardPersistence:true,
    oneActiveTradePerSymbol:true,
    signalsObservedWhileActiveMayContributeToLaterConfirmation:true,
    ruleFrozenBeforeHoldoutOutcomeRetrieval:true,
  }),
  roundTripCostPct:0.05,
  sameSessionOnly:true,
  overnightHoldingAllowed:false,
  developmentDiagnosticsUsedToMotivateRule:true,
  holdoutOutcomesUsedToChooseRule:false,
  postSelectionOnHoldoutForbidden:true,
  finalEdgeClaimRequiresAdequateSampleAndStability:true,
});

export const PHASE57_P23_10B_SAFETY=Object.freeze({
  mode:'PHASE57_FRESH_PERSISTENCE_HOLDOUT_RESEARCH_ONLY',
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,
  overnightHoldingAllowed:false,humanApprovalRequired:true,
});

export default {P23_10B_FRESH_HOLDOUT_SYMBOLS,P23_10B_FRESH_HOLDOUT_POLICY,PHASE57_P23_10B_SAFETY};
