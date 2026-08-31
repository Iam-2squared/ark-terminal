import crypto from 'node:crypto';
import {scoreP25ExitV2StateConditioned} from './phase57-p25-exit-v2-state-conditioned.js';
import {P25_EXIT_V3_INDEPENDENT_PROTOCOL,P25_EXIT_V3_SAFETY} from './phase57-p25-exit-v3-independent-protocol.js';

export const P25_EXIT_V4_POLICY=Object.freeze({
  candidateFamily:'STRUCTURAL_RISK_TRAJECTORY_EXIT_V4',
  inheritedAnalogCutoff:P25_EXIT_V3_INDEPENDENT_PROTOCOL.developmentCutoff,
  firstFreshEligibleDate:'2026-09-01',
  developmentEvidence:Object.freeze({
    august31PartialRole:'FAILURE_ANALYSIS_ONLY',
    august31UsedForThresholdSearch:false,
    august31UsedForCoefficientSearch:false,
    august31EligibleForV4PerformanceClaim:false,
  }),
  loserRisk:Object.freeze({
    rule:'Require causal analog edge rejection plus non-improving downside trajectory before rescue; emergency deterioration may exit on the first structurally confirmed bar.',
    upper90MaxPct:0,
    downsideProbabilityMin:0.5,
    trajectoryBars:2,
    emergencyAdverseExcursionMultiple:1.5,
  }),
  winnerProtection:Object.freeze({
    rule:'Protect only an established winner after causal edge rejection and at least half of observed MFE has been given back; require two confirmations.',
    minimumPositiveMfe:true,
    maxCaptureRatio:0.5,
    consecutiveConfirmations:2,
  }),
  neutralRisk:Object.freeze({
    rule:'Neutral state stays HOLD unless directional close deterioration persists for three consecutive managed bars.',
    consecutiveDirectionalLossBars:3,
  }),
  fixedBaselineUntouched:true,
  sameFrozenEntryAsV3:true,
  entryRetuningAllowed:false,
  universeRetuningAllowed:false,
  resultBasedRetuning:false,
  freshOutcomeUsedForFitting:false,
  promotionEligible:false,
});
const canonical=JSON.stringify(P25_EXIT_V4_POLICY);
export const P25_EXIT_V4_POLICY_SHA256=crypto.createHash('sha256').update(canonical).digest('hex');
export const P25_EXIT_V4_SAFETY=Object.freeze({...P25_EXIT_V3_SAFETY});

const signOf=d=>d==='LONG'||d==='UP'||d===1?1:-1;
const dirRet=(a,b,sign)=>(Number(b)/Number(a)-1)*100*sign;
function normalizeBars(rows=[]){return rows.map(x=>({timestamp:new Date(Date.parse(x.timestamp??x.time)).toISOString(),open:Number(x.open),high:Number(x.high),low:Number(x.low),close:Number(x.close),volume:Number(x.volume??0)})).filter(x=>[x.open,x.high,x.low,x.close,x.volume].every(Number.isFinite)&&x.close>0).sort((a,b)=>a.timestamp.localeCompare(b.timestamp));}

export function decideP25ExitV4({baseScore,currentReturnPct,mfePct,captureRatio,downsideHistory=[],neutralLossStreak=0,winnerExitStreak=0,adverseExcursionScalePct=null}={}){
  const stateBucket=String(baseScore?.stateBucket??'');
  if(!baseScore?.ready)return Object.freeze({decision:'HOLD',reason:String(baseScore?.reason??'V4_BASE_NOT_READY'),neutralLossStreak:0,winnerExitStreak:0,stateBucket});
  const h1=(baseScore?.horizonScores??[]).find(x=>Number(x?.horizonBars)===1)??null;
  const edgeRejected=Boolean(h1)&&Number(h1.upper90Pct)<=P25_EXIT_V4_POLICY.loserRisk.upper90MaxPct&&Number(h1.downsideProbability)>=P25_EXIT_V4_POLICY.loserRisk.downsideProbabilityMin;

  if(stateBucket==='LOSER_RESCUE'){
    const hist=[...downsideHistory,Number(h1?.downsideProbability)].filter(Number.isFinite);
    const last=hist.slice(-P25_EXIT_V4_POLICY.loserRisk.trajectoryBars);
    const nonImproving=last.length>=2&&last.every((v,i)=>i===0||v>=last[i-1]);
    const emergency=Number.isFinite(Number(adverseExcursionScalePct))&&Number(adverseExcursionScalePct)>0&&Number(currentReturnPct)<=-P25_EXIT_V4_POLICY.loserRisk.emergencyAdverseExcursionMultiple*Number(adverseExcursionScalePct)&&edgeRejected;
    const exit=edgeRejected&&(nonImproving||emergency);
    return Object.freeze({decision:exit?'EXIT':'HOLD',reason:exit?(emergency?'V4_EMERGENCY_STRUCTURAL_DOWNSIDE':'V4_CONFIRMED_DOWNSIDE_TRAJECTORY'):'V4_LOSER_RISK_NOT_CONFIRMED',neutralLossStreak:0,winnerExitStreak:0,stateBucket,horizon1:h1,downsideHistory:Object.freeze(hist.slice(-4))});
  }

  if(stateBucket==='WINNER_PROTECTION'){
    const protectedWinner=Number(mfePct)>0&&Number(captureRatio)<=P25_EXIT_V4_POLICY.winnerProtection.maxCaptureRatio&&Number(currentReturnPct)>0;
    const next=baseScore.decision==='EXIT'&&protectedWinner?Number(winnerExitStreak)+1:0;
    const exit=next>=P25_EXIT_V4_POLICY.winnerProtection.consecutiveConfirmations;
    return Object.freeze({decision:exit?'EXIT':'HOLD',reason:exit?'V4_WINNER_GIVEBACK_CONFIRMED':'V4_WINNER_CONTINUE',neutralLossStreak:0,winnerExitStreak:next,stateBucket,horizon1:h1});
  }

  if(stateBucket==='NEUTRAL_HOLD'){
    const next=Number(currentReturnPct)<0?Number(neutralLossStreak)+1:0;
    const exit=next>=P25_EXIT_V4_POLICY.neutralRisk.consecutiveDirectionalLossBars&&edgeRejected;
    return Object.freeze({decision:exit?'EXIT':'HOLD',reason:exit?'V4_NEUTRAL_PERSISTENT_DOWNSIDE':'V4_NEUTRAL_HOLD',neutralLossStreak:next,winnerExitStreak:0,stateBucket,horizon1:h1});
  }
  return Object.freeze({decision:'HOLD',reason:'V4_UNKNOWN_STATE_FAIL_CLOSED',neutralLossStreak:0,winnerExitStreak:0,stateBucket,horizon1:h1});
}

