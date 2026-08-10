import { evaluateLeaveSymbolOutRolling, PHASE57_P23_9F_SAFETY } from './phase57-leave-symbol-out-opportunity.js';

export const PHASE57_P23_10A_SAFETY=Object.freeze({...PHASE57_P23_9F_SAFETY,mode:'PHASE57_ADAPTIVE_SIGNAL_META_LABEL_RESEARCH_ONLY'});
export const P23_10A_CONFIG=Object.freeze({
  k:16,
  fitLookbackSessions:24,
  calibrationSessionCount:3,
  maxCalibrationRows:120,
  minimumCalibrationSignals:10,
  minimumCalibrationNetPct:0.02,
  minimumCalibrationProfitFactor:1.10,
  sameSymbolOutcomeNeighborsForbidden:true,
});

function validMetaExample(row){
  return row?.baseSignalOosValid===true
    && row?.pointInTimeFeaturesOnly===true
    && row?.futureTargetsEvaluationOnly===true
    && row?.baseSignalSource==='P21_1_OUTER_OOS_REPLAY'
    && row?.sameSessionOnly===true
    && Number.isFinite(Number(row?.realizedRatchetNetReturnPct));
}

export function evaluateAdaptiveSignalMetaLabel({historicalSignalExamples=[],frozenTestExamples=[],config={}}={}){
  const training=(Array.isArray(historicalSignalExamples)?historicalSignalExamples:[]).filter(validMetaExample);
  const tests=(Array.isArray(frozenTestExamples)?frozenTestExamples:[]).filter(row=>row?.pointInTimeFeaturesOnly===true&&row?.futureTargetsEvaluationOnly===true);
  const cfg={...P23_10A_CONFIG,...config};
  const evaluation=evaluateLeaveSymbolOutRolling({trainingExamples:training,frozenTestExamples:tests,config:cfg});
  return Object.freeze({
    phase:'57.p23.10a-adaptive-signal-meta-label',
    status:'ADAPTIVE_SIGNAL_META_LABEL_EVALUATED',
    historicalSignalExampleCount:training.length,
    frozenTestCount:tests.length,
    config:Object.freeze(cfg),
    evaluation,
    integrity:Object.freeze({
      trainingPopulation:'CAUSAL_BASE_ENTRY_OOS_SIGNALS_ONLY',
      baseSignalsOuterOosOnly:true,
      baseSignalSelectionUsesInnerOnly:true,
      metaTrainingUsesOnlyPriorSessions:true,
      sameSymbolOutcomeNeighborsForbidden:true,
      futureExtremaUsedAsFeatures:false,
      frozenOuterOutcomesUsedForGateSelection:false,
      candidateFamilyInheritedWithoutOuterRetuning:true,
      developmentOnly:true,
      finalUntouchedOosEdgeClaimAllowed:false,
    }),
    edgeClaimAllowed:false,recommendationAllowed:false,
    executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,
    liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,
    overnightHoldingAllowed:false,transmitted:false,safety:PHASE57_P23_10A_SAFETY,
  });
}

export default {PHASE57_P23_10A_SAFETY,P23_10A_CONFIG,evaluateAdaptiveSignalMetaLabel};
