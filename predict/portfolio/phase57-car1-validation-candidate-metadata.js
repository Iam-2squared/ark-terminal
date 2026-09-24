import {
  PHASE57_P25_LANE_C_ALLOCATION_PROFILES,
} from './phase57-p25-lane-c-portfolio-simulator.js';
import {
  PHASE57_P25_LANE_C_FIXED_RUNNER_SAFETY,
  runLaneCFixedCheckpointedPortfolio,
} from './phase57-p25-lane-c-fixed-checkpoint-runner.js';
import {
  PHASE57_CAR1_CHECKPOINT_POLICY,
  PHASE57_CAR1_CHECKPOINT_SAFETY,
} from './phase57-car1-checkpoint-runner.js';
import {
  PHASE57_CAR1_PROFILES,
  PHASE57_CAR1_SAFETY,
} from './phase57-car1-sizing-research.js';
import {
  Car1IndependentValidationInternals,
  PHASE57_CAR1_VALIDATION_PLAN,
  PHASE57_CAR1_VALIDATION_SAFETY,
  selectCar1IndependentValidationWindow,
} from './phase57-car1-independent-validation.js';

export const PHASE57_CAR1_VALIDATION_CANDIDATE_SAFETY=Object.freeze({
  phase:'57.car1.validation-candidate-metadata',
  mode:'READ_ONLY_METADATA_ONLY_VALIDATION_CANDIDATE',
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
  freshHoldoutConsumed:false,
});

const FALSE_KEYS=Object.freeze([
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted',
]);
const SHA256_RE=/^[0-9a-f]{64}$/;

function assertFalseSafety(safety,label){
  for(const key of FALSE_KEYS)if(safety?.[key]!==false)throw new Error(`CAR-1 ${label} safety ${key} must remain false`);
}

function assertMetadataOnly(metadata){
  for(const key of ['matrixRows','attributions','results','challengerResults','closedTrades','equityCurve']){
    if(Object.prototype.hasOwnProperty.call(metadata??{},key))throw new Error(`CAR-1 validation candidate must not materialize challenger performance: ${key}`);
  }
  if(metadata?.methodology?.challengerReplayExecuted!==false||metadata?.methodology?.challengerPerformanceMaterialized!==false){
    throw new Error('CAR-1 validation candidate must remain metadata-only');
  }
  if(metadata?.methodology?.performanceExtractionAllowed!==false)throw new Error('CAR-1 cumulative candidate performance extraction must remain disabled');
}

function candidateIdentityFromFixed(fixed){
  const rows=[];
  const baselines=PHASE57_CAR1_CHECKPOINT_POLICY.baselineProfiles;
  for(const universeVariant of fixed.universeVariantOrder??[]){
    const comparison=fixed.comparisons?.[universeVariant];
    const hash=String(comparison?.pairedAudit?.candidateKeySha256??'').toLowerCase();
    const count=Number(comparison?.pairedAudit?.candidateEntryCount);
    if(!SHA256_RE.test(hash)||!Number.isInteger(count)||count<0)throw new Error(`CAR-1 candidate identity missing for ${universeVariant}`);
    for(const baselineProfileId of baselines){
      rows.push(Object.freeze({universeVariant,baselineProfileId,candidateKeySha256:hash,candidateEntryCount:count}));
    }
  }
  if(!rows.length)throw new Error('CAR-1 validation candidate identity matrix is empty');
  return Object.freeze(rows);
}