export function simulateP25ExitV4({row,analogPool,roundTripCostPct=0.05}={}){
  if(row?.entryAccepted!==true||row?.frozenBeforeOutcome!==true||row?.currentOutcomeUsed!==false)throw new Error('EXIT v4 requires outcome-free frozen Entry');
  const future=normalizeBars(row.futureBars??[]);if(!future.length)throw new Error('EXIT v4 requires sequential futureBars');
  const context=normalizeBars(row.contextBars??[]),direction=signOf(row.signalDirection??row.direction)===1?'LONG':'SHORT',sign=signOf(direction),entryPrice=Number(row.entryPrice);
  const ranges=context.slice(-6).map(b=>(b.high-b.low)/b.close*100).filter(Number.isFinite);
  const adverseExcursionScalePct=ranges.length?ranges.reduce((a,b)=>a+b,0)/ranges.length:null;
  const observed=[],decisions=[],downsideHistory=[];let exit=future.at(-1),exitReason='SESSION_END',winnerExitStreak=0,neutralLossStreak=0,mfe=0;
  for(const bar of future){
    observed.push(bar);
    const currentReturnPct=dirRet(entryPrice,bar.close,sign);
    const barMfe=dirRet(entryPrice,sign===1?bar.high:bar.low,sign);mfe=Math.max(mfe,barMfe);
    const captureRatio=mfe>0?currentReturnPct/mfe:null;
    const baseScore=scoreP25ExitV2StateConditioned({entryPrice,direction,observedBars:observed,timestamp:bar.timestamp,sessionDate:row.sessionDate,analogPool});
    const h1=(baseScore?.horizonScores??[]).find(x=>Number(x?.horizonBars)===1);if(Number.isFinite(Number(h1?.downsideProbability)))downsideHistory.push(Number(h1.downsideProbability));
    const gate=decideP25ExitV4({baseScore,currentReturnPct,mfePct:mfe,captureRatio,downsideHistory:downsideHistory.slice(0,-1),neutralLossStreak,winnerExitStreak,adverseExcursionScalePct});
    neutralLossStreak=gate.neutralLossStreak;winnerExitStreak=gate.winnerExitStreak;decisions.push(Object.freeze({timestamp:bar.timestamp,baseScore,gate,currentReturnPct,mfePct:mfe,captureRatio}));
    if(gate.decision==='EXIT'){exit=bar;exitReason=gate.reason;break;}
  }
  const idx=future.findIndex(x=>x.timestamp===exit.timestamp),used=future.slice(0,idx+1),gross=dirRet(entryPrice,exit.close,sign),finalMfe=Math.max(0,...used.map(b=>dirRet(entryPrice,sign===1?b.high:b.low,sign))),mae=Math.min(0,...used.map(b=>dirRet(entryPrice,sign===1?b.low:b.high,sign)));
  return Object.freeze({exitTimestamp:exit.timestamp,exitPrice:exit.close,exitReason,barsHeld:used.length,grossReturnPct:gross,netReturnPct:gross-Number(roundTripCostPct),mfePct:finalMfe,maePct:mae,givebackPct:Math.max(0,finalMfe-gross),captureRatio:finalMfe>0?gross/finalMfe:null,policySha256:P25_EXIT_V4_POLICY_SHA256,managementDecisions:Object.freeze(decisions),methodology:P25_EXIT_V4_POLICY,safety:P25_EXIT_V4_SAFETY});
}

export default {P25_EXIT_V4_POLICY,P25_EXIT_V4_POLICY_SHA256,P25_EXIT_V4_SAFETY,decideP25ExitV4,simulateP25ExitV4};
