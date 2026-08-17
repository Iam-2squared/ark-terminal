import {buildPhase57MicrostructureOverlay,PHASE58_FINAL_SAFETY} from './phase58-integration-benchmark.js';

export const PHASE58_PHASE57_FROZEN_OVERLAY_SAFETY=Object.freeze({...PHASE58_FINAL_SAFETY,phase:'58.p8.phase57-frozen-overlay',executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,freshHoldoutConsumed:false});

const signDirection=value=>{
  if(value==='UP'||value==='LONG'||value===1)return 1;
  if(value==='DOWN'||value==='SHORT'||value===-1)return -1;
  return 0;
};

export function normalizeFrozenPhase57Context(context={}){
  const direction=signDirection(context.direction??context.signalDirection??context.phase57Direction);
  return Object.freeze({
    phase:'57.frozen-context',
    direction,
    rawDirection:context.direction??context.signalDirection??context.phase57Direction??null,
    setup:context.setup??null,
    entryEligible:context.entryEligible??context.entryCandidate??null,
    confidence:Number.isFinite(Number(context.confidence))?Number(context.confidence):null,
    sourceTimestamp:context.sourceTimestamp??context.timestamp??null,
    frozenByPhase57:context.frozenByPhase57===true,
    reconstructed:false,
  });
}

export function buildFrozenPhase57MicrostructureDecision({phase57Context={},inputSeries=[],qualityOptions={}}={}){
  const frozen=normalizeFrozenPhase57Context(phase57Context);
  if(!frozen.frozenByPhase57||frozen.direction===0){
    return Object.freeze({phase:'58.p8.phase57-frozen-overlay',status:'BLOCKED_NO_VALID_FROZEN_PHASE57_CONTEXT',base:frozen,action:'DEFER_TO_PHASE57',researchOnly:true,safety:PHASE58_PHASE57_FROZEN_OVERLAY_SAFETY});
  }
  const overlay=buildPhase57MicrostructureOverlay({phase57Direction:frozen.direction,inputSeries,qualityOptions});
  const action=overlay.action==='MICROSTRUCTURE_ALIGNED'?'CONFIRM_PHASE57_ENTRY':overlay.action==='ABSTAIN_LIQUIDITY_SHOCK'?'ABSTAIN_LIQUIDITY_SHOCK':'DEFER_TO_PHASE57';
  return Object.freeze({
    phase:'58.p8.phase57-frozen-overlay',
    status:'PHASE57_FROZEN_OVERLAY_MEASURED',
    base:frozen,
    action,
    confidenceAdjustment:action==='CONFIRM_PHASE57_ENTRY'?1:action==='ABSTAIN_LIQUIDITY_SHOCK'?-1:0,
    overlay,
    directionChanged:false,
    phase57DirectionPreserved:true,
    researchOnly:true,
    recommendationAllowed:false,
    safety:PHASE58_PHASE57_FROZEN_OVERLAY_SAFETY,
  });
}

export default {normalizeFrozenPhase57Context,buildFrozenPhase57MicrostructureDecision,PHASE58_PHASE57_FROZEN_OVERLAY_SAFETY};
