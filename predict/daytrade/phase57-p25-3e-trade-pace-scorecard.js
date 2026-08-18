import {PHASE57_P25_2H_VARIANTS} from './phase57-p25-2h-multisession-evidence-accumulator.js';

export const PHASE57_P25_3E_SAFETY=Object.freeze({
  phase:'57.p25.3e.trade-pace-scorecard',
  mode:'READ_ONLY_DESCRIPTIVE_PROSPECTIVE_SCORECARD',
  researchOnly:true,
  executionAllowed:false,
  brokerWriteAllowed:false,
  excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,
  paperTradingAllowed:false,
  automaticPromotionAllowed:false,
  productionUpdateAllowed:false,
  transmitted:false,
  freshHoldoutConsumed:false,
});

export const PHASE57_P25_3E_POLICY=Object.freeze({
  variants:PHASE57_P25_2H_VARIANTS,
  targetTradeCount:400,
  targetTradingDays:Object.freeze([30,20]),
  allFiveVariantsRetained:true,
  variantRankingAllowed:false,
  winnerSelectionAllowed:false,
  dynamicNSelectedFromCurrentOuterOos:false,
  entryThresholdRelaxationAllowed:false,
  postHocWinnerFilteringAllowed:false,
  performancePromotionAllowed:false,
  dailyMarketSpeedRequired:false,
  boardOrTickUsed:false,
  microstructureUsed:false,
});

const SAFETY_FALSE_KEYS=Object.freeze([
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed',
  'transmitted','freshHoldoutConsumed',
]);
const finite=value=>value!==null&&value!==undefined&&value!==''&&Number.isFinite(Number(value));
const numberOrNull=value=>finite(value)?Number(value):null;
const round=(value,digits=6)=>Number.isFinite(value)?Number(Number(value).toFixed(digits)):null;

function assertSafetyFalse(safety,label){
  for(const key of SAFETY_FALSE_KEYS){
    if(safety?.[key]!==false)throw new Error(`P25.3E ${label} safety ${key} must be false`);
  }
}
function unwrapEvaluation(input){
  if(input?.phase==='57.p25.3d.autonomous-evidence-evaluation-cli')return input.evaluation;
  return input;
}
function targetPace(targetTradeCount,targetTradingDays){
  return Object.freeze(targetTradingDays.map(days=>Object.freeze({
    tradingDays:days,
    requiredEntriesPerTradingSession:round(targetTradeCount/days),
  })));
}

/**
 * Build a stable descriptive scorecard from the lineage-pinned P25.3D result.
 * It deliberately preserves the precommitted variant order and never ranks or
 * selects a Dynamic N from current outer-OOS performance.
 */
