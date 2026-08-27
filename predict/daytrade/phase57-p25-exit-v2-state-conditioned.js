import crypto from 'node:crypto';
import {buildExitState} from './phase57-probabilistic-exit-reasoner.js';
import {P25_EXIT_V2_INDEPENDENT_PROTOCOL,validateP25ExitV2DevelopmentDates} from './phase57-p25-exit-v2-independent-protocol.js';

export const P25_EXIT_V2_STATE_CONDITIONED_SAFETY=Object.freeze({
  phase:'57.p25.data-driven-exit.v2.state-conditioned',mode:'CAUSAL_RESEARCH_ONLY',researchOnly:true,
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,
  transmitted:false,freshHoldoutConsumed:false,
});

export const P25_EXIT_V2_STATE_CONDITIONED_POLICY=Object.freeze({
  candidateFamily:'STATE_CONDITIONED_ANALOG_EXIT',
  developmentCutoff:P25_EXIT_V2_INDEPENDENT_PROTOCOL.developmentCutoff,
  forecastHorizonsBars:Object.freeze([1,3,6]),
  maxNeighbors:80,
  minNeighbors:30,
  confidenceZ:1.645,
  decisionBoundaryExpectedReturnPct:0,
  stateBuckets:Object.freeze(['WINNER_PROTECTION','LOSER_RESCUE','NEUTRAL_HOLD']),
  stateBoundaryPct:0,
  neutralDecision:'HOLD',
  decisionRule:'Within the same causal sign-state bucket, EXIT only when every supported 1/3/6-bar upper 90% confidence bound of remaining directional return is <= 0; NEUTRAL_HOLD always HOLD.',
  exactDynamic50Only:true,
  sameFrozenEntryAsFixed:true,
  fixedHoldMinutesUsedAsDecisionInput:false,
  fixedHorizonUsedAsDecisionInput:false,
  currentProspectiveOutcomeUsedForFitting:false,
  legacy27UsedForTuning:false,
  thresholdSearchAllowed:false,
  outcomeTuningAllowed:false,
});

const canonicalPolicy=JSON.stringify(P25_EXIT_V2_STATE_CONDITIONED_POLICY);
export const P25_EXIT_V2_STATE_CONDITIONED_POLICY_SHA256=crypto.createHash('sha256').update(canonicalPolicy).digest('hex');

const finite=v=>v!==null&&v!==undefined&&Number.isFinite(Number(v));
const mean=xs=>xs.length?xs.reduce((s,x)=>s+Number(x),0)/xs.length:null;
const std=xs=>{if(xs.length<2)return 0;const m=mean(xs);return Math.sqrt(xs.reduce((s,x)=>s+(Number(x)-m)**2,0)/(xs.length-1));};
const dirSign=d=>d==='LONG'||d==='UP'||d===1?1:-1;
const dirRet=(a,b,sign)=>(Number(b)/Number(a)-1)*100*sign;

function normalizeBars(rows=[]){
  return rows.map(x=>({timestamp:new Date(Date.parse(x.timestamp??x.time)).toISOString(),open:Number(x.open),high:Number(x.high),low:Number(x.low),close:Number(x.close),volume:Number(x.volume??0)}))
    .filter(x=>[x.open,x.high,x.low,x.close,x.volume].every(Number.isFinite)&&x.close>0)
    .sort((a,b)=>a.timestamp.localeCompare(b.timestamp));
}
function stateVector(state={}){
  return ['currentReturnPct','bestReturnPct','givebackPctPoints','atrPct','momentumPct','bodyPressure','directionalRangePos','elapsedBars'].map(k=>Number(state[k]??0));
}
function distance(a,b){
  const av=stateVector(a),bv=stateVector(b);
  return Math.sqrt(av.reduce((s,x,i)=>{const scale=i>=5&&i<=6?1:Math.max(0.05,Math.abs(x)+Math.abs(bv[i]));const d=(x-bv[i])/scale;return s+d*d;},0));
}
export function classifyP25ExitV2State(state={}){
  const r=Number(state?.currentReturnPct??0);
  if(r>0)return 'WINNER_PROTECTION';
  if(r<0)return 'LOSER_RESCUE';
  return 'NEUTRAL_HOLD';
}

export function validateP25ExitV2AnalogPool(analogPool=[]){
  const rows=Array.isArray(analogPool)?analogPool:[];
  if(!rows.length)return Object.freeze({ready:false,status:'BLOCKED_V2_EMPTY_ANALOG_POOL'});
  const dates=[...new Set(rows.map(x=>String(x?.sessionDate??'')))];
  const causal=validateP25ExitV2DevelopmentDates(dates);
  if(!causal.ready)return Object.freeze({ready:false,status:causal.status});
  return Object.freeze({ready:true,status:'V2_ANALOG_POOL_CAUSAL',rowCount:rows.length,developmentDates:causal.sessionDates});
}