export function buildCar1ValidationCandidateMetadataFromFixed({fixed}={}){
  assertFalseSafety(PHASE57_CAR1_VALIDATION_CANDIDATE_SAFETY,'validation candidate');
  assertFalseSafety(PHASE57_CAR1_CHECKPOINT_SAFETY,'checkpoint');
  assertFalseSafety(PHASE57_CAR1_SAFETY,'sizing');
  assertFalseSafety(PHASE57_P25_LANE_C_FIXED_RUNNER_SAFETY,'Lane C Fixed');
  if(fixed?.status!=='LANE_C_FIXED_CHECKPOINTED_PORTFOLIO_MATRIX_READY')throw new Error('CAR-1 validation candidate requires reconciled Lane C Fixed evidence');
  if(fixed?.managementMode!=='FIXED_HORIZON'||fixed?.sourceReconciliation?.exactCheckpointRecomputationMatch!==true){
    throw new Error('CAR-1 validation candidate requires exact Fixed-Horizon checkpoint reconciliation');
  }
  const universeVariantOrder=Object.freeze([...(fixed.universeVariantOrder??[])]);
  if(JSON.stringify(universeVariantOrder)!==JSON.stringify(PHASE57_CAR1_CHECKPOINT_POLICY.defaultUniverseVariants)){
    throw new Error('CAR-1 validation candidate universe configuration drift detected');
  }
  const baselineProfileOrder=Object.freeze([...PHASE57_CAR1_CHECKPOINT_POLICY.baselineProfiles]);
  const sizingProfileOrder=Object.freeze(PHASE57_CAR1_PROFILES.map(row=>row.id));
  const lineage=String(fixed.lineageManifestHeadSha256??'').toLowerCase();
  const sourceEvaluation=String(fixed?.sourceReconciliation?.sourceEvaluationCanonicalSha256??'').toLowerCase();
  if(!SHA256_RE.test(lineage)||!SHA256_RE.test(sourceEvaluation))throw new Error('CAR-1 validation candidate lineage/source identity must be SHA-256');
  const metadata=Object.freeze({
    phase:'57.car1.validation-candidate-metadata',
    status:'CAR1_VALIDATION_CANDIDATE_METADATA_READY',
    managementMode:'FIXED_HORIZON',
    initialEquityJpy:Number(fixed.initialEquityJpy),
    lineageManifestHeadSha256:lineage,
    universeVariantOrder,
    baselineProfileOrder,
    sizingProfileOrder,
    inputAudit:fixed.inputAudit,
    sourceReconciliation:Object.freeze({
      formalP25EvaluationRequired:true,
      exactCheckpointRecomputationMatch:true,
      sourceEvaluationCanonicalSha256:sourceEvaluation,
      recomputedEvaluationCanonicalSha256:String(fixed?.sourceReconciliation?.recomputedEvaluationCanonicalSha256??'').toLowerCase(),
      packetSummariesMatch:fixed?.sourceReconciliation?.packetSummariesMatch===true,
    }),
    candidateIdentity:candidateIdentityFromFixed(fixed),
    methodology:Object.freeze({
      formalP25CheckpointEvidenceRequired:true,
      laneCFixedReconciliationRequired:true,
      sameFrozenEntry:true,
      sameEntryPrice:true,
      sameDirection:true,
      sameFrozenExit:true,
      sameCostAssumption:true,
      sameCandidatePriority:true,
      baselineBudgetEnvelopeAnchored:true,
      rankingChanged:false,
      selectorChanged:false,
      entryChanged:false,
      exitChanged:false,
      parameterSearchAllowed:false,
      winnerSelectionAllowed:false,
      promotionEligible:false,
      futureOutcomeUsedBySizer:false,
      incompleteProspectiveBackfillAllowed:false,
      challengerReplayExecuted:false,
      challengerPerformanceMaterialized:false,
      performanceExtractionAllowed:false,
      cumulativeCandidateMetadataOnly:true,
    }),
    safety:Object.freeze({
      candidate:PHASE57_CAR1_VALIDATION_CANDIDATE_SAFETY,
      checkpoint:PHASE57_CAR1_CHECKPOINT_SAFETY,
      sizing:PHASE57_CAR1_SAFETY,
      laneCFixed:PHASE57_P25_LANE_C_FIXED_RUNNER_SAFETY,
    }),
  });
  assertMetadataOnly(metadata);
  return metadata;
}

export function runCar1ValidationCandidateMetadata({
  historyPack,
  captureArtifacts=[],
  sessionIntegrityLedger,
  lineageManifest,
  checkpointsBySession={},
  sourceEvaluationArtifact,
  initialEquity,
}={}){
  const fixed=runLaneCFixedCheckpointedPortfolio({
    historyPack,captureArtifacts,sessionIntegrityLedger,lineageManifest,checkpointsBySession,sourceEvaluationArtifact,
    universeVariants:PHASE57_CAR1_CHECKPOINT_POLICY.defaultUniverseVariants,
    profiles:PHASE57_P25_LANE_C_ALLOCATION_PROFILES,
    ...(initialEquity===undefined?{}:{initialEquity}),
  });
  return buildCar1ValidationCandidateMetadataFromFixed({fixed});
}