export function buildP253TradePaceScorecard({evaluationArtifact}={}){
  const evaluation=unwrapEvaluation(evaluationArtifact);
  if(evaluation?.phase!=='57.p25.3d.autonomous-evidence-evaluation'||evaluation?.status!=='P25_3_AUTONOMOUS_EVIDENCE_EVALUATED')throw new Error('P25.3E requires a completed P25.3D autonomous evidence evaluation');
  assertSafetyFalse(evaluation?.safety,'P25.3D evaluation');
  if(evaluation?.methodology?.currentOuterOosDoesNotSelectDynamicN!==true||evaluation?.methodology?.allFiveVariantsRetained!==true)throw new Error('P25.3E requires the frozen all-five no-selection policy');

  const result=evaluation?.result;
  if(result?.phase!=='57.p25.2i.end-to-end-prospective-evaluation')throw new Error('P25.3E missing P25.2I result');
  assertSafetyFalse(result?.safety,'P25.2I result');
  const evidence=result?.evidence;
  if(evidence?.phase!=='57.p25.2h.multisession-evidence-accumulator')throw new Error('P25.3E missing P25.2H accumulated evidence');
  assertSafetyFalse(evidence?.safety,'P25.2H evidence');

  const frequency=evidence?.operationalTradeFrequency??{};
  const comparison=evidence?.comparison;
  if(comparison?.phase!=='57.p25.2d.precommitted-prospective-comparison')throw new Error('P25.3E missing P25.2D five-variant comparison');
  assertSafetyFalse(comparison?.safety,'P25.2D comparison');

  const targetTradeCount=PHASE57_P25_3E_POLICY.targetTradeCount;
  const paceTargets=targetPace(targetTradeCount,PHASE57_P25_3E_POLICY.targetTradingDays);
  const rows=[];
  for(const variant of PHASE57_P25_2H_VARIANTS){
    const operational=frequency?.[variant];
    const performance=comparison?.results?.[variant];
    if(!operational)throw new Error(`P25.3E operational frequency missing ${variant}`);
    if(!performance)throw new Error(`P25.3E performance summary missing ${variant}`);
    const frozenEntries=numberOrNull(operational.validFrozenEntries);
    const resolvedEntries=numberOrNull(performance.validFrozenEntries);
    const entriesPerSession=numberOrNull(operational.validFrozenEntriesPerTradingSession);
    const targetProgress=Object.freeze(paceTargets.map(target=>Object.freeze({
      ...target,
      currentEntriesPerTradingSession:entriesPerSession,
      paceRatio:entriesPerSession===null?null:round(entriesPerSession/target.requiredEntriesPerTradingSession),
      currentlyAtOrAboveTargetPace:entriesPerSession===null?null:entriesPerSession>=target.requiredEntriesPerTradingSession,
    })));
    rows.push(Object.freeze({
      variant,
      expectedTradingSessions:numberOrNull(operational.tradingSessions),
      commonReadyTradingSessions:numberOrNull(performance.evaluatedTradingSessions),
      frozenEntries,
      resolvedEntries,
      unresolvedFrozenEntries:frozenEntries===null||resolvedEntries===null?null:Math.max(0,frozenEntries-resolvedEntries),
      entriesPerTradingSession:entriesPerSession,
      observedDaysTo400:numberOrNull(operational.observedDaysToTarget),
      paceEstimatedDaysTo400:numberOrNull(operational.paceEstimatedDaysToTarget),
      targetProgress,
      hitRate:numberOrNull(performance.hitRate),
      tradeWinRate:numberOrNull(performance.tradeWinRate),
      afterCostNetPct:numberOrNull(performance.afterCostNetPct),
      profitFactor:numberOrNull(performance.profitFactor),
      maxDrawdownPct:numberOrNull(performance.maxDrawdownPct),
      meanNetReturnPct:numberOrNull(performance.meanNetReturnPct),
      coverage:numberOrNull(performance.coverage),
      coverageDenominator:numberOrNull(performance.coverageDenominator),
      conservativeEffectiveIndependentEntries:numberOrNull(performance?.sameTimeCorrelation?.conservativeEffectiveIndependentEntries),
      conservativeIndependenceRatio:numberOrNull(performance?.sameTimeCorrelation?.conservativeIndependenceRatio),
      sessionEqualWeightAfterCostNetPct:numberOrNull(performance?.sessionEqualWeightPortfolio?.afterCostNetPct),
      largestSymbolShare:numberOrNull(performance?.symbolConcentration?.largestShare),
      symbolHhi:numberOrNull(performance?.symbolConcentration?.hhi),
      largestSectorShare:numberOrNull(performance?.sectorConcentration?.largestShare),
      sectorHhi:numberOrNull(performance?.sectorConcentration?.hhi),
    }));
  }

  return Object.freeze({
    phase:'57.p25.3e.trade-pace-scorecard',
    status:'P25_3_TRADE_PACE_SCORECARD_READY',
    lineageManifestHeadSha256:String(evaluation.lineageManifestHeadSha256??''),
    targetTradeCount,
    paceTargets,
    expectedSessionCount:Number(evaluation.expectedSessionCount??0),
    frozenReadySessionInputCount:Number(evaluation.frozenReadySessionInputCount??0),
    readyPacketCount:Number(result.readyPacketCount??0),
    blockedSessionCount:Number(result.blockedSessionCount??0),
    rows:Object.freeze(rows),
    methodology:Object.freeze({
      descriptiveOnly:true,
      allFiveVariantsRetained:true,
      fixedVariantDisplayOrder:true,
      variantsRankedByPerformance:false,
      currentOuterOosDoesNotSelectDynamicN:true,
      entryThresholdRelaxed:false,
      postHocWinnerFiltering:false,
      performanceConclusionAllowed:false,
      targetPaceIsArithmeticOnly:true,
      dailyMarketSpeedRequired:false,
      boardOrTickUsed:false,
      microstructureUsed:false,
      freshHoldoutConsumed:false,
    }),
    safety:PHASE57_P25_3E_SAFETY,
  });
}

export default {buildP253TradePaceScorecard,PHASE57_P25_3E_POLICY,PHASE57_P25_3E_SAFETY};
