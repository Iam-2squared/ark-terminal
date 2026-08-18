import {replayP252FrozenDaySession} from './phase57-p25-2f-postsession-point-in-time-replay.js';
import {materializeP252FixedHorizonOutcomes} from './phase57-p25-2g-fixed-horizon-outcome-materialization.js';
import {accumulateP252MultiSessionEvidence} from './phase57-p25-2h-multisession-evidence-accumulator.js';

export const PHASE57_P25_2I_SAFETY=Object.freeze({
  phase:'57.p25.2i.end-to-end-prospective-evaluation',
  mode:'READ_ONLY_PROVIDER_AGNOSTIC_END_TO_END_EVALUATION',
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

export const PHASE57_P25_2I_POLICY=Object.freeze({
  dailyMarketSpeedRequired:false,
  marketSpeedVerificationOptionalAndSeparate:true,
  microstructureUsed:false,
  boardOrTickRequired:false,
  fullSessionBarsMayBeCollectedAfterClose:true,
  scorerReceivesPrefixOnly:true,
  frozenUniverseBeforeSessionRequired:true,
  fixedHorizonFormalDefault:true,
  roundTripCostPct:0.05,
  allFiveVariantsRetained:true,
  dynamicNSelectedFromCurrentOuterOos:false,
  entryThresholdRelaxationAllowed:false,
  postHocWinnerFilteringAllowed:false,
});

function sessionDateOf(input){
  return String(input?.sessionDate??input?.universeRecord?.sessionDate??'').trim();
}
function normalizeExpected(values){
  return [...new Set((Array.isArray(values)?values:[]).map(String).filter(x=>/^\d{4}-\d{2}-\d{2}$/.test(x)))].sort();
}
function freezeFailure({sessionDate,status,reason,sourceProvenance=null}){
  return Object.freeze({
    sessionDate:sessionDate||null,
    status,
    reason:String(reason??'UNKNOWN'),
    sourceProvenance:sourceProvenance&&typeof sourceProvenance==='object'?Object.freeze({...sourceProvenance}):sourceProvenance,
  });
}

/**
 * Compose the already-frozen P25.2 stages into one reproducible research pipeline:
 * frozen pre-open universe -> post-session prefix-only replay -> immutable Entry
 * ledger -> frozen Fixed Horizon outcomes -> five-variant multi-session evidence.
 *
 * The session bar source is intentionally provider-agnostic. MARKETSPEED II / Excel
 * is not required for routine daily evaluation. Any later RSS verification remains a
 * separate validation surface and cannot change these frozen Entries or outcomes.
 */
export function runP252EndToEndProspectiveEvaluation({
  sessionInputs=[],
  historicalSessions=[],
  expectedSessionDates=[],
  scorePrefix,
}={}){
  const inputs=Array.isArray(sessionInputs)?sessionInputs:[];
  const expected=normalizeExpected(expectedSessionDates);
  const seen=new Set(),packets=[],failures=[];

  for(const input of inputs){
    const sessionDate=sessionDateOf(input);
    if(!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate))throw new Error('P25.2I session input requires YYYY-MM-DD sessionDate');
    if(seen.has(sessionDate))throw new Error(`duplicate P25.2I session input: ${sessionDate}`);
    seen.add(sessionDate);
    if(expected.length&&!expected.includes(sessionDate))throw new Error(`P25.2I session input ${sessionDate} is outside expectedSessionDates`);

    const universeRecord=input?.universeRecord;
    if(universeRecord?.ready!==true||String(universeRecord?.sessionDate??'')!==sessionDate){
      failures.push(freezeFailure({sessionDate,status:'BLOCKED_UNIVERSE_NOT_READY',reason:universeRecord?.reason??'READY_FROZEN_UNIVERSE_REQUIRED',sourceProvenance:input?.sourceProvenance??null}));
      continue;
    }

    let replay;
    try{
      replay=replayP252FrozenDaySession({
        universeRecord,
        historicalSessions,
        sessionBarsBySymbol:input?.sessionBarsBySymbol??{},
        ...(typeof scorePrefix==='function'?{scorePrefix}:{}),
      });
    }catch(error){
      failures.push(freezeFailure({sessionDate,status:'BLOCKED_SESSION_REPLAY_EXCEPTION',reason:error?.message??error,sourceProvenance:input?.sourceProvenance??null}));
      continue;
    }

    const ledger=replay?.ledger;
    if(!ledger||String(ledger?.sessionDate??'')!==sessionDate){
      failures.push(freezeFailure({sessionDate,status:'BLOCKED_LEDGER_NOT_READY',reason:replay?.status??'P25_2F_LEDGER_MISSING',sourceProvenance:input?.sourceProvenance??null}));
      continue;
    }

    let outcomes;
    try{
      outcomes=materializeP252FixedHorizonOutcomes({
        frozenTrades:ledger.frozenTrades??[],
        sessionBarsBySymbol:input?.sessionBarsBySymbol??{},
        regimeBySession:input?.regimeBySession??{},
      });
    }catch(error){
      failures.push(freezeFailure({sessionDate,status:'BLOCKED_OUTCOME_MATERIALIZATION_EXCEPTION',reason:error?.message??error,sourceProvenance:input?.sourceProvenance??null}));
      continue;
    }

    packets.push(Object.freeze({
      sessionDate,
      universeRecord,
      replay,
      ledger,
      outcomes,
      blockedDecisions:replay?.blockedDecisions??[],
      sourceProvenance:input?.sourceProvenance&&typeof input.sourceProvenance==='object'?Object.freeze({...input.sourceProvenance}):input?.sourceProvenance??null,
    }));
  }

  const operationalSessions=expected.length?expected:[...new Set([...inputs.map(sessionDateOf),...packets.map(x=>x.sessionDate)])].filter(x=>/^\d{4}-\d{2}-\d{2}$/.test(x)).sort();
  const evidence=accumulateP252MultiSessionEvidence({
    sessionPackets:packets,
    expectedSessionDates:operationalSessions,
  });

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

  return Object.freeze({
    phase:'57.p25.2i.end-to-end-prospective-evaluation',
    status:'P25_2_END_TO_END_PROSPECTIVE_EVIDENCE_READY',
    inputSessionCount:inputs.length,
    readyPacketCount:packets.length,
    blockedSessionCount:failures.length,
    expectedTradingSessionCount:operationalSessions.length,
    expectedTradingSessions:Object.freeze(operationalSessions),
    packetSummaries,
    blockedSessions:Object.freeze(failures),
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
      roundTripCostPct:PHASE57_P25_2I_POLICY.roundTripCostPct,
      allFiveVariantsRetained:true,
      currentOuterOosDoesNotSelectDynamicN:true,
      entryThresholdRelaxed:false,
      postHocWinnerFiltering:false,
      freshHoldoutConsumed:false,
    }),
    safety:PHASE57_P25_2I_SAFETY,
  });
}

export default {runP252EndToEndProspectiveEvaluation,PHASE57_P25_2I_POLICY,PHASE57_P25_2I_SAFETY};
