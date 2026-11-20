import crypto from 'node:crypto';

export const REQUIRED_PHASE57_LONG_ONLY_ACQUISITION_GATES=Object.freeze([
  'officialEndpointContractRecorded',
  'historicalCodeAuditCompleted',
  'artifactInventoryCompleted',
  'l0DataContractFrozen',
  'l1L2DataContractFrozen',
  'datasetSplitFrozen',
  'historicalSessionIdentifiersFrozen',
  'dataBudgetCalculated',
  'paginationBudgetCalculated',
  'storageManifestContractFrozen',
  'integratedDataReuseContractFrozen',
  'humanOverfittingControlsFrozen',
  'independentReviewDispositionFrozen',
  'exactCurrentEntitlementReattested',
  'storageDeletionTermsReattested',
  'privateCacheDestinationConfirmed',
  'postCancellationPurgeMechanismTested',
  'freshSelectionRuleFrozen',
  'credentialAvailabilityConfirmed',
  'claudeIndependentReviewReceived',
  'claudeCriticalBlockersResolved',
  'operatorExplicitAcquisitionApproval',
]);

const stable=value=>{
  if(Array.isArray(value))return value.map(stable);
  if(value&&typeof value==='object')return Object.fromEntries(Object.keys(value).sort().map(key=>[key,stable(value[key])]));
  return value;
};

export function evaluateLongOnlyAcquisitionGate(plan){
  if(!plan||typeof plan!=='object')throw new TypeError('data plan is required');
  if(plan.newJquantsAcquisitionAuthorized!==false)throw new Error('committed plan must keep acquisition authorization false');
  const gates=plan.preAcquisitionGate??{};
  const missing=REQUIRED_PHASE57_LONG_ONLY_ACQUISITION_GATES.filter(key=>gates[key]!==true);
  return Object.freeze({
    status:missing.length?'BLOCKED':'READY_FOR_SEPARATE_OPERATOR_AUTHORIZATION',
    acquisitionMayStart:false,
    missing:Object.freeze(missing),
    planSha256:crypto.createHash('sha256').update(JSON.stringify(stable(plan))).digest('hex'),
    rationale:missing.length
      ?'Every gate must be evidenced before a separate, non-committed operator authorization can start acquisition.'
      :'The committed plan still cannot start acquisition; explicit runtime authorization must be supplied outside Git.',
  });
}

export function assertRuntimeAcquisitionAuthorization({plan,authorization,partition}){
  const committed=evaluateLongOnlyAcquisitionGate(plan);
  if(authorization?.planSha256!==committed.planSha256)throw new Error('runtime authorization does not match committed data plan');
  const effective={...(plan.preAcquisitionGate??{}),...(authorization?.gateEvidence??{})};
  const missing=REQUIRED_PHASE57_LONG_ONLY_ACQUISITION_GATES.filter(key=>effective[key]!==true);
  if(missing.length)throw new Error(`runtime acquisition authorization is incomplete: ${missing.join(', ')}`);
  if(authorization?.operatorApproved!==true)throw new Error('separate operator approval is required');
  if(!authorization?.acquisitionPartitions?.includes(partition))throw new Error(`${partition} is not authorized for sealed cache acquisition`);
  if(!authorization?.authorizationSha256?.match(/^[a-f0-9]{64}$/))throw new Error('runtime authorization requires an external evidence SHA-256');
  if(!String(authorization?.privateCacheRoot??''))throw new Error('private cache root is required');
  return Object.freeze({authorized:true,partition,analysisPartitionOpened:false,planSha256:committed.planSha256,privateCacheRoot:String(authorization.privateCacheRoot)});
}

export function buildAcquisitionGateSummary({plan,allocation,credentialPresent=false,privateCacheRootConfirmed=false,purgeDryRunPassed=false}={}){
  const gate=evaluateLongOnlyAcquisitionGate(plan);
  const partitions=allocation?.partitions??{},sessions=Object.values(partitions).flat();
  if(sessions.length!==205||new Set(sessions).size!==205)throw new Error('frozen clean-205 allocation is required');
  return Object.freeze({
    status:gate.status,
    acquisitionMayStart:false,
    planSha256:gate.planSha256,
    allocationId:String(allocation?.allocationId??''),
    sessions:205,
    requests:Object.freeze({daily:206,datedMaster:205,minute:0,totalBase:411}),
    causalWarmup:Object.freeze({sessionDate:String(plan?.l0Contract?.causalWarmup?.sessionDate??''),evaluationPartition:false}),
    destination:Object.freeze({publicRepositoryProhibited:true,privateCacheRootConfirmed:Boolean(privateCacheRootConfirmed)}),
    storageLifecycle:Object.freeze({termsRecorded:plan?.preAcquisitionGate?.storageDeletionTermsReattested===true,purgeDryRunPassed:Boolean(purgeDryRunPassed)}),
    credential:Object.freeze({present:Boolean(credentialPresent),valueObserved:false}),
    missingCommittedGates:gate.missing,
    operatorApprovalStillRequired:true,
  });
}

export function assertReleasedPartition({partition,plan}){
  const allowed=new Set([
    'DEVELOPMENT_A','DEVELOPMENT_B','DEVELOPMENT_C','DEVELOPMENT_D',
    'VALIDATION','VALIDATION_REPLICATION','PRIMARY_OOS','CONTINGENCY_OOS','FRESH_PROSPECTIVE',
  ]);
  if(!allowed.has(partition))throw new Error('unknown or non-mountable partition');
  const release=plan?.runtimeReleaseEvidence?.[partition];
  if(release?.released!==true||!release?.releaseSha256?.match(/^[a-f0-9]{64}$/))throw new Error(`${partition} is sealed`);
  if(partition==='CONTINGENCY_OOS'&&release?.reason!=='PRIMARY_EVALUATION_INVALIDATED_NON_PERFORMANCE')throw new Error('CONTINGENCY_OOS release reason is not permitted');
  return true;
}

export function assertReserveReplacement({plan,reserveSessionId,replacementFor,trigger,evidenceSha256}){
  const reserve=plan?.datasetSplit?.reserve;
  if(!reserve||reserve.opened!==false)throw new Error('reserve contract missing or invalid');
  if(!reserveSessionId||!replacementFor)throw new Error('reserve session and replacement target are required');
  if(!reserve.triggers?.includes(trigger))throw new Error('reserve deployment trigger is not precommitted');
  if(!evidenceSha256?.match(/^[a-f0-9]{64}$/))throw new Error('reserve deployment requires hashed admission-failure evidence');
  return true;
}

export default {
  REQUIRED_PHASE57_LONG_ONLY_ACQUISITION_GATES,
  evaluateLongOnlyAcquisitionGate,
  assertRuntimeAcquisitionAuthorization,
  buildAcquisitionGateSummary,
  assertReleasedPartition,
  assertReserveReplacement,
};
