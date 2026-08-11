import {P23_11B_RESERVE_HOLDOUT_B_SYMBOLS} from './phase57-reserve-holdout-b.js';
export const P23_11B_HOLDOUT_B_POLICY=Object.freeze({
  phase:'57.p23.11b-fresh-daily-cap-persistence-holdout',
  status:'ARCHITECTURE_ASSIGNED_BEFORE_RESERVE_HOLDOUT_B_OUTCOME_RETRIEVAL',
  reserveUniverseCommit:'28d1b8c21c142bb04b1b4aa67e9c23e9fdc2dba3',
  symbols:P23_11B_RESERVE_HOLDOUT_B_SYMBOLS,
  entryMechanism:'P21_1_CAUSAL_ADAPTIVE_ENTRY_PLUS_P23_5_NESTED_STATE_OUTER_ROW_SELECTION',
  exitMechanism:'P23_8D_STATE_MONOTONIC_RATCHET_V1',
  persistenceRule:Object.freeze({requiredSameDirectionSignals:3,lookbackMinutes:15,sameSymbolSameSessionOnly:true,currentSignalCounts:true,oneActiveTradePerSymbol:true,maxAcceptedTradesPerSymbolPerSession:1,signalsObservedAfterDailyCapMayBeIgnored:true}),
  roundTripCostPct:0.05,sameSessionOnly:true,overnightHoldingAllowed:false,
  developmentEvidenceUsedToAssignArchitecture:true,reserveHoldoutBOutcomesUsedToAssignArchitecture:false,postSelectionOnReserveHoldoutBForbidden:true,
  practicalResearchGate:Object.freeze({minimumSignals:30,minimumProfitFactor:1.20,minimumNetAverageReturnPct:0.05,minimumPositiveShards:2,maximumSingleSymbolSignalShare:0.35,minimumUniqueSymbols:10}),
});
export const PHASE57_P23_11B_SAFETY=Object.freeze({mode:'PHASE57_FRESH_DAILY_CAP_PERSISTENCE_HOLDOUT_RESEARCH_ONLY',executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,overnightHoldingAllowed:false,humanApprovalRequired:true});
export default {P23_11B_HOLDOUT_B_POLICY,PHASE57_P23_11B_SAFETY};
