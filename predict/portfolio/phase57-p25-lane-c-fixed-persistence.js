import {createHash} from 'node:crypto';

export const PHASE57_P25_LANE_C_FIXED_PERSISTENCE_VARIANTS=Object.freeze([
  'FIXED_5','OLD_FIXED_30','DYNAMIC_30','DYNAMIC_40','DYNAMIC_50',
]);

export const PHASE57_P25_LANE_C_FIXED_PERSISTENCE_PROFILES=Object.freeze([
  'CURRENT_EXISTING','MAX_10','MAX_4','MAX_3','MAX_2',
]);

export const PHASE57_P25_LANE_C_FIXED_PERSISTENCE_SAFETY_KEYS=Object.freeze([
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed',
  'transmitted','freshHoldoutConsumed',
]);

const sha256=bytes=>createHash('sha256').update(bytes).digest('hex');
const isSha256=value=>/^[0-9a-f]{64}$/.test(String(value??''));

function canonicalize(value){
  if(Array.isArray(value))return value.map(canonicalize);
  if(value&&typeof value==='object'){
    return Object.fromEntries(Object.keys(value).sort().map(key=>[key,canonicalize(value[key])]));
  }
  return value;
}

function canonicalSha256(value){
  return sha256(JSON.stringify(canonicalize(value)));
}

function assertExactOrder(actual,expected,label){
  if(!Array.isArray(actual)||actual.length!==expected.length||actual.some((value,index)=>value!==expected[index])){
    throw new Error(`Lane C Fixed persistence ${label} must retain its precommitted order`);
  }
}

function assertSafetyFalse(safety,label){
  for(const key of PHASE57_P25_LANE_C_FIXED_PERSISTENCE_SAFETY_KEYS){
    if(safety?.[key]!==false)throw new Error(`Lane C Fixed persistence ${label} safety ${key} must be false`);
  }
}

function assertBoolean(value,expected,label){
  if(value!==expected)throw new Error(`Lane C Fixed persistence ${label} must be ${expected}`);
}

function assertCurve(curve,label){
  if(!Array.isArray(curve)||curve.length<1)throw new Error(`Lane C Fixed persistence ${label} must retain a non-empty curve`);
  for(let index=0;index<curve.length;index+=1){
    const timestamp=String(curve[index]?.timestamp??'');
    if(!Number.isFinite(Date.parse(timestamp)))throw new Error(`Lane C Fixed persistence ${label} timestamp is invalid`);
    if(index>0&&timestamp<String(curve[index-1]?.timestamp??''))throw new Error(`Lane C Fixed persistence ${label} must be chronological`);
  }
}

function curveAudit(result){
  const equity=result.equityCurve;
  const daily=result.dailyEquityCurve;
  const concentration=result.concentrationCurve;
  assertCurve(equity,'5-minute MTM equity curve');
  assertCurve(concentration,'concentration curve');
  if(!Array.isArray(daily)||daily.length<1)throw new Error('Lane C Fixed persistence daily equity curve must be non-empty');
  const first=equity[0],last=equity.at(-1);
  if(Math.abs(Number(last?.portfolioEquityJpy)-Number(result?.return?.finalEquityJpy))>1e-6){
    throw new Error('Lane C Fixed persistence final MTM equity does not match the return summary');
  }
  return Object.freeze({
    equityPointCount:equity.length,
    dailyPointCount:daily.length,
    concentrationPointCount:concentration.length,
    firstTimestamp:String(first.timestamp),
    lastTimestamp:String(last.timestamp),
    finalEquityJpy:Number(last.portfolioEquityJpy),
  });
}

