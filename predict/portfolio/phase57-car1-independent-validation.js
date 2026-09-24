import {createHash} from 'node:crypto';
import {
  PHASE57_CAR1_CHECKPOINT_POLICY,
  PHASE57_CAR1_CHECKPOINT_SAFETY,
} from './phase57-car1-checkpoint-runner.js';
import {
  PHASE57_CAR1_POLICY,
  PHASE57_CAR1_PROFILES,
  PHASE57_CAR1_SAFETY,
} from './phase57-car1-sizing-research.js';
import {
  PHASE57_P25_LANE_C_POLICY,
} from './phase57-p25-lane-c-portfolio-simulator.js';

export const PHASE57_CAR1_VALIDATION_SAFETY=Object.freeze({
  phase:'57.car1.independent-validation',
  mode:'READ_ONLY_PRECOMMITTED_VALIDATION_GATE',
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

/**
 * Frozen before any post-2026-09-05 validation outcome is observed.
 * Dates are not hand-picked. The formal Lane C expected-session lineage supplies
 * the schedule and the first N dates strictly after the freeze date are used.
 * A missing/incomplete member invalidates the tranche; a later session may not
 * replace it and no retrospective backfill is allowed.
 */
export const PHASE57_CAR1_VALIDATION_PLAN=Object.freeze({
  protocolId:'CAR1_FIRST_5_POST_FREEZE_EXPECTED_SESSIONS_V1',
  protocolFreezeDate:'2026-09-05',
  eligibleSessionDateStrictlyAfter:'2026-09-05',
  requiredSessionCount:5,
  sessionSelectionRule:'FIRST_N_FORMAL_EXPECTED_SESSION_DATES_STRICTLY_AFTER_FREEZE_DATE',
  incompleteSessionPolicy:'FAIL_CLOSED_NO_REPLACEMENT_NO_BACKFILL',
  developmentEvidenceReuseAllowed:false,
  parameterSearchAllowed:false,
  winnerSelectionAllowed:false,
  automaticPromotionAllowed:false,
  productionUpdateAllowed:false,
  performanceExtractionRequiresWindowedReplay:true,
  promotionEligible:false,
});

const FALSE_KEYS=Object.freeze([
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted',
]);
const SHA256_RE=/^[0-9a-f]{64}$/;

function canonicalize(value){
  if(Array.isArray(value))return value.map(canonicalize);
  if(value&&typeof value==='object')return Object.fromEntries(Object.keys(value).sort().map(key=>[key,canonicalize(value[key])]));
  return value;
}
function sha256(value){
  return createHash('sha256').update(JSON.stringify(canonicalize(value))).digest('hex');
}
function normalizeDate(value){
  const date=String(value??'').trim();
  if(!/^\d{4}-\d{2}-\d{2}$/.test(date)||!Number.isFinite(Date.parse(`${date}T00:00:00Z`)))throw new Error(`invalid CAR-1 session date: ${value??'MISSING'}`);
  return date;
}
function uniqueSortedDates(values,label){
  const dates=(Array.isArray(values)?values:[]).map(normalizeDate).sort();
  if(new Set(dates).size!==dates.length)throw new Error(`duplicate CAR-1 ${label} session date`);
  return dates;
}
function assertFalseSafety(safety,label){
  for(const key of FALSE_KEYS)if(safety?.[key]!==false)throw new Error(`CAR-1 ${label} safety ${key} must remain false`);
}
function assertResearchLocks(result,label){
  if(result?.status!=='CAR1_CHECKPOINTED_PAIRED_SIZING_ATTRIBUTION_READY')throw new Error(`CAR-1 ${label} result is not checkpoint-ready`);
  if(result?.managementMode!=='FIXED_HORIZON')throw new Error(`CAR-1 ${label} must keep Fixed-Horizon EXIT`);
  const method=result?.methodology??{};
  for(const key of ['sameFrozenEntry','sameEntryPrice','sameDirection','sameFrozenExit','sameCostAssumption','sameCandidatePriority','baselineBudgetEnvelopeAnchored']){
    if(method[key]!==true)throw new Error(`CAR-1 ${label} methodology lock failed: ${key}`);
  }
  for(const key of ['rankingChanged','selectorChanged','entryChanged','exitChanged','parameterSearchAllowed','winnerSelectionAllowed','promotionEligible','futureOutcomeUsedBySizer','incompleteProspectiveBackfillAllowed']){
    if(method[key]!==false)throw new Error(`CAR-1 ${label} forbidden methodology changed: ${key}`);
  }
  assertFalseSafety(result?.safety?.checkpoint,`${label} checkpoint`);
  assertFalseSafety(result?.safety?.sizing,`${label} sizing`);
  assertFalseSafety(result?.safety?.laneCFixed,`${label} Lane C Fixed`);
}

function configurationSnapshot(result){
  return Object.freeze({
    managementMode:result.managementMode,
    universeVariantOrder:Object.freeze([...(result.universeVariantOrder??[])]),
    baselineProfileOrder:Object.freeze([...(result.baselineProfileOrder??[])]),
    sizingProfileOrder:Object.freeze([...(result.sizingProfileOrder??[])]),
    initialEquityJpy:Number(result.initialEquityJpy),
    roundTripCostPct:PHASE57_CAR1_CHECKPOINT_POLICY.roundTripCostPct,
    slippageBps:PHASE57_CAR1_CHECKPOINT_POLICY.slippageBps,
    lotSize:PHASE57_P25_LANE_C_POLICY.lotSize,
    priorityRule:PHASE57_CAR1_POLICY.priorityRule,
    atrLookbackBars:PHASE57_CAR1_POLICY.atrLookbackBars,
    realizedVolLookbackBars:PHASE57_CAR1_POLICY.realizedVolLookbackBars,
    profileDefinitions:Object.freeze(PHASE57_CAR1_PROFILES.map(row=>Object.freeze({id:row.id,riskMetric:row.riskMetric}))),
  });
}
function candidateIdentity(result){
  const rows=[];
  for(const variant of result.universeVariantOrder??[]){
    for(const baseline of result.baselineProfileOrder??[]){
      const parity=result.baselineParity?.[variant]?.[baseline];
      const hash=String(parity?.candidateKeySha256??'').toLowerCase();
      if(parity?.passed!==true||!SHA256_RE.test(hash))throw new Error(`CAR-1 candidate identity missing for ${variant}/${baseline}`);
      rows.push(Object.freeze({
        universeVariant:variant,
        baselineProfileId:baseline,
        candidateKeySha256:hash,
        candidateEntryCount:Number(parity.candidateEntryCount),
      }));
    }
  }
  if(!rows.length)throw new Error('CAR-1 candidate identity matrix is empty');
  return Object.freeze(rows);
}
function auditDates(result){
  const expected=uniqueSortedDates(result?.inputAudit?.expectedSessionDates,'expected');
  const ready=uniqueSortedDates((result?.inputAudit?.packetSummaries??[]).map(row=>row?.sessionDate),'ready');
  if(Number(result?.inputAudit?.readySessionCount)!==ready.length)throw new Error('CAR-1 ready-session audit count mismatch');
  if(Number(result?.inputAudit?.expectedSessionCount)!==expected.length)throw new Error('CAR-1 expected-session audit count mismatch');
  const expectedSet=new Set(expected);
  if(ready.some(date=>!expectedSet.has(date)))throw new Error('CAR-1 ready session is absent from formal expected-session lineage');
  return Object.freeze({expected:Object.freeze(expected),ready:Object.freeze(ready)});
}

export function buildCar1DevelopmentEvidenceLock({result}={}){
  assertFalseSafety(PHASE57_CAR1_VALIDATION_SAFETY,'validation contract');
  assertFalseSafety(PHASE57_CAR1_CHECKPOINT_SAFETY,'checkpoint policy');
  assertFalseSafety(PHASE57_CAR1_SAFETY,'sizing policy');
  assertResearchLocks(result,'development');
  const dates=auditDates(result);
  const configuration=configurationSnapshot(result);
  const identities=candidateIdentity(result);
  const lineage=String(result.lineageManifestHeadSha256??'').toLowerCase();
  const sourceEvaluation=String(result?.sourceReconciliation?.sourceEvaluationCanonicalSha256??'').toLowerCase();
  if(!SHA256_RE.test(lineage)||!SHA256_RE.test(sourceEvaluation))throw new Error('CAR-1 development lineage/source identity must be SHA-256');
  const evidenceIdentity=Object.freeze({
    lineageManifestHeadSha256:lineage,
    sourceEvaluationCanonicalSha256:sourceEvaluation,
    expectedSessionDates:dates.expected,
    readySessionDates:dates.ready,
    packetSummariesSha256:sha256(result.inputAudit.packetSummaries??[]),
    candidateIdentity:identities,
    frozenTradeCount:Number(result.inputAudit.frozenTradeCount),
    resolvedTradeCount:Number(result.inputAudit.resolvedTradeCount),
    unresolvedTradeCount:Number(result.inputAudit.unresolvedTradeCount),
  });
  return Object.freeze({
    phase:'57.car1.independent-validation-lock',
    status:'CAR1_DEVELOPMENT_EVIDENCE_LOCKED_BEFORE_VALIDATION',
    validationPlan:PHASE57_CAR1_VALIDATION_PLAN,
    configuration,
    configurationSha256:sha256(configuration),
    developmentEvidence:evidenceIdentity,
    developmentEvidenceSha256:sha256(evidenceIdentity),
    lockedBeforeValidationOutcomes:true,
    winnerSelectionAllowed:false,
    promotionEligible:false,
    safety:PHASE57_CAR1_VALIDATION_SAFETY,
  });
}

export function selectCar1IndependentValidationWindow({expectedSessionDates,readySessionDates,developmentLock}={}){
  if(developmentLock?.status!=='CAR1_DEVELOPMENT_EVIDENCE_LOCKED_BEFORE_VALIDATION'||developmentLock?.lockedBeforeValidationOutcomes!==true){
    throw new Error('CAR-1 independent validation requires a precommitted development evidence lock');
  }
  const plan=developmentLock.validationPlan;
  if(plan?.protocolId!==PHASE57_CAR1_VALIDATION_PLAN.protocolId||plan?.incompleteSessionPolicy!=='FAIL_CLOSED_NO_REPLACEMENT_NO_BACKFILL'){
    throw new Error('CAR-1 validation plan drift detected');
  }
  const expected=uniqueSortedDates(expectedSessionDates,'validation expected');
  const ready=uniqueSortedDates(readySessionDates,'validation ready');
  const cutoff=normalizeDate(plan.eligibleSessionDateStrictlyAfter);
  const eligible=expected.filter(date=>date>cutoff);
  const required=Number(plan.requiredSessionCount);
  if(eligible.length<required)throw new Error(`CAR-1 validation requires first ${required} formal expected sessions after ${cutoff}; only ${eligible.length} observed`);
  const selected=eligible.slice(0,required);
  const developmentDates=new Set(developmentLock.developmentEvidence.expectedSessionDates??[]);
  if(selected.some(date=>developmentDates.has(date)))throw new Error('CAR-1 validation session overlaps development evidence');
  const readySet=new Set(ready);
  const missing=selected.filter(date=>!readySet.has(date));
  if(missing.length)throw new Error(`CAR-1 precommitted validation window incomplete; no replacement/backfill allowed: ${missing.join(',')}`);
  return Object.freeze({
    status:'CAR1_PRECOMMITTED_VALIDATION_WINDOW_COMPLETE',
    protocolId:plan.protocolId,
    selectedSessionDates:Object.freeze(selected),
    requiredSessionCount:required,
    replacementAllowed:false,
    backfillAllowed:false,
  });
}

/**
 * Gate only. It intentionally does not expose challenger performance from the
 * cumulative artifact. A later windowed replay must run solely on the selected
 * validation dates before any validation metric is inspected.
 */
export function gateCar1IndependentValidationCandidate({developmentLock,candidateResult}={}){
  assertFalseSafety(PHASE57_CAR1_VALIDATION_SAFETY,'validation contract');
  assertResearchLocks(candidateResult,'validation candidate');
  const candidateDates=auditDates(candidateResult);
  const candidateConfiguration=configurationSnapshot(candidateResult);
  const candidateConfigurationSha256=sha256(candidateConfiguration);
  if(candidateConfigurationSha256!==developmentLock?.configurationSha256)throw new Error('CAR-1 validation configuration drift detected');
  const candidateLineage=String(candidateResult.lineageManifestHeadSha256??'').toLowerCase();
  if(!SHA256_RE.test(candidateLineage))throw new Error('CAR-1 validation lineage must be SHA-256');
  if(candidateLineage===developmentLock?.developmentEvidence?.lineageManifestHeadSha256)throw new Error('CAR-1 development evidence cannot be reused as independent validation');
  const window=selectCar1IndependentValidationWindow({
    expectedSessionDates:candidateDates.expected,
    readySessionDates:candidateDates.ready,
    developmentLock,
  });
  return Object.freeze({
    phase:'57.car1.independent-validation-gate',
    status:'CAR1_INDEPENDENT_VALIDATION_WINDOW_READY_FOR_WINDOWED_REPLAY',
    protocolId:window.protocolId,
    selectedSessionDates:window.selectedSessionDates,
    candidateLineageManifestHeadSha256:candidateLineage,
    configurationSha256:candidateConfigurationSha256,
    sameFrozenConfiguration:true,
    developmentEvidenceReused:false,
    incompleteSessionReplacementAllowed:false,
    retrospectiveBackfillAllowed:false,
    parameterSearchAllowed:false,
    winnerSelectionAllowed:false,
    performanceExtractionAllowed:false,
    performanceExtractionReason:'REQUIRES_SELECTED_SESSION_ONLY_WINDOWED_REPLAY',
    promotionEligible:false,
    safety:PHASE57_CAR1_VALIDATION_SAFETY,
  });
}

export const Car1IndependentValidationInternals=Object.freeze({canonicalize,sha256,configurationSnapshot,candidateIdentity,auditDates});

export default {
  PHASE57_CAR1_VALIDATION_SAFETY,
  PHASE57_CAR1_VALIDATION_PLAN,
  buildCar1DevelopmentEvidenceLock,
  selectCar1IndependentValidationWindow,
  gateCar1IndependentValidationCandidate,
};