export function gateCar1IndependentValidationMetadataCandidate({developmentLock,candidateMetadata}={}){
  assertFalseSafety(PHASE57_CAR1_VALIDATION_SAFETY,'validation contract');
  assertFalseSafety(PHASE57_CAR1_VALIDATION_CANDIDATE_SAFETY,'validation candidate');
  if(candidateMetadata?.status!=='CAR1_VALIDATION_CANDIDATE_METADATA_READY')throw new Error('CAR-1 metadata candidate is not ready');
  assertMetadataOnly(candidateMetadata);
  const methodology=candidateMetadata.methodology??{};
  for(const key of ['sameFrozenEntry','sameEntryPrice','sameDirection','sameFrozenExit','sameCostAssumption','sameCandidatePriority','baselineBudgetEnvelopeAnchored']){
    if(methodology[key]!==true)throw new Error(`CAR-1 metadata candidate methodology lock failed: ${key}`);
  }
  for(const key of ['rankingChanged','selectorChanged','entryChanged','exitChanged','parameterSearchAllowed','winnerSelectionAllowed','promotionEligible','futureOutcomeUsedBySizer','incompleteProspectiveBackfillAllowed']){
    if(methodology[key]!==false)throw new Error(`CAR-1 metadata candidate forbidden methodology changed: ${key}`);
  }
  for(const safety of Object.values(candidateMetadata.safety??{}))assertFalseSafety(safety,'metadata candidate nested');
  const candidateConfiguration=Car1IndependentValidationInternals.configurationSnapshot(candidateMetadata);
  const configurationSha256=Car1IndependentValidationInternals.sha256(candidateConfiguration);
  if(configurationSha256!==developmentLock?.configurationSha256)throw new Error('CAR-1 validation configuration drift detected');
  const lineage=String(candidateMetadata.lineageManifestHeadSha256??'').toLowerCase();
  if(!SHA256_RE.test(lineage))throw new Error('CAR-1 validation lineage must be SHA-256');
  if(lineage===developmentLock?.developmentEvidence?.lineageManifestHeadSha256)throw new Error('CAR-1 development evidence cannot be reused as independent validation');
  const dates=Car1IndependentValidationInternals.auditDates(candidateMetadata);
  const window=selectCar1IndependentValidationWindow({
    expectedSessionDates:dates.expected,
    readySessionDates:dates.ready,
    developmentLock,
  });
  return Object.freeze({
    phase:'57.car1.independent-validation-gate',
    status:'CAR1_INDEPENDENT_VALIDATION_WINDOW_READY_FOR_WINDOWED_REPLAY',
    protocolId:PHASE57_CAR1_VALIDATION_PLAN.protocolId,
    selectedSessionDates:window.selectedSessionDates,
    candidateLineageManifestHeadSha256:lineage,
    configurationSha256,
    sameFrozenConfiguration:true,
    developmentEvidenceReused:false,
    cumulativeChallengerPerformanceMaterialized:false,
    challengerReplayExecuted:false,
    incompleteSessionReplacementAllowed:false,
    retrospectiveBackfillAllowed:false,
    parameterSearchAllowed:false,
    winnerSelectionAllowed:false,
    performanceExtractionAllowed:false,
    performanceExtractionReason:'REQUIRES_SELECTED_SESSION_ONLY_WINDOWED_REPLAY',
    promotionEligible:false,
    safety:PHASE57_CAR1_VALIDATION_CANDIDATE_SAFETY,
  });
}

export default {
  PHASE57_CAR1_VALIDATION_CANDIDATE_SAFETY,
  buildCar1ValidationCandidateMetadataFromFixed,
  runCar1ValidationCandidateMetadata,
  gateCar1IndependentValidationMetadataCandidate,
};
