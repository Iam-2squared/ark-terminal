import crypto from 'node:crypto';
import {scoreP25ExitV2StateConditioned,P25_EXIT_V2_STATE_CONDITIONED_POLICY} from './phase57-p25-exit-v2-state-conditioned.js';
import {P25_EXIT_V3_INDEPENDENT_PROTOCOL,P25_EXIT_V3_SAFETY} from './phase57-p25-exit-v3-independent-protocol.js';

export const P25_EXIT_V3_DUAL_GATE_POLICY=Object.freeze({
  candidateFamily:P25_EXIT_V3_INDEPENDENT_PROTOCOL.candidateFamily,
  developmentCutoff:P25_EXIT_V3_INDEPENDENT_PROTOCOL.developmentCutoff,
  inheritedAnalogPolicy:P25_EXIT_V2_STATE_CONDITIONED_POLICY,
  loserRescue:Object.freeze({
    rule:'EXIT on causal LOSER_RESCUE evidence when the 1-bar upper 90% CI is <= 0 and at least half of matched outcomes are negative.',
    horizonBars:1,
    maxUpper90Pct:0,
    minDownsideProbability:0.5,
    confirmationBars:1,
  }),
  winnerProtection:Object.freeze({
    rule:'EXIT only after two consecutive causal WINNER_PROTECTION v2 edge-rejection signals; a non-EXIT observation resets confirmation.',
    consecutiveConfirmations:2,
  }),
  neutralDecision:'HOLD',
  exactDynamic50Only:true,
  sameFrozenEntryAsFixed:true,
  fixedBaselineUntouched:true,
  fixedHorizonUsedAsDecisionInput:false,
  legacy27UsedForThresholdTuning:false,
  legacy27UsedForFeatureSelection:false,
  legacy27UsedForHorizonSelection:false,
  legacy27UsedForCoefficientSelection:false,
  legacy27UsedForCandidateSelection:false,
  freshOutcomeUsedForFitting:false,
  resultBasedRetuning:false,
});
const canonical=JSON.stringify(P25_EXIT_V3_DUAL_GATE_POLICY);
export const P25_EXIT_V3_DUAL_GATE_POLICY_SHA256=crypto.createHash('sha256').update(canonical).digest('hex');

export function decideP25ExitV3DualGate({baseScore,winnerExitStreak=0}={}){
  const stateBucket=String(baseScore?.stateBucket??'');
  if(!baseScore?.ready)return Object.freeze({decision:'HOLD',reason:String(baseScore?.reason??'V3_BASE_NOT_READY'),winnerExitStreak:0,stateBucket});
  if(stateBucket==='NEUTRAL_HOLD')return Object.freeze({decision:'HOLD',reason:'V3_NEUTRAL_FAIL_CLOSED',winnerExitStreak:0,stateBucket});
  if(stateBucket==='LOSER_RESCUE'){
    const h1=(baseScore?.horizonScores??[]).find(x=>Number(x?.horizonBars)===P25_EXIT_V3_DUAL_GATE_POLICY.loserRescue.horizonBars);
    const rescue=Boolean(h1)&&Number(h1.upper90Pct)<=P25_EXIT_V3_DUAL_GATE_POLICY.loserRescue.maxUpper90Pct&&Number(h1.downsideProbability)>=P25_EXIT_V3_DUAL_GATE_POLICY.loserRescue.minDownsideProbability;
    return Object.freeze({decision:rescue?'EXIT':'HOLD',reason:rescue?'V3_LOSER_RESCUE_SHORT_HORIZON_EDGE_REJECTED':'V3_LOSER_RESCUE_EVIDENCE_NOT_SUFFICIENT',winnerExitStreak:0,stateBucket,horizon1:h1??null});
  }
  if(stateBucket==='WINNER_PROTECTION'){
    const next=baseScore.decision==='EXIT'?Number(winnerExitStreak)+1:0;
    const confirmed=next>=P25_EXIT_V3_DUAL_GATE_POLICY.winnerProtection.consecutiveConfirmations;
    return Object.freeze({decision:confirmed?'EXIT':'HOLD',reason:confirmed?'V3_WINNER_PROTECTION_CONFIRMED_EDGE_REJECTION':(baseScore.decision==='EXIT'?'V3_WINNER_PROTECTION_CONFIRMATION_PENDING':'V3_WINNER_PROTECTION_EDGE_NOT_REJECTED'),winnerExitStreak:next,stateBucket});
  }
  return Object.freeze({decision:'HOLD',reason:'V3_UNKNOWN_STATE_FAIL_CLOSED',winnerExitStreak:0,stateBucket});
}

