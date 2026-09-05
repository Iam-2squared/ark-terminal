import {
  buildP252FixedPortfolioSessions,
  PHASE57_P25_LANE_C_ALLOCATION_PROFILES,
  PHASE57_P25_LANE_C_POLICY,
} from './phase57-p25-lane-c-portfolio-simulator.js';
import {
  buildLaneCFixedCheckpointPackets,
  PHASE57_P25_LANE_C_FIXED_RUNNER_POLICY,
  PHASE57_P25_LANE_C_FIXED_RUNNER_SAFETY,
  runLaneCFixedCheckpointedPortfolio,
} from './phase57-p25-lane-c-fixed-checkpoint-runner.js';
import {
  PHASE57_CAR1_PROFILES,
  PHASE57_CAR1_SAFETY,
} from './phase57-car1-sizing-research.js';
import {runCar1CounterfactualPortfolioAttribution} from './phase57-car1-counterfactual-replay.js';

export const PHASE57_CAR1_CHECKPOINT_SAFETY=Object.freeze({
  phase:'57.car1.checkpointed-sizing-attribution',
  mode:'READ_ONLY_LINEAGE_PINNED_COUNTERFACTUAL_RESEARCH',
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
  winnerSelectionAllowed:false,
  formalOos:false,
  freshHoldoutConsumed:false,
});

export const PHASE57_CAR1_CHECKPOINT_POLICY=Object.freeze({
  managementMode:'FIXED_HORIZON',
  defaultUniverseVariants:Object.freeze(['DYNAMIC_50']),
  baselineProfiles:Object.freeze(PHASE57_P25_LANE_C_ALLOCATION_PROFILES.map(row=>row.id)),
  sizingProfiles:Object.freeze(PHASE57_CAR1_PROFILES.map(row=>row.id)),
  roundTripCostPct:PHASE57_P25_LANE_C_POLICY.fixedRoundTripCostPct,
  slippageBps:PHASE57_P25_LANE_C_POLICY.baselineSlippageBps,
  baselineBudgetEnvelopeAnchored:true,
  rankingChanged:false,
  selectorChanged:false,
  entryChanged:false,
  exitChanged:false,
  parameterSearchAllowed:false,
  winnerSelectionAllowed:false,
  promotionEligible:false,
});

const FALSE_KEYS=Object.freeze([
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted',
]);
const close=(a,b,tolerance=1e-6)=>Math.abs(Number(a)-Number(b))<=tolerance;
const round=(value,digits=6)=>Number.isFinite(Number(value))?Number(Number(value).toFixed(digits)):value;

function assertSafety(){
  for(const key of FALSE_KEYS){
    if(PHASE57_CAR1_CHECKPOINT_SAFETY[key]!==false)throw new Error(`CAR-1 checkpoint safety ${key} must remain false`);
    if(PHASE57_CAR1_SAFETY[key]!==false)throw new Error(`CAR-1 sizing safety ${key} must remain false`);
    if(PHASE57_P25_LANE_C_FIXED_RUNNER_SAFETY[key]!==false)throw new Error(`Lane C Fixed safety ${key} must remain false`);
  }
  if(PHASE57_CAR1_CHECKPOINT_SAFETY.winnerSelectionAllowed!==false||PHASE57_CAR1_SAFETY.winnerSelectionAllowed!==false){
    throw new Error('CAR-1 winner selection must remain disabled');
  }
}

function selectedBaselineProfiles(profileIds){
  const ids=[...(Array.isArray(profileIds)?profileIds:PHASE57_P25_LANE_C_ALLOCATION_PROFILES.map(row=>row.id))];
  if(!ids.length||new Set(ids).size!==ids.length)throw new Error('CAR-1 baseline profile ids must be unique and non-empty');
  const byId=new Map(PHASE57_P25_LANE_C_ALLOCATION_PROFILES.map(row=>[row.id,row]));
  return ids.map(id=>{
    const profile=byId.get(id);
    if(!profile)throw new Error(`unknown CAR-1 baseline profile: ${id}`);
    return profile;
  });
}

function selectedSizingProfiles(profileIds){
  const ids=[...(Array.isArray(profileIds)?profileIds:PHASE57_CAR1_PROFILES.map(row=>row.id))];
  if(!ids.length||new Set(ids).size!==ids.length)throw new Error('CAR-1 sizing profile ids must be unique and non-empty');
  const known=new Set(PHASE57_CAR1_PROFILES.map(row=>row.id));
  for(const id of ids)if(!known.has(id))throw new Error(`unknown CAR-1 sizing profile: ${id}`);
  return ids;
}