export function scoreP25ExitV2StateConditioned({entryPrice,direction,observedBars=[],timestamp,sessionDate,analogPool=[],policy=P25_EXIT_V2_STATE_CONDITIONED_POLICY}={}){
  const poolCheck=validateP25ExitV2AnalogPool(analogPool);
  if(!poolCheck.ready)return Object.freeze({ready:false,decision:'HOLD',reason:poolCheck.status});
  const bars=normalizeBars(observedBars),base=buildExitState({entryPrice,direction,bars});
  if(!base)return Object.freeze({ready:false,decision:'HOLD',reason:'STATE_NOT_READY'});
  const queryState={...base,elapsedBars:bars.length},stateBucket=classifyP25ExitV2State(queryState),ts=String(timestamp??bars.at(-1)?.timestamp??''),sd=String(sessionDate??'');
  if(stateBucket==='NEUTRAL_HOLD')return Object.freeze({ready:true,decision:'HOLD',reason:'NEUTRAL_STATE_FAIL_CLOSED',stateBucket,state:Object.freeze(queryState),neighborCount:0});
  const eligible=analogPool
    .filter(row=>row?.direction===direction&&String(row.sessionDate)<=policy.developmentCutoff&&String(row.sessionDate)<sd&&String(row.fullyRealizedAt)<ts&&row.state&&row.labels&&classifyP25ExitV2State(row.state)===stateBucket)
    .map(row=>({...row,d:distance(queryState,row.state)})).sort((a,b)=>a.d-b.d).slice(0,policy.maxNeighbors);
  if(eligible.length<policy.minNeighbors)return Object.freeze({ready:false,decision:'HOLD',reason:'INSUFFICIENT_STATE_CONDITIONED_CAUSAL_ANALOGS',stateBucket,neighborCount:eligible.length,state:Object.freeze(queryState)});
  const horizonScores=[];
  for(const h of policy.forecastHorizonsBars){
    const xs=eligible.map(row=>row.labels?.[h]).filter(finite).map(Number);
    if(xs.length<policy.minNeighbors)continue;
    const m=mean(xs),se=std(xs)/Math.sqrt(xs.length),upper90=m+policy.confidenceZ*se,downsideProbability=xs.filter(x=>x<0).length/xs.length;
    horizonScores.push(Object.freeze({horizonBars:h,n:xs.length,expectedDirectionalReturnPct:m,standardErrorPct:se,upper90Pct:upper90,downsideProbability}));
  }
  if(!horizonScores.length)return Object.freeze({ready:false,decision:'HOLD',reason:'INSUFFICIENT_STATE_CONDITIONED_HORIZON_LABELS',stateBucket,neighborCount:eligible.length,state:Object.freeze(queryState)});
  const best=[...horizonScores].sort((a,b)=>b.upper90Pct-a.upper90Pct)[0];
  const exit=horizonScores.every(x=>Number(x.upper90Pct)<=policy.decisionBoundaryExpectedReturnPct);
  return Object.freeze({ready:true,decision:exit?'EXIT':'HOLD',reason:exit?'NO_POSITIVE_STATE_CONDITIONED_REMAINING_EDGE_AT_90CI':'POSITIVE_STATE_CONDITIONED_REMAINING_EDGE_NOT_REJECTED',stateBucket,neighborCount:eligible.length,state:Object.freeze(queryState),bestHorizonBars:best.horizonBars,bestUpper90Pct:best.upper90Pct,horizonScores:Object.freeze(horizonScores),nearestDistance:eligible[0]?.d??null,furthestDistance:eligible.at(-1)?.d??null,policySha256:P25_EXIT_V2_STATE_CONDITIONED_POLICY_SHA256});
}

export function simulateP25ExitV2StateConditioned({row,analogPool,roundTripCostPct=0.05,policy=P25_EXIT_V2_STATE_CONDITIONED_POLICY}={}){
  if(row?.entryAccepted!==true||row?.frozenBeforeOutcome!==true||row?.currentOutcomeUsed!==false)throw new Error('EXIT v2 requires outcome-free frozen Entry');
  const future=normalizeBars(row.futureBars??[]),observed=[],decisions=[];
  if(!future.length)throw new Error('EXIT v2 requires sequential futureBars');
  const direction=dirSign(row.signalDirection??row.direction)===1?'LONG':'SHORT',sign=dirSign(direction),entryPrice=Number(row.entryPrice);
  let exit=future.at(-1),exitReason='SESSION_END';
  for(const bar of future){
    observed.push(bar);
    const score=scoreP25ExitV2StateConditioned({entryPrice,direction,observedBars:observed,timestamp:bar.timestamp,sessionDate:row.sessionDate,analogPool,policy});
    decisions.push(Object.freeze({timestamp:bar.timestamp,...score}));
    if(score.ready&&score.decision==='EXIT'){exit=bar;exitReason=`V2_${score.stateBucket}_EXPECTED_VALUE_EXIT`;break;}
  }
  const used=future.slice(0,future.findIndex(x=>x.timestamp===exit.timestamp)+1),gross=dirRet(entryPrice,exit.close,sign),mfe=Math.max(0,...used.map(b=>dirRet(entryPrice,sign===1?b.high:b.low,sign))),mae=Math.min(0,...used.map(b=>dirRet(entryPrice,sign===1?b.low:b.high,sign)));
  return Object.freeze({exitTimestamp:exit.timestamp,exitPrice:exit.close,exitReason,barsHeld:used.length,grossReturnPct:gross,netReturnPct:gross-Number(roundTripCostPct),mfePct:mfe,maePct:mae,givebackPct:Math.max(0,mfe-gross),captureRatio:mfe>0?gross/mfe:null,policySha256:P25_EXIT_V2_STATE_CONDITIONED_POLICY_SHA256,managementDecisions:Object.freeze(decisions)});
}

export default {classifyP25ExitV2State,validateP25ExitV2AnalogPool,scoreP25ExitV2StateConditioned,simulateP25ExitV2StateConditioned,P25_EXIT_V2_STATE_CONDITIONED_POLICY,P25_EXIT_V2_STATE_CONDITIONED_POLICY_SHA256,P25_EXIT_V2_STATE_CONDITIONED_SAFETY};