function normalizeBars(rows=[]){return rows.map(x=>({timestamp:new Date(Date.parse(x.timestamp??x.time)).toISOString(),open:Number(x.open),high:Number(x.high),low:Number(x.low),close:Number(x.close),volume:Number(x.volume??0)})).filter(x=>[x.open,x.high,x.low,x.close,x.volume].every(Number.isFinite)&&x.close>0).sort((a,b)=>a.timestamp.localeCompare(b.timestamp));}
const dirSign=d=>d==='LONG'||d==='UP'||d===1?1:-1;
const dirRet=(a,b,sign)=>(Number(b)/Number(a)-1)*100*sign;
export function simulateP25ExitV3DualGate({row,analogPool,roundTripCostPct=0.05}={}){
  if(row?.entryAccepted!==true||row?.frozenBeforeOutcome!==true||row?.currentOutcomeUsed!==false)throw new Error('EXIT v3 requires outcome-free frozen Entry');
  const future=normalizeBars(row.futureBars??[]);if(!future.length)throw new Error('EXIT v3 requires sequential futureBars');
  const direction=dirSign(row.signalDirection??row.direction)===1?'LONG':'SHORT',sign=dirSign(direction),entryPrice=Number(row.entryPrice),observed=[],decisions=[];
  let exit=future.at(-1),exitReason='SESSION_END',winnerExitStreak=0;
  for(const bar of future){
    observed.push(bar);
    const baseScore=scoreP25ExitV2StateConditioned({entryPrice,direction,observedBars:observed,timestamp:bar.timestamp,sessionDate:row.sessionDate,analogPool});
    const gate=decideP25ExitV3DualGate({baseScore,winnerExitStreak});winnerExitStreak=gate.winnerExitStreak;
    decisions.push(Object.freeze({timestamp:bar.timestamp,baseScore,gate}));
    if(gate.decision==='EXIT'){exit=bar;exitReason=gate.reason;break;}
  }
  const idx=future.findIndex(x=>x.timestamp===exit.timestamp),used=future.slice(0,idx+1),gross=dirRet(entryPrice,exit.close,sign),mfe=Math.max(0,...used.map(b=>dirRet(entryPrice,sign===1?b.high:b.low,sign))),mae=Math.min(0,...used.map(b=>dirRet(entryPrice,sign===1?b.low:b.high,sign)));
  return Object.freeze({exitTimestamp:exit.timestamp,exitPrice:exit.close,exitReason,barsHeld:used.length,grossReturnPct:gross,netReturnPct:gross-Number(roundTripCostPct),mfePct:mfe,maePct:mae,givebackPct:Math.max(0,mfe-gross),captureRatio:mfe>0?gross/mfe:null,policySha256:P25_EXIT_V3_DUAL_GATE_POLICY_SHA256,managementDecisions:Object.freeze(decisions),methodology:P25_EXIT_V3_INDEPENDENT_PROTOCOL,safety:P25_EXIT_V3_SAFETY});
}
export default {P25_EXIT_V3_DUAL_GATE_POLICY,P25_EXIT_V3_DUAL_GATE_POLICY_SHA256,decideP25ExitV3DualGate,simulateP25ExitV3DualGate};