function assertBaselineParity({fixedComparison,baselineProfileId,attribution}){
  const fixed=fixedComparison?.results?.[baselineProfileId];
  if(!fixed||fixed.status!=='LANE_C_PORTFOLIO_SIMULATED')throw new Error(`CAR-1 fixed baseline missing for ${baselineProfileId}`);
  if(attribution?.legacyReplayParity?.passed!==true)throw new Error(`CAR-1 legacy replay parity missing for ${baselineProfileId}`);
  if(fixed.input?.candidateKeySha256!==attribution.pairedAudit?.candidateKeySha256){
    throw new Error(`CAR-1 candidate identity mismatch for ${baselineProfileId}`);
  }
  if(Number(fixed.input?.candidateEntryCount)!==Number(attribution.pairedAudit?.candidateEntryCount)){
    throw new Error(`CAR-1 candidate cardinality mismatch for ${baselineProfileId}`);
  }
  if(!close(fixed.return?.totalReturnPct,attribution.baseline?.totalReturnPct)||
     !close(fixed.risk?.maxDrawdownPct,attribution.baseline?.maxDrawdownPct)||
     !close(fixed.trade?.profitFactor,attribution.baseline?.profitFactor)||
     Number(fixed.trade?.accepted)!==Number(attribution.baseline?.acceptedTradeCount)){
    throw new Error(`CAR-1 fixed baseline metric parity failed for ${baselineProfileId}`);
  }
  return Object.freeze({
    passed:true,
    candidateKeySha256:fixed.input.candidateKeySha256,
    candidateEntryCount:Number(fixed.input.candidateEntryCount),
    totalReturnDeltaPct:round(Number(attribution.baseline.totalReturnPct)-Number(fixed.return.totalReturnPct)),
    maxDrawdownDeltaPct:round(Number(attribution.baseline.maxDrawdownPct)-Number(fixed.risk.maxDrawdownPct)),
    acceptedTradeDelta:Number(attribution.baseline.acceptedTradeCount)-Number(fixed.trade.accepted),
  });
}

function rowFor({universeVariant,baselineProfileId,sizingProfileId,result,baseline}){
  return Object.freeze({
    universeVariant,
    managementMode:'FIXED_HORIZON',
    baselineProfileId,
    sizingProfileId,
    resultClass:'CAUSAL_COUNTERFACTUAL_POSITION_SIZING',
    winnerEligible:false,
    formalOos:false,
    finalEquityJpy:result.finalEquityJpy,
    totalReturnPct:result.totalReturnPct,
    deltaTotalReturnPct:round(Number(result.totalReturnPct)-Number(baseline.totalReturnPct)),
    profitFactor:result.profitFactor,
    maxDrawdownPct:result.maxDrawdownPct,
    deltaMaxDrawdownPct:round(Number(result.maxDrawdownPct)-Number(baseline.maxDrawdownPct)),
    winRate:result.winRate,
    acceptedTradeCount:result.acceptedTradeCount,
    rejectedTradeCount:result.rejectedTradeCount,
    averageCapitalUtilization:result.averageCapitalUtilization,
    turnover:result.turnover,
    totalTransactionCostsJpy:result.totalTransactionCostsJpy,
    totalAdverseSlippageJpy:result.totalAdverseSlippageJpy,
    observedMaximumConcurrentPositions:result.observedMaximumConcurrentPositions,
    maximumSymbolShare:result.maximumSymbolShare,
    maximumSectorShare:result.maximumSectorShare,
  });
}

