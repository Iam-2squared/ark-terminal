import {assembleP253AutonomousEvidenceInputs,PHASE57_P25_3D_SAFETY} from './phase57-p25-3d-autonomous-evidence-evaluation.js';
import {buildP253PCheckpointPlan,validateP253PCheckpointCoverage} from './phase57-p25-3p-checkpoint-plan.js';
import {recombineP253PrefixShards} from './phase57-p25-3o-sharded-prefix-replay.js';
import {materializeP252FixedHorizonOutcomes} from './phase57-p25-2g-fixed-horizon-outcome-materialization.js';
import {accumulateP252MultiSessionEvidence} from './phase57-p25-2h-multisession-evidence-accumulator.js';
import {PHASE57_P25_2I_SAFETY} from './phase57-p25-2i-end-to-end-prospective-evaluation.js';

export const PHASE57_P25_3Q_SAFETY=Object.freeze({...PHASE57_P25_3D_SAFETY,phase:'57.p25.3q.checkpointed-evaluation'});

const normalizeSha=value=>String(value??'').toLowerCase();

function assertCheckpointIdentity({checkpoint,session,batchSize}){
  if(Number(checkpoint?.batchSize)!==Number(batchSize))throw new Error(`P25.3Q batch size mismatch for ${checkpoint?.batchId??'UNKNOWN'}`);
  const sessionDate=String(session?.sessionDate??session?.universeRecord?.sessionDate??'');
  if(String(checkpoint?.identities?.sessionDate??'')!==sessionDate)throw new Error(`P25.3Q checkpoint session mismatch ${checkpoint?.batchId??'UNKNOWN'}`);
  const expectedCaptureSha=normalizeSha(session?.sourceProvenance?.captureArtifactSha256);
  const checkpointCaptureSha=normalizeSha(checkpoint?.identities?.captureSha256);
  if(expectedCaptureSha&&checkpointCaptureSha!==expectedCaptureSha)throw new Error(`P25.3Q capture identity mismatch ${checkpoint?.batchId??'UNKNOWN'}`);
  if(checkpoint?.methodology?.computePlacementOnly!==true||checkpoint?.methodology?.fullUnionFairCutoffGridPreserved!==true)throw new Error(`P25.3Q checkpoint methodology mismatch ${checkpoint?.batchId??'UNKNOWN'}`);
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','freshHoldoutConsumed']){
    if(checkpoint?.safety?.[key]!==false)throw new Error(`P25.3Q checkpoint safety ${key} must be false`);
  }
}

export function runP253QCheckpointedEvaluation({
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
    if(!checkpoints.length)throw new Error(`P25.3Q checkpoints missing for ${sessionDate}`);
    const batchSize=Number(checkpoints[0]?.batchSize);
    if(!Number.isInteger(batchSize)||batchSize<1)throw new Error(`P25.3Q invalid batch size for ${sessionDate}`);
    const plan=buildP253PCheckpointPlan({universeRecord:session.universeRecord,batchSize});
    for(const checkpoint of checkpoints)assertCheckpointIdentity({checkpoint,session,batchSize});
    validateP253PCheckpointCoverage({plan,checkpoints});
    const recombined=recombineP253PrefixShards({universeRecord:session.universeRecord,shards:checkpoints.map(x=>x.shard)});
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
      sourceProvenance:session.sourceProvenance??null,
    }));
  }

  const evidence=accumulateP252MultiSessionEvidence({sessionPackets:packets,expectedSessionDates:assembled.expectedSessionDates});
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
  const result=Object.freeze({
    phase:'57.p25.2i.end-to-end-prospective-evaluation',
    status:'P25_2_END_TO_END_PROSPECTIVE_EVIDENCE_READY',
    inputSessionCount:assembled.sessionInputs.length,
    readyPacketCount:packets.length,
    blockedSessionCount:0,
    expectedTradingSessionCount:assembled.expectedSessionDates.length,
    expectedTradingSessions:assembled.expectedSessionDates,
    packetSummaries,
    blockedSessions:Object.freeze([]),
    evidence,
    methodology:Object.freeze({
      dailyMarketSpeedRequired:false,
      routineDailyEvaluationProviderAgnostic:true,
      marketSpeedMayBeUsedLaterForSeparateFinalVerification:true,
      marketSpeedVerificationMayChangeFrozenEntry:false,
      microstructureUsed:false,
      boardOrTickRequired:false,
      universeFrozenBeforeSession:true,
      replayMayRunAfterClose:true,
      eachScorerReceivesPrefixOnly:true,
      futureBarsPassedToScorer:false,
      fixedHorizonFormalDefault:true,
      roundTripCostPct:0.05,
      allFiveVariantsRetained:true,
      currentOuterOosDoesNotSelectDynamicN:true,
      entryThresholdRelaxed:false,
      postHocWinnerFiltering:false,
      checkpointedComputeOnly:true,
      freshHoldoutConsumed:false,
    }),
    safety:PHASE57_P25_2I_SAFETY,
  });

  return Object.freeze({
    phase:'57.p25.3d.autonomous-evidence-evaluation',
    status:'P25_3_AUTONOMOUS_EVIDENCE_EVALUATED',
    lineageManifestHeadSha256:assembled.lineageManifestHeadSha256,
    lineageNodeCount:assembled.lineageNodeCount,
    frozenReadySessionInputCount:assembled.sessionInputs.length,
    expectedSessionCount:assembled.expectedSessionDates.length,
    result,
    methodology:Object.freeze({...assembled.methodology,checkpointedComputeOnly:true}),
    safety:PHASE57_P25_3Q_SAFETY,
  });
}

export default {runP253QCheckpointedEvaluation,PHASE57_P25_3Q_SAFETY};
