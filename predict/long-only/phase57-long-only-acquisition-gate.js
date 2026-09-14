import crypto from 'node:crypto';

export const REQUIRED_PHASE57_LONG_ONLY_ACQUISITION_GATES=Object.freeze([
  'officialEndpointContractRecorded',
  'historicalCodeAuditCompleted',
  'artifactInventoryCompleted',
  'l0DataContractFrozen',
  'l1L2DataContractFrozen',
  'datasetSplitFrozen',
  'dataBudgetCalculated',
  'paginationBudgetCalculated',
  'storageManifestContractFrozen',
  'exactCurrentEntitlementReattested',
  'storageDeletionTermsReattested',
  'freshExactDatesFrozen',
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

export function assertReleasedPartition({partition,plan}){
  const allowed=new Set(['DEVELOPMENT_A','DEVELOPMENT_B','DEVELOPMENT_C','DEVELOPMENT_D','VALIDATION','VALIDATION_CONFIRMATION','UNTOUCHED_OOS','FINAL_CONFIRMATION','FRESH_PROSPECTIVE']);
  if(!allowed.has(partition))throw new Error('unknown partition');
  const release=plan?.runtimeReleaseEvidence?.[partition];
  if(release?.released!==true||!release?.releaseSha256?.match(/^[a-f0-9]{64}$/))throw new Error(`${partition} is sealed`);
  return true;
}

export default {REQUIRED_PHASE57_LONG_ONLY_ACQUISITION_GATES,evaluateLongOnlyAcquisitionGate,assertReleasedPartition};