export function validateLaneCFixedPortfolioArtifact(artifact){
  if(artifact?.phase!=='57.p25.lane-c.fixed-checkpoint-portfolio-cli'||artifact?.status!=='LANE_C_FIXED_CHECKPOINTED_PORTFOLIO_ARTIFACT_WRITTEN'){
    throw new Error('Lane C Fixed persistence requires the checkpoint portfolio CLI artifact');
  }
  if(!artifact?.result||artifact.result.status!=='LANE_C_FIXED_CHECKPOINTED_PORTFOLIO_MATRIX_READY'||artifact.result.managementMode!=='FIXED_HORIZON'){
    throw new Error('Lane C Fixed persistence requires a ready Fixed-Horizon matrix');
  }
  if(!isSha256(artifact.resultCanonicalSha256)||canonicalSha256(artifact.result)!==artifact.resultCanonicalSha256){
    throw new Error('Lane C Fixed persistence result canonical SHA does not match');
  }
  assertSafetyFalse(artifact.safety,'artifact');
  assertSafetyFalse(artifact.result.safety,'result');
  assertExactOrder(artifact.result.universeVariantOrder,PHASE57_P25_LANE_C_FIXED_PERSISTENCE_VARIANTS,'universe variants');
  assertExactOrder(artifact.result.profileOrder,PHASE57_P25_LANE_C_FIXED_PERSISTENCE_PROFILES,'allocation profiles');

  assertBoolean(artifact.methodology?.formalP25EvaluationReconciledBeforeSimulation,true,'formal evaluation reconciliation');
  assertBoolean(artifact.methodology?.sameFrozenEntry,true,'same Frozen Entry lock');
  assertBoolean(artifact.methodology?.fixedHorizonExitUnchanged,true,'Fixed-Horizon EXIT lock');
  assertBoolean(artifact.methodology?.currentExistingReferenceOnly,true,'Current reference-only lock');
  assertBoolean(artifact.methodology?.max10AssumedEquivalentToCurrent,false,'Max10 equivalence claim');
  assertBoolean(artifact.methodology?.dynamicManagementArtifactUsed,false,'Dynamic management connection');
  assertBoolean(artifact.methodology?.winnerSelectionAllowed,false,'winner selection');
  assertBoolean(artifact.methodology?.freshHoldoutConsumed,false,'fresh holdout consumption');
  assertBoolean(artifact.result.sourceReconciliation?.exactCheckpointRecomputationMatch,true,'checkpoint recomputation match');
  assertBoolean(artifact.result.sourceReconciliation?.packetSummariesMatch,true,'packet summary match');
  if(artifact.result.sourceReconciliation?.sourceEvaluationCanonicalSha256!==artifact.result.sourceReconciliation?.recomputedEvaluationCanonicalSha256){
    throw new Error('Lane C Fixed persistence source and recomputed evaluation SHA must match');
  }
  assertBoolean(artifact.result.methodology?.dynamicHoldExitConnected,false,'Dynamic HOLD/EXIT connection');
  assertBoolean(artifact.result.methodology?.winnerSelectionAllowed,false,'result winner selection');
  assertBoolean(artifact.result.methodology?.prospectiveSampleSufficient,false,'prospective sufficiency claim');
  assertBoolean(artifact.result.methodology?.availableCashConstrainsPurchase,true,'available-cash constraint');
  assertBoolean(artifact.result.methodology?.unrealizedPnlInEquityButNotCash,true,'equity and cash separation');
  assertBoolean(artifact.result.methodology?.futureExitOrReturnVisibleToAllocator,false,'future outcome visibility');

  const dates=artifact.result.inputAudit?.expectedSessionDates;
  if(!Array.isArray(dates)||dates.length<1||dates.some(date=>!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(String(date)))){
    throw new Error('Lane C Fixed persistence expected session dates are invalid');
  }
  if(new Set(dates).size!==dates.length||dates.some((date,index)=>index>0&&date<=dates[index-1])){
    throw new Error('Lane C Fixed persistence expected session dates must be unique and chronological');
  }
  if(Number(artifact.result.inputAudit.expectedSessionCount)!==dates.length){
    throw new Error('Lane C Fixed persistence expected session count mismatch');
  }

  const expectedMatrixKeys=new Set();
  for(const variant of PHASE57_P25_LANE_C_FIXED_PERSISTENCE_VARIANTS){
    for(const profileId of PHASE57_P25_LANE_C_FIXED_PERSISTENCE_PROFILES)expectedMatrixKeys.add(`${variant}:${profileId}`);
  }
  const matrixRows=artifact.result.matrixRows;
  if(!Array.isArray(matrixRows)||matrixRows.length!==expectedMatrixKeys.size)throw new Error('Lane C Fixed persistence matrix is incomplete');
  for(const row of matrixRows){
    const key=`${row?.universeVariant}:${row?.profileId}`;
    if(!expectedMatrixKeys.delete(key))throw new Error(`Lane C Fixed persistence matrix row is unexpected or duplicated: ${key}`);
    if(row?.managementMode!=='FIXED_HORIZON'||row?.winnerEligible!==false)throw new Error(`Lane C Fixed persistence matrix row is not interpretation-locked: ${key}`);
    if(row.profileId==='CURRENT_EXISTING'&&row.resultClass!=='REFERENCE_ONLY_NOT_CAUSAL')throw new Error(`Lane C Fixed persistence Current row must remain reference-only: ${key}`);
    if(row.profileId!=='CURRENT_EXISTING'&&row.resultClass!=='CAUSAL_EVENT_TIME_PORTFOLIO')throw new Error(`Lane C Fixed persistence causal row classification mismatch: ${key}`);
  }
  if(expectedMatrixKeys.size)throw new Error('Lane C Fixed persistence matrix combinations are missing');

  const curves={};
  for(const variant of PHASE57_P25_LANE_C_FIXED_PERSISTENCE_VARIANTS){
    const comparison=artifact.result.comparisons?.[variant];
    if(comparison?.status!=='LANE_C_PAIRED_ALLOCATION_PROFILES_SIMULATED')throw new Error(`Lane C Fixed persistence comparison missing for ${variant}`);
    assertSafetyFalse(comparison.safety,`comparison ${variant}`);
    assertExactOrder(comparison.resultOrder,PHASE57_P25_LANE_C_FIXED_PERSISTENCE_PROFILES,`comparison ${variant} profiles`);
    if(artifact.result.sourceReconciliation?.byUniverseVariant?.[variant]?.currentReferenceMatchesFormalP25!==true){
      throw new Error(`Lane C Fixed persistence Current reference does not match formal P25 for ${variant}`);
    }
    if(comparison.pairedAudit?.sameFrozenEntryCandidates!==true||comparison.pairedAudit?.sameManagementResult!==true||comparison.pairedAudit?.onlyCausalAllocationProfileChanged!==true){
      throw new Error(`Lane C Fixed persistence paired audit failed for ${variant}`);
    }
    if(comparison.interpretation?.winnerSelectionAllowed!==false||comparison.interpretation?.prospectiveSampleSufficient!==false){
      throw new Error(`Lane C Fixed persistence interpretation lock failed for ${variant}`);
    }
    const current=comparison.results?.CURRENT_EXISTING;
    if(current?.status!=='REFERENCE_ONLY_NOT_CAUSAL_PORTFOLIO'||current.max10Equivalent!==null||current.eligibleForCapitalAllocationWinnerSelection!==false||current.comparableWithEventDrivenProfiles!==false){
      throw new Error(`Lane C Fixed persistence Current must remain separate from Max10 for ${variant}`);
    }
    assertSafetyFalse(current.safety,`Current reference ${variant}`);
    curves[variant]={};
    for(const profileId of PHASE57_P25_LANE_C_FIXED_PERSISTENCE_PROFILES.slice(1)){
      const result=comparison.results?.[profileId];
      if(result?.status!=='LANE_C_EVENT_TIME_PORTFOLIO_SIMULATED')throw new Error(`Lane C Fixed persistence causal result missing for ${variant}/${profileId}`);
      assertSafetyFalse(result.safety,`result ${variant}/${profileId}`);
      assertBoolean(result.methodology?.allocatorCanSeeFutureExit,false,`allocator future outcome visibility ${variant}/${profileId}`);
      assertBoolean(result.methodology?.availableCashConstrainsPurchase,true,`available cash constraint ${variant}/${profileId}`);
      curves[variant][profileId]=curveAudit(result);
    }
  }

  return Object.freeze({evidenceDate:String(dates.at(-1)),curveAudit:Object.freeze(curves)});
}

