export const L2_CANDIDATE_CONTRACT=Object.freeze({
  contractId:'PHASE57_LONG_ONLY_L2_SMALL_CANDIDATE_SET_V1',
  targetCandidates:Object.freeze(['CONTINUATION_PROBABILITY','EXPECTED_CONTINUATION_RETURN','RISK_ADJUSTED_REMAINING_OPPORTUNITY']),
  modelFamilies:Object.freeze(['REGULARIZED_LINEAR_OR_LOGISTIC','SHALLOW_MONOTONIC_TREE']),
  maximumTargets:3,
  maximumModelFamilies:2,
  selectionPartitions:Object.freeze(['DEVELOPMENT_C','DEVELOPMENT_D']),
  validationMaySelectTarget:false,
  validationMaySelectFeature:false,
  fullCrossSectionRequiredForFinalFit:true,
  riskPenaltyLambda:0.5,
});

export function buildEvaluatorOnlyL2Targets(label,{continuationThresholdPct=1,lambda=L2_CANDIDATE_CONTRACT.riskPenaltyLambda}={}){
  if(label?.evaluatorOnly!==true)throw new Error('L2 targets require evaluator-only labels');
  const remaining=Number(label.remainingUpsidePct),mae=Math.abs(Number(label.futureMaePct)),continuation=Number(label.continuationToClosePct);
  if(![remaining,mae,continuation].every(Number.isFinite))throw new Error('complete L2 evaluator targets are required');
  return Object.freeze({evaluatorOnly:true,continuationProbabilityLabel:continuation>=continuationThresholdPct?1:0,expectedContinuationReturnPct:continuation,riskAdjustedRemainingOpportunityPct:remaining-Number(lambda)*mae});
}

export function assertL2SelectionBoundary({partition,targetCount,modelFamilyCount}={}){
  if(!L2_CANDIDATE_CONTRACT.selectionPartitions.includes(partition))throw new Error('target/model selection is Development C/D only');
  if(!Number.isInteger(targetCount)||targetCount<1||targetCount>L2_CANDIDATE_CONTRACT.maximumTargets)throw new Error('target zoo is prohibited');
  if(!Number.isInteger(modelFamilyCount)||modelFamilyCount<1||modelFamilyCount>L2_CANDIDATE_CONTRACT.maximumModelFamilies)throw new Error('model zoo is prohibited');
  return true;
}

export default {L2_CANDIDATE_CONTRACT,buildEvaluatorOnlyL2Targets,assertL2SelectionBoundary};
