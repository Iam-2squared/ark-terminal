import {createHash} from 'node:crypto';
import {assembleP253AutonomousEvidenceInputs} from '../daytrade/phase57-p25-3d-autonomous-evidence-evaluation.js';
import {buildP253PCheckpointPlan,validateP253PCheckpointCoverage} from '../daytrade/phase57-p25-3p-checkpoint-plan.js';
import {recombineP253PrefixShards} from '../daytrade/phase57-p25-3o-sharded-prefix-replay.js';
import {runP253QCheckpointedEvaluation} from '../daytrade/phase57-p25-3q-checkpointed-evaluation.js';
import {materializeP252FixedHorizonOutcomes} from '../daytrade/phase57-p25-2g-fixed-horizon-outcome-materialization.js';
import {PHASE57_P25_2H_VARIANTS} from '../daytrade/phase57-p25-2h-multisession-evidence-accumulator.js';
import {
  buildP252FixedPortfolioSessions,
  compareLaneCAllocationProfiles,
  PHASE57_P25_LANE_C_ALLOCATION_PROFILES,
  PHASE57_P25_LANE_C_POLICY,
} from './phase57-p25-lane-c-portfolio-simulator.js';

export const PHASE57_P25_LANE_C_FIXED_RUNNER_SAFETY=Object.freeze({
  phase:'57.p25.lane-c.fixed-checkpoint-portfolio',
  mode:'READ_ONLY_LINEAGE_PINNED_FIXED_PORTFOLIO_RESEARCH',
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

export const PHASE57_P25_LANE_C_FIXED_RUNNER_POLICY=Object.freeze({
  managementMode:'FIXED_HORIZON',
  initialEquityJpy:PHASE57_P25_LANE_C_POLICY.initialEquityJpy,
  lotSize:PHASE57_P25_LANE_C_POLICY.lotSize,
  roundTripCostPct:PHASE57_P25_LANE_C_POLICY.fixedRoundTripCostPct,
  slippageBps:PHASE57_P25_LANE_C_POLICY.baselineSlippageBps,
  universeVariants:PHASE57_P25_2H_VARIANTS,
  allocationProfiles:PHASE57_P25_LANE_C_ALLOCATION_PROFILES.map(row=>row.id),
  currentExistingReferenceOnly:true,
  max10AssumedEquivalentToCurrent:false,
  officialEvaluationReconciliationRequired:true,
  dynamicManagementArtifactRequired:false,
  dynamicManagementChanged:false,
  winnerSelectionAllowed:false,
});

const FALSE_SAFETY_KEYS=Object.freeze([
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed',
  'transmitted','freshHoldoutConsumed',
]);
const CHECKPOINT_REQUIRED_FALSE_KEYS=Object.freeze(FALSE_SAFETY_KEYS.filter(key=>key!=='transmitted'));
const normalizeSha=value=>String(value??'').toLowerCase();

function assertSafetyFalse(safety,label,{transmittedMayBeAbsent=false}={}){
  const required=transmittedMayBeAbsent?CHECKPOINT_REQUIRED_FALSE_KEYS:FALSE_SAFETY_KEYS;
  for(const key of required){
    if(safety?.[key]!==false)throw new Error(`Lane C Fixed runner ${label} safety ${key} must be false`);
  }
  if(transmittedMayBeAbsent&&safety?.transmitted!==undefined&&safety.transmitted!==false){
    throw new Error(`Lane C Fixed runner ${label} safety transmitted must not be true`);
  }
}

function canonicalize(value){
  if(Array.isArray(value))return value.map(canonicalize);
  if(value&&typeof value==='object'){
    return Object.fromEntries(Object.keys(value).sort().map(key=>[key,canonicalize(value[key])]));
  }
  return value;
}

function canonicalSha256(value){
  return createHash('sha256').update(JSON.stringify(canonicalize(value))).digest('hex');
}

function unwrapSourceEvaluation(sourceEvaluationArtifact){
  const evaluation=sourceEvaluationArtifact?.evaluation??sourceEvaluationArtifact;
  if(evaluation?.phase!=='57.p25.3d.autonomous-evidence-evaluation'||evaluation?.status!=='P25_3_AUTONOMOUS_EVIDENCE_EVALUATED'){
    throw new Error('Lane C Fixed runner requires the formal P25.3Q evaluation artifact');
  }
  if(sourceEvaluationArtifact?.safety)assertSafetyFalse(sourceEvaluationArtifact.safety,'source evaluation artifact');
  assertSafetyFalse(evaluation.safety,'source evaluation');
  return evaluation;
}

function assertCheckpointIdentity({checkpoint,session,batchSize}){
  if(Number(checkpoint?.batchSize)!==Number(batchSize))throw new Error(`Lane C Fixed checkpoint batch size mismatch for ${checkpoint?.batchId??'UNKNOWN'}`);
  const sessionDate=String(session?.sessionDate??session?.universeRecord?.sessionDate??'');
  if(String(checkpoint?.identities?.sessionDate??'')!==sessionDate)throw new Error(`Lane C Fixed checkpoint session mismatch ${checkpoint?.batchId??'UNKNOWN'}`);
  const expectedCaptureSha=normalizeSha(session?.sourceProvenance?.captureArtifactSha256);
  const checkpointCaptureSha=normalizeSha(checkpoint?.identities?.captureSha256);
  if(expectedCaptureSha&&checkpointCaptureSha!==expectedCaptureSha)throw new Error(`Lane C Fixed capture identity mismatch ${checkpoint?.batchId??'UNKNOWN'}`);
  if(checkpoint?.methodology?.computePlacementOnly!==true||checkpoint?.methodology?.fullUnionFairCutoffGridPreserved!==true){
    throw new Error(`Lane C Fixed checkpoint methodology mismatch ${checkpoint?.batchId??'UNKNOWN'}`);
  }
  assertSafetyFalse(checkpoint?.safety,`checkpoint ${checkpoint?.batchId??'UNKNOWN'}`,{transmittedMayBeAbsent:true});
}

export function buildLaneCFixedCheckpointPackets({
  historyPack,
  captureArtifacts=[],
  sessionIntegrityLedger,
  lineageManifest,
  checkpointsBySession={},
}={}){
  const assembled=assembleP253AutonomousEvidenceInputs({historyPack,captureArtifacts,sessionIntegrityLedger,lineageManifest});
  const packets=[];
  for(const session of assembled.sessionInputs){
    const sessionDate=String(session.sessionDate??session.universeRecord?.sessionDate??'');
    const checkpoints=Array.isArray(checkpointsBySession?.[sessionDate])?checkpointsBySession[sessionDate]:[];
    if(!checkpoints.length)throw new Error(`Lane C Fixed checkpoints missing for ${sessionDate}`);
    const batchSize=Number(checkpoints[0]?.batchSize);
    if(!Number.isInteger(batchSize)||batchSize<1)throw new Error(`Lane C Fixed invalid batch size for ${sessionDate}`);
    const plan=buildP253PCheckpointPlan({universeRecord:session.universeRecord,batchSize});
    for(const checkpoint of checkpoints)assertCheckpointIdentity({checkpoint,session,batchSize});
    validateP253PCheckpointCoverage({plan,checkpoints});
    const recombined=recombineP253PrefixShards({universeRecord:session.universeRecord,shards:checkpoints.map(row=>row.shard)});
    const outcomes=materializeP252FixedHorizonOutcomes({
      frozenTrades:recombined.ledger?.frozenTrades??[],
      sessionBarsBySymbol:session.sessionBarsBySymbol??{},
      regimeBySession:session.regimeBySession??{},
    });
    packets.push(Object.freeze({
      sessionDate,
      universeRecord:session.universeRecord,
      replay:recombined,
      ledger:recombined.ledger,
      outcomes,
      blockedDecisions:recombined.blockedDecisions??[],
      sessionBarsBySymbol:session.sessionBarsBySymbol??{},
      sourceProvenance:session.sourceProvenance??null,
    }));
  }
  const packetSummaries=Object.freeze(packets.map(packet=>Object.freeze({
    sessionDate:packet.sessionDate,
    replayStatus:packet.replay?.status??null,
    commonFairCutoffCount:Number(packet.replay?.commonFairCutoffCount??0),
    blockedDecisionCount:Number(packet.replay?.blockedDecisionCount??0),
    ledgerStatus:packet.ledger?.status??null,
    frozenTradeCount:Number(packet.ledger?.frozenTrades?.length??0),
    resolvedTradeCount:Number(packet.outcomes?.resolvedCount??0),
    unresolvedTradeCount:Number(packet.outcomes?.unresolvedCount??0),
    sourceProvenance:packet.sourceProvenance??null,
  })));
  return Object.freeze({assembled,packets:Object.freeze(packets),packetSummaries});
}

function assertReferenceReconciliation({comparison,sourceEvaluation,universeVariant,initialEquity}){
  const sourceComparison=sourceEvaluation?.result?.evidence?.comparison;
  const joined=Number(sourceComparison?.joinedTradeCounts?.[universeVariant]);
  if(!Number.isInteger(joined)||joined<0)throw new Error(`Lane C Fixed source joined-trade count missing for ${universeVariant}`);
  if(comparison.pairedAudit.candidateEntryCount!==joined)throw new Error(`Lane C Fixed joined-trade count mismatch for ${universeVariant}`);
  const sourceReference=sourceComparison?.results?.[universeVariant]?.sessionEqualWeightPortfolio;
  const current=comparison.results.CURRENT_EXISTING;
  if(!sourceReference)throw new Error(`Lane C Fixed source Current reference missing for ${universeVariant}`);
  const expectedFinal=Number(sourceReference.finalEquity)*Number(initialEquity);
  if(Math.abs(current.referenceMetrics.illustrativeFinalEquityJpy-expectedFinal)>1){
    throw new Error(`Lane C Fixed Current reference final-equity mismatch for ${universeVariant}`);
  }
  if(Math.abs(current.referenceMetrics.totalReturnPct-Number(sourceReference.afterCostNetPct))>1e-6){
    throw new Error(`Lane C Fixed Current reference return mismatch for ${universeVariant}`);
  }
  if(Math.abs(current.referenceMetrics.maxDrawdownPct-Number(sourceReference.maxDrawdownPct))>1e-6){
    throw new Error(`Lane C Fixed Current reference drawdown mismatch for ${universeVariant}`);
  }
  const sourceSessions=(sourceReference.sessions??[]).map(row=>({sessionDate:String(row.sessionDate),returnPct:Number(row.returnPct)}));
  const currentSessions=current.sessionCurve.map(row=>({sessionDate:row.sessionDate,returnPct:row.returnPct}));
  if(canonicalSha256(sourceSessions)!==canonicalSha256(currentSessions))throw new Error(`Lane C Fixed Current reference session curve mismatch for ${universeVariant}`);
  return Object.freeze({
    joinedTradeCount:joined,
    currentReferenceMatchesFormalP25:true,
    sourceReferenceFinalEquityMultiple:Number(sourceReference.finalEquity),
  });
}

function matrixRows({comparison,universeVariant}){
  return Object.freeze(comparison.resultOrder.map(profileId=>{
    const result=comparison.results[profileId];
    if(profileId==='CURRENT_EXISTING'){
      return Object.freeze({
        managementMode:'FIXED_HORIZON',universeVariant,profileId,
        resultClass:'REFERENCE_ONLY_NOT_CAUSAL',winnerEligible:false,
        candidateEntryCount:comparison.pairedAudit.candidateEntryCount,acceptedTradeCount:null,rejectedTradeCount:null,
        finalEquityJpy:result.referenceMetrics.illustrativeFinalEquityJpy,totalReturnPct:result.referenceMetrics.totalReturnPct,
        maxDrawdownPct:result.referenceMetrics.maxDrawdownPct,annualizedVolatilityPct:null,sharpe:null,
        averageCapitalUtilization:null,averageCashRatio:null,capitalRecyclingCount:null,turnover:null,
        maximumSymbolShare:null,maximumSectorShare:null,
      });
    }
    return Object.freeze({
      managementMode:'FIXED_HORIZON',universeVariant,profileId,
      resultClass:'CAUSAL_EVENT_TIME_PORTFOLIO',winnerEligible:false,
      candidateEntryCount:result.trade.candidates,acceptedTradeCount:result.trade.accepted,rejectedTradeCount:result.trade.rejected,
      finalEquityJpy:result.return.finalEquityJpy,totalReturnPct:result.return.totalReturnPct,
      maxDrawdownPct:result.risk.maxDrawdownPct,annualizedVolatilityPct:result.risk.annualizedVolatilityPct,sharpe:result.risk.sharpe,
      averageCapitalUtilization:result.capitalEfficiency.averageCapitalUtilization,averageCashRatio:result.capitalEfficiency.averageCashRatio,
      capitalRecyclingCount:result.capitalEfficiency.capitalRecyclingCount,turnover:result.capitalEfficiency.turnover,
      maximumSymbolShare:result.concentration.maximumSymbolShare,maximumSectorShare:result.concentration.maximumSectorShare,
    });
  }));
}

export function runLaneCFixedCheckpointedPortfolio({
  historyPack,
  captureArtifacts=[],
  sessionIntegrityLedger,
  lineageManifest,
  checkpointsBySession={},
  sourceEvaluationArtifact,
  universeVariants=PHASE57_P25_2H_VARIANTS,
  profiles=PHASE57_P25_LANE_C_ALLOCATION_PROFILES,
  initialEquity=PHASE57_P25_LANE_C_FIXED_RUNNER_POLICY.initialEquityJpy,
}={}){
  assertSafetyFalse(PHASE57_P25_LANE_C_FIXED_RUNNER_SAFETY,'runner');
  const selected=[...(Array.isArray(universeVariants)?universeVariants:[])];
  if(!selected.length)throw new Error('Lane C Fixed runner requires at least one universe variant');
  if(new Set(selected).size!==selected.length||selected.some(variant=>!PHASE57_P25_2H_VARIANTS.includes(variant))){
    throw new Error('Lane C Fixed runner universe variants must be unique precommitted P25 variants');
  }
  const sourceEvaluation=unwrapSourceEvaluation(sourceEvaluationArtifact);
  const recomputedEvaluation=runP253QCheckpointedEvaluation({
    historyPack,captureArtifacts,sessionIntegrityLedger,lineageManifest,checkpointsBySession,
  });
  const sourceEvaluationSha256=canonicalSha256(sourceEvaluation);
  const recomputedEvaluationSha256=canonicalSha256(recomputedEvaluation);
  if(sourceEvaluationSha256!==recomputedEvaluationSha256)throw new Error('Lane C Fixed formal P25 evaluation artifact does not match checkpoint recomputation');

  const packetBundle=buildLaneCFixedCheckpointPackets({
    historyPack,captureArtifacts,sessionIntegrityLedger,lineageManifest,checkpointsBySession,
  });
  if(packetBundle.assembled.lineageManifestHeadSha256!==sourceEvaluation.lineageManifestHeadSha256){
    throw new Error('Lane C Fixed lineage head differs from formal P25 evaluation');
  }
  if(canonicalSha256(packetBundle.packetSummaries)!==canonicalSha256(sourceEvaluation.result?.packetSummaries??[])){
    throw new Error('Lane C Fixed packet summaries differ from formal P25 evaluation');
  }

  const comparisons={},referenceReconciliation={},rows=[];
  for(const universeVariant of selected){
    const sessions=buildP252FixedPortfolioSessions({sessionPackets:packetBundle.packets,universeVariant});
    const comparison=compareLaneCAllocationProfiles({
      sessions,profiles,initialEquity,managementMode:'FIXED_HORIZON',universeVariant,
      roundTripCostPct:PHASE57_P25_LANE_C_FIXED_RUNNER_POLICY.roundTripCostPct,
      slippageBps:PHASE57_P25_LANE_C_FIXED_RUNNER_POLICY.slippageBps,
    });
    referenceReconciliation[universeVariant]=assertReferenceReconciliation({comparison,sourceEvaluation,universeVariant,initialEquity});
    comparisons[universeVariant]=comparison;
    rows.push(...matrixRows({comparison,universeVariant}));
  }

  const frozenTradeCount=packetBundle.packets.reduce((sum,packet)=>sum+Number(packet.ledger?.frozenTrades?.length??0),0);
  const resolvedTradeCount=packetBundle.packets.reduce((sum,packet)=>sum+Number(packet.outcomes?.resolvedCount??0),0);
  const unresolvedTradeCount=packetBundle.packets.reduce((sum,packet)=>sum+Number(packet.outcomes?.unresolvedCount??0),0);
  return Object.freeze({
    phase:'57.p25.lane-c.fixed-checkpoint-portfolio',
    status:'LANE_C_FIXED_CHECKPOINTED_PORTFOLIO_MATRIX_READY',
    managementMode:'FIXED_HORIZON',
    initialEquityJpy:Number(initialEquity),
    universeVariantOrder:Object.freeze(selected),
    profileOrder:Object.freeze(['CURRENT_EXISTING',...profiles.map(row=>row.id)]),
    lineageManifestHeadSha256:packetBundle.assembled.lineageManifestHeadSha256,
    sourceReconciliation:Object.freeze({
      formalP25EvaluationRequired:true,
      exactCheckpointRecomputationMatch:true,
      sourceEvaluationCanonicalSha256:sourceEvaluationSha256,
      recomputedEvaluationCanonicalSha256:recomputedEvaluationSha256,
      packetSummariesMatch:true,
      byUniverseVariant:Object.freeze(referenceReconciliation),
    }),
    inputAudit:Object.freeze({
      readySessionCount:packetBundle.packets.length,
      expectedSessionCount:packetBundle.assembled.expectedSessionDates.length,
      expectedSessionDates:packetBundle.assembled.expectedSessionDates,
      checkpointArtifactCount:Object.values(checkpointsBySession??{}).reduce((sum,value)=>sum+(Array.isArray(value)?value.length:0),0),
      frozenTradeCount,resolvedTradeCount,unresolvedTradeCount,
      packetSummaries:packetBundle.packetSummaries,
    }),
    comparisons:Object.freeze(comparisons),
    matrixRows:Object.freeze(rows),
    methodology:Object.freeze({
      sameFrozenEntry:true,
      fixedHorizonExitUnchanged:true,
      dynamicHoldExitConnected:false,
      allRequestedUniverseVariantsComparedSeparately:true,
      dynamicVariantNamesAreUniverseSizesNotManagementModes:true,
      currentExistingReferenceOnly:true,
      max10AssumedEquivalentToCurrent:false,
      onlyCausalAllocationProfilesComparedForAllocationEdge:true,
      eventTimeOnly:true,
      availableCashConstrainsPurchase:true,
      unrealizedPnlInEquityButNotCash:true,
      futureExitOrReturnVisibleToAllocator:false,
      winnerSelectionAllowed:false,
      prospectiveSampleSufficient:false,
      signalEdgeChanged:false,
      managementEdgeChanged:false,
      freshHoldoutConsumed:false,
    }),
    safety:PHASE57_P25_LANE_C_FIXED_RUNNER_SAFETY,
  });
}

export const LaneCFixedCheckpointRunnerInternals=Object.freeze({
  assertCheckpointIdentity,canonicalSha256,unwrapSourceEvaluation,
});

export default {
  runLaneCFixedCheckpointedPortfolio,
  buildLaneCFixedCheckpointPackets,
  PHASE57_P25_LANE_C_FIXED_RUNNER_POLICY,
  PHASE57_P25_LANE_C_FIXED_RUNNER_SAFETY,
};