export function runCar1CheckpointedSizingAttribution({
  historyPack,
  captureArtifacts=[],
  sessionIntegrityLedger,
  lineageManifest,
  checkpointsBySession={},
  sourceEvaluationArtifact,
  universeVariants=PHASE57_CAR1_CHECKPOINT_POLICY.defaultUniverseVariants,
  baselineProfileIds,
  sizingProfileIds,
  initialEquity=PHASE57_P25_LANE_C_FIXED_RUNNER_POLICY.initialEquityJpy,
}={}){
  assertSafety();
  const selectedUniverseVariants=[...(Array.isArray(universeVariants)?universeVariants:[])];
  if(!selectedUniverseVariants.length||new Set(selectedUniverseVariants).size!==selectedUniverseVariants.length){
    throw new Error('CAR-1 universe variants must be unique and non-empty');
  }
  const baselineProfiles=selectedBaselineProfiles(baselineProfileIds);
  const sizingProfiles=selectedSizingProfiles(sizingProfileIds);

  const fixed=runLaneCFixedCheckpointedPortfolio({
    historyPack,captureArtifacts,sessionIntegrityLedger,lineageManifest,checkpointsBySession,sourceEvaluationArtifact,
    universeVariants:selectedUniverseVariants,profiles:baselineProfiles,initialEquity,
  });
  if(fixed.status!=='LANE_C_FIXED_CHECKPOINTED_PORTFOLIO_MATRIX_READY'||fixed.sourceReconciliation?.exactCheckpointRecomputationMatch!==true){
    throw new Error('CAR-1 requires reconciled Lane C Fixed checkpoint evidence');
  }

  const packetBundle=buildLaneCFixedCheckpointPackets({
    historyPack,captureArtifacts,sessionIntegrityLedger,lineageManifest,checkpointsBySession,
  });
  if(packetBundle.assembled.lineageManifestHeadSha256!==fixed.lineageManifestHeadSha256){
    throw new Error('CAR-1 lineage differs from reconciled Lane C Fixed baseline');
  }

  const attributions={},matrixRows=[],baselineParity={};
  for(const universeVariant of selectedUniverseVariants){
    const sessions=buildP252FixedPortfolioSessions({sessionPackets:packetBundle.packets,universeVariant});
    attributions[universeVariant]={};
    baselineParity[universeVariant]={};
    for(const baselineProfile of baselineProfiles){
      const attribution=runCar1CounterfactualPortfolioAttribution({
        sessions,
        baselineProfile,
        profileIds:sizingProfiles,
        initialEquity,
        managementMode:'FIXED_HORIZON',
        universeVariant,
        roundTripCostPct:PHASE57_CAR1_CHECKPOINT_POLICY.roundTripCostPct,
        slippageBps:PHASE57_CAR1_CHECKPOINT_POLICY.slippageBps,
      });
      const parity=assertBaselineParity({
        fixedComparison:fixed.comparisons[universeVariant],baselineProfileId:baselineProfile.id,attribution,
      });
      attributions[universeVariant][baselineProfile.id]=attribution;
      baselineParity[universeVariant][baselineProfile.id]=parity;
      for(const sizingProfileId of sizingProfiles){
        matrixRows.push(rowFor({
          universeVariant,
          baselineProfileId:baselineProfile.id,
          sizingProfileId,
          result:attribution.results[sizingProfileId],
          baseline:attribution.baseline,
        }));
      }
    }
    attributions[universeVariant]=Object.freeze(attributions[universeVariant]);
    baselineParity[universeVariant]=Object.freeze(baselineParity[universeVariant]);
  }

  return Object.freeze({
    phase:'57.car1.checkpointed-sizing-attribution',
    status:'CAR1_CHECKPOINTED_PAIRED_SIZING_ATTRIBUTION_READY',
    managementMode:'FIXED_HORIZON',
    initialEquityJpy:Number(initialEquity),
    lineageManifestHeadSha256:fixed.lineageManifestHeadSha256,
    universeVariantOrder:Object.freeze(selectedUniverseVariants),
    baselineProfileOrder:Object.freeze(baselineProfiles.map(row=>row.id)),
    sizingProfileOrder:Object.freeze(sizingProfiles),
    inputAudit:fixed.inputAudit,
    sourceReconciliation:fixed.sourceReconciliation,
    baselineParity:Object.freeze(baselineParity),
    attributions:Object.freeze(attributions),
    matrixRows:Object.freeze(matrixRows),
    methodology:Object.freeze({
      formalP25CheckpointEvidenceRequired:true,
      laneCFixedReconciliationRequired:true,
      exactLegacyReplayParityRequired:true,
      sameFrozenEntry:true,
      sameEntryPrice:true,
      sameDirection:true,
      sameFrozenExit:true,
      sameCostAssumption:true,
      sameCandidatePriority:true,
      baselineBudgetEnvelopeAnchored:true,
      challengerSelfCompoundingSizing:false,
      rankingChanged:false,
      selectorChanged:false,
      entryChanged:false,
      exitChanged:false,
      parameterSearchAllowed:false,
      winnerSelectionAllowed:false,
      promotionEligible:false,
      formalOos:false,
      prospectiveSampleSufficient:false,
      futureOutcomeUsedBySizer:false,
      incompleteProspectiveBackfillAllowed:false,
    }),
    safety:Object.freeze({
      checkpoint:PHASE57_CAR1_CHECKPOINT_SAFETY,
      sizing:PHASE57_CAR1_SAFETY,
      laneCFixed:PHASE57_P25_LANE_C_FIXED_RUNNER_SAFETY,
    }),
  });
}

export default {
  runCar1CheckpointedSizingAttribution,
  PHASE57_CAR1_CHECKPOINT_POLICY,
  PHASE57_CAR1_CHECKPOINT_SAFETY,
};
