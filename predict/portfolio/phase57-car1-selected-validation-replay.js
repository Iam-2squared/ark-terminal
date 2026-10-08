import {
  buildP252FixedPortfolioSessions,
  PHASE57_P25_LANE_C_ALLOCATION_PROFILES,
  PHASE57_P25_LANE_C_POLICY,
} from './phase57-p25-lane-c-portfolio-simulator.js';
import {runCar1CounterfactualPortfolioAttribution} from './phase57-car1-counterfactual-replay.js';
import {
  PHASE57_CAR1_PROFILES,
  PHASE57_CAR1_SAFETY,
} from './phase57-car1-sizing-research.js';
import {
  PHASE57_CAR1_VALIDATION_PLAN,
  PHASE57_CAR1_VALIDATION_SAFETY,
} from './phase57-car1-independent-validation.js';

export const PHASE57_CAR1_SELECTED_VALIDATION_REPLAY_SAFETY=Object.freeze({
  phase:'57.car1.selected-validation-replay',
  mode:'READ_ONLY_PRECOMMITTED_SELECTED_SESSION_REPLAY',
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
const round=(value,digits=6)=>Number.isFinite(Number(value))?Number(Number(value).toFixed(digits)):value;

function assertFalseSafety(safety,label){
  for(const key of FALSE_KEYS)if(safety?.[key]!==false)throw new Error(`CAR-1 ${label} safety ${key} must remain false`);
}
function assertReplayBoundary({developmentLock,validationGate}){
  assertFalseSafety(PHASE57_CAR1_SELECTED_VALIDATION_REPLAY_SAFETY,'selected replay');
  assertFalseSafety(PHASE57_CAR1_VALIDATION_SAFETY,'validation');
  assertFalseSafety(PHASE57_CAR1_SAFETY,'sizing');
  assertFalseSafety(validationGate?.safety,'validation gate');
  if(developmentLock?.status!=='CAR1_DEVELOPMENT_EVIDENCE_LOCKED_BEFORE_VALIDATION'||developmentLock?.lockedBeforeValidationOutcomes!==true){
    throw new Error('CAR-1 selected replay requires the frozen development lock');
  }
  if(validationGate?.status!=='CAR1_INDEPENDENT_VALIDATION_WINDOW_READY_FOR_WINDOWED_REPLAY'){
    throw new Error('CAR-1 selected replay requires a completed independent-validation gate');
  }
  if(validationGate?.protocolId!==PHASE57_CAR1_VALIDATION_PLAN.protocolId||developmentLock?.validationPlan?.protocolId!==PHASE57_CAR1_VALIDATION_PLAN.protocolId){
    throw new Error('CAR-1 selected replay validation protocol drift detected');
  }
  if(validationGate?.configurationSha256!==developmentLock?.configurationSha256||validationGate?.sameFrozenConfiguration!==true){
    throw new Error('CAR-1 selected replay configuration lock mismatch');
  }
  if(validationGate?.developmentEvidenceReused!==false||validationGate?.incompleteSessionReplacementAllowed!==false||validationGate?.retrospectiveBackfillAllowed!==false){
    throw new Error('CAR-1 selected replay requires independent no-replacement/no-backfill validation');
  }
  if(validationGate?.parameterSearchAllowed!==false||validationGate?.winnerSelectionAllowed!==false||validationGate?.promotionEligible!==false){
    throw new Error('CAR-1 selected replay cannot search/select/promote');
  }
  if(validationGate?.performanceExtractionAllowed!==false){
    throw new Error('CAR-1 selected replay gate must not expose cumulative challenger performance');
  }
}

function selectedPacketWindow(sessionPackets,selectedSessionDates){
  const selected=[...(Array.isArray(selectedSessionDates)?selectedSessionDates:[])];
  const required=Number(PHASE57_CAR1_VALIDATION_PLAN.requiredSessionCount);
  if(selected.length!==required||new Set(selected).size!==selected.length)throw new Error(`CAR-1 selected replay requires exactly ${required} unique precommitted sessions`);
  const sorted=[...selected].sort();
  if(sorted.some((date,index)=>date!==selected[index]))throw new Error('CAR-1 selected replay session order must be chronological');
  const packets=Array.isArray(sessionPackets)?sessionPackets:[];
  const byDate=new Map();
  for(const packet of packets){
    const date=String(packet?.sessionDate??'');
    if(!/^\d{4}-\d{2}-\d{2}$/.test(date))throw new Error('CAR-1 selected replay packet sessionDate must be YYYY-MM-DD');
    if(byDate.has(date))throw new Error(`duplicate CAR-1 selected replay packet: ${date}`);
    byDate.set(date,packet);
  }
  const chosen=selected.map(date=>{
    const packet=byDate.get(date);
    if(!packet)throw new Error(`CAR-1 selected replay missing precommitted packet ${date}; replacement is forbidden`);
    return packet;
  });
  return Object.freeze({
    packets:Object.freeze(chosen),
    selectedSessionDates:Object.freeze(selected),
    availablePacketCount:packets.length,
    excludedPacketCount:Math.max(0,packets.length-chosen.length),
  });
}

function resolveConfiguration(developmentLock){
  const config=developmentLock?.configuration??{};
  const universeVariantOrder=[...(config.universeVariantOrder??[])];
  const baselineProfileOrder=[...(config.baselineProfileOrder??[])];
  const sizingProfileOrder=[...(config.sizingProfileOrder??[])];
  if(!universeVariantOrder.length||new Set(universeVariantOrder).size!==universeVariantOrder.length)throw new Error('CAR-1 selected replay universe configuration invalid');
  if(!baselineProfileOrder.length||new Set(baselineProfileOrder).size!==baselineProfileOrder.length)throw new Error('CAR-1 selected replay baseline configuration invalid');
  if(!sizingProfileOrder.length||new Set(sizingProfileOrder).size!==sizingProfileOrder.length)throw new Error('CAR-1 selected replay sizing configuration invalid');
  const baselineById=new Map(PHASE57_P25_LANE_C_ALLOCATION_PROFILES.map(row=>[row.id,row]));
  const sizingKnown=new Set(PHASE57_CAR1_PROFILES.map(row=>row.id));
  const baselineProfiles=baselineProfileOrder.map(id=>{
    const row=baselineById.get(id);
    if(!row)throw new Error(`unknown CAR-1 selected replay baseline profile ${id}`);
    return row;
  });
  for(const id of sizingProfileOrder)if(!sizingKnown.has(id))throw new Error(`unknown CAR-1 selected replay sizing profile ${id}`);
  const initialEquity=Number(config.initialEquityJpy);
  if(!Number.isFinite(initialEquity)||initialEquity<=0)throw new Error('CAR-1 selected replay initial equity invalid');
  if(Number(config.roundTripCostPct)!==Number(PHASE57_P25_LANE_C_POLICY.fixedRoundTripCostPct))throw new Error('CAR-1 selected replay cost drift detected');
  if(Number(config.slippageBps)!==Number(PHASE57_P25_LANE_C_POLICY.baselineSlippageBps))throw new Error('CAR-1 selected replay slippage drift detected');
  if(Number(config.lotSize)!==Number(PHASE57_P25_LANE_C_POLICY.lotSize))throw new Error('CAR-1 selected replay lot-size drift detected');
  if(config.managementMode!=='FIXED_HORIZON')throw new Error('CAR-1 selected replay must keep Fixed-Horizon EXIT');
  return Object.freeze({universeVariantOrder,baselineProfileOrder,sizingProfileOrder,baselineProfiles,initialEquity});
}

function resultRow({universeVariant,baselineProfileId,sizingProfileId,result,baseline}){
  return Object.freeze({
    universeVariant,
    managementMode:'FIXED_HORIZON',
    baselineProfileId,
    sizingProfileId,
    resultClass:'PRECOMMITTED_SELECTED_SESSION_CAUSAL_COUNTERFACTUAL_POSITION_SIZING',
    independentValidation:true,
    winnerEligible:false,
    promotionEligible:false,
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

export function runCar1SelectedValidationReplay({
  developmentLock,
  validationGate,
  sessionPackets=[],
}={}){
  assertReplayBoundary({developmentLock,validationGate});
  const config=resolveConfiguration(developmentLock);
  const window=selectedPacketWindow(sessionPackets,validationGate.selectedSessionDates);
  const attributions={},matrixRows=[],parity={};
  for(const universeVariant of config.universeVariantOrder){
    const sessions=buildP252FixedPortfolioSessions({sessionPackets:window.packets,universeVariant});
    attributions[universeVariant]={};
    parity[universeVariant]={};
    for(const baselineProfile of config.baselineProfiles){
      const attribution=runCar1CounterfactualPortfolioAttribution({
        sessions,
        baselineProfile,
        profileIds:config.sizingProfileOrder,
        initialEquity:config.initialEquity,
        managementMode:'FIXED_HORIZON',
        universeVariant,
        roundTripCostPct:PHASE57_P25_LANE_C_POLICY.fixedRoundTripCostPct,
        slippageBps:PHASE57_P25_LANE_C_POLICY.baselineSlippageBps,
      });
      if(attribution?.legacyReplayParity?.passed!==true)throw new Error(`CAR-1 selected replay legacy parity failed for ${universeVariant}/${baselineProfile.id}`);
      if(attribution?.pairedAudit?.sameFrozenEntryCandidates!==true||attribution?.pairedAudit?.sameEntryPrice!==true||
         attribution?.pairedAudit?.sameDirection!==true||attribution?.pairedAudit?.sameFrozenExit!==true||
         attribution?.pairedAudit?.sameCostAssumption!==true||attribution?.pairedAudit?.sameCandidatePriority!==true||
         attribution?.pairedAudit?.baselineBudgetEnvelopeAnchored!==true||attribution?.pairedAudit?.futureOutcomeUsedBySizer!==false){
        throw new Error(`CAR-1 selected replay paired causal lock failed for ${universeVariant}/${baselineProfile.id}`);
      }
      attributions[universeVariant][baselineProfile.id]=attribution;
      parity[universeVariant][baselineProfile.id]=Object.freeze({
        passed:true,
        candidateKeySha256:attribution.pairedAudit.candidateKeySha256,
        candidateEntryCount:Number(attribution.pairedAudit.candidateEntryCount),
      });
      for(const sizingProfileId of config.sizingProfileOrder){
        matrixRows.push(resultRow({
          universeVariant,
          baselineProfileId:baselineProfile.id,
          sizingProfileId,
          result:attribution.results[sizingProfileId],
          baseline:attribution.baseline,
        }));
      }
    }
    attributions[universeVariant]=Object.freeze(attributions[universeVariant]);
    parity[universeVariant]=Object.freeze(parity[universeVariant]);
  }
  return Object.freeze({
    phase:'57.car1.selected-validation-replay',
    status:'CAR1_SELECTED_SESSION_ONLY_VALIDATION_REPLAY_READY',
    protocolId:validationGate.protocolId,
    configurationSha256:validationGate.configurationSha256,
    selectedSessionDates:window.selectedSessionDates,
    universeVariantOrder:Object.freeze(config.universeVariantOrder),
    baselineProfileOrder:Object.freeze(config.baselineProfileOrder),
    sizingProfileOrder:Object.freeze(config.sizingProfileOrder),
    initialEquityJpy:config.initialEquity,
    inputAudit:Object.freeze({
      selectedSessionOnly:true,
      selectedSessionCount:window.selectedSessionDates.length,
      consumedSessionDates:window.selectedSessionDates,
      availablePacketCount:window.availablePacketCount,
      excludedPacketCount:window.excludedPacketCount,
      laterSessionReplacementAllowed:false,
      retrospectiveBackfillAllowed:false,
    }),
    parity:Object.freeze(parity),
    attributions:Object.freeze(attributions),
    matrixRows:Object.freeze(matrixRows),
    methodology:Object.freeze({
      independentValidation:true,
      precommittedProspectiveWindow:true,
      selectedSessionOnly:true,
      cumulativeChallengerPerformanceRequired:false,
      sameFrozenEntry:true,
      sameEntryPrice:true,
      sameDirection:true,
      sameFrozenExit:true,
      sameCostAssumption:true,
      sameCandidatePriority:true,
      baselineBudgetEnvelopeAnchored:true,
      futureOutcomeUsedBySizer:false,
      rankingChanged:false,
      selectorChanged:false,
      entryChanged:false,
      exitChanged:false,
      parameterSearchAllowed:false,
      winnerSelectionAllowed:false,
      promotionEligible:false,
      performanceExtractionAllowed:true,
      performanceExtractionScope:'SELECTED_PRECOMMITTED_SESSIONS_ONLY',
      incompleteProspectiveBackfillAllowed:false,
    }),
    safety:PHASE57_CAR1_SELECTED_VALIDATION_REPLAY_SAFETY,
  });
}

export default {
  PHASE57_CAR1_SELECTED_VALIDATION_REPLAY_SAFETY,
  runCar1SelectedValidationReplay,
};