export function buildLaneCFixedPersistenceSummary({artifact,sourceRunId,rawArtifactBytes,archiveBytes,rawArtifactName,archiveName}={}){
  const {evidenceDate,curveAudit:curves}=validateLaneCFixedPortfolioArtifact(artifact);
  if(!/^\d+$/.test(String(sourceRunId??'')))throw new Error('Lane C Fixed persistence source run id must be numeric');
  if(!Buffer.isBuffer(rawArtifactBytes)||!rawArtifactBytes.length)throw new Error('Lane C Fixed persistence raw artifact bytes are required');
  if(!Buffer.isBuffer(archiveBytes)||!archiveBytes.length)throw new Error('Lane C Fixed persistence archive bytes are required');
  const rawSha256=sha256(rawArtifactBytes),archiveSha256=sha256(archiveBytes);
  return Object.freeze({
    schemaVersion:1,
    phase:'57.p25.lane-c.fixed-portfolio-persistence-summary',
    status:'LANE_C_FIXED_PORTFOLIO_PERSISTENCE_SUMMARY_READY',
    evidenceDate,
    sourceRunId:String(sourceRunId),
    lineageManifestHeadSha256:artifact.result.lineageManifestHeadSha256,
    resultCanonicalSha256:artifact.resultCanonicalSha256,
    sourceEvaluationCanonicalSha256:artifact.result.sourceReconciliation.sourceEvaluationCanonicalSha256,
    inputAudit:artifact.result.inputAudit,
    universeVariantOrder:artifact.result.universeVariantOrder,
    profileOrder:artifact.result.profileOrder,
    matrixRows:artifact.result.matrixRows,
    curveAudit:curves,
    fullArtifact:Object.freeze({
      rawArtifactName:String(rawArtifactName??''),
      rawSha256,
      rawBytes:rawArtifactBytes.length,
      archiveName:String(archiveName??''),
      archiveFormat:'gzip',
      archiveSha256,
      archiveBytes:archiveBytes.length,
      containsFullFiveMinuteMtmEquityCurves:true,
      containsFullConcentrationCurves:true,
      githubActionsRawArtifactRetained:true,
    }),
    methodology:Object.freeze({
      formalP25EvaluationReconciledBeforeSimulation:true,
      sameFrozenEntry:true,
      fixedHorizonExitUnchanged:true,
      currentExistingReferenceOnly:true,
      max10AssumedEquivalentToCurrent:false,
      dynamicManagementArtifactUsed:false,
      appendOnlyDatedPersistence:true,
      performanceRankingUsed:false,
      winnerSelectionAllowed:false,
      prospectiveSampleSufficient:false,
      freshHoldoutConsumed:false,
    }),
    safety:artifact.safety,
  });
}

export const LaneCFixedPersistenceInternals=Object.freeze({canonicalSha256,sha256});

export default {buildLaneCFixedPersistenceSummary,validateLaneCFixedPortfolioArtifact};
