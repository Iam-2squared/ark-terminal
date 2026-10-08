import {buildExitState} from './phase57-probabilistic-exit-reasoner.js';
import {
  P25_EXIT_V2_STATE_CONDITIONED_POLICY,
  P25_EXIT_V2_STATE_CONDITIONED_POLICY_SHA256,
  classifyP25ExitV2State,
  validateP25ExitV2AnalogPool,
} from './phase57-p25-exit-v2-state-conditioned.js';
import {P25_EXIT_V4_POLICY,P25_EXIT_V4_POLICY_SHA256,P25_EXIT_V4_SAFETY,decideP25ExitV4} from './phase57-p25-exit-v4-structural-risk.js';

export const PHASE57_EXIT_V4_INDEXED_REPLAY_CONTRACT=Object.freeze({
  executionSemantics:'EXACT_TOP_K_REPLAY',
  approximateNearestNeighbors:false,
  analogSubsampling:false,
  policyRetuning:false,
  outcomeTuning:false,
  requiredEvaluationDateAfterDevelopmentCutoff:true,
  originalStableTieBreakPreserved:true,
  policySha256:P25_EXIT_V4_POLICY_SHA256,
});

const finite=value=>value!==null&&value!==undefined&&Number.isFinite(Number(value));
const mean=xs=>xs.length?xs.reduce((s,x)=>s+Number(x),0)/xs.length:null;
const std=xs=>{if(xs.length<2)return 0;const m=mean(xs);return Math.sqrt(xs.reduce((s,x)=>s+(Number(x)-m)**2,0)/(xs.length-1));};
const signOf=d=>d==='LONG'||d==='UP'||d===1?1:-1;
const dirRet=(a,b,sign)=>(Number(b)/Number(a)-1)*100*sign;
const vector=state=>['currentReturnPct','bestReturnPct','givebackPctPoints','atrPct','momentumPct','bodyPressure','directionalRangePos','elapsedBars'].map(key=>Number(state?.[key]??0));
function normalizeBars(rows=[]){return rows.map(row=>({timestamp:new Date(Date.parse(row.timestamp??row.time)).toISOString(),open:Number(row.open),high:Number(row.high),low:Number(row.low),close:Number(row.close),volume:Number(row.volume??0)})).filter(row=>[row.open,row.high,row.low,row.close,row.volume].every(Number.isFinite)&&row.close>0).sort((a,b)=>a.timestamp.localeCompare(b.timestamp));}

function distanceSquared(query,candidate){
  let sum=0;
  for(let i=0;i<query.length;i+=1){
    const scale=i>=5&&i<=6?1:Math.max(0.05,Math.abs(query[i])+Math.abs(candidate[i]));
    const delta=(query[i]-candidate[i])/scale;
    sum+=delta*delta;
  }
  return sum;
}
const worse=(a,b)=>a.d2>b.d2||(a.d2===b.d2&&a.originalIndex>b.originalIndex);
const better=(a,b)=>a.d2<b.d2||(a.d2===b.d2&&a.originalIndex<b.originalIndex);
function heapPushTopK(heap,item,k){
  if(heap.length<k){
    heap.push(item);
    let i=heap.length-1;
    while(i>0){const p=(i-1)>>1;if(!worse(heap[i],heap[p]))break;[heap[i],heap[p]]=[heap[p],heap[i]];i=p;}
    return;
  }
  if(!better(item,heap[0]))return;
  heap[0]=item;
  let i=0;
  while(true){
    const left=i*2+1,right=left+1;
    if(left>=heap.length)break;
    let child=left;
    if(right<heap.length&&worse(heap[right],heap[left]))child=right;
    if(!worse(heap[child],heap[i]))break;
    [heap[i],heap[child]]=[heap[child],heap[i]];i=child;
  }
}

export function buildExactExitV4AnalogIndex(analogPool=[]){
  const validation=validateP25ExitV2AnalogPool(analogPool);
  if(!validation.ready)throw new Error(validation.status);
  const buckets={LONG:{WINNER_PROTECTION:[],LOSER_RESCUE:[]},SHORT:{WINNER_PROTECTION:[],LOSER_RESCUE:[]}};
  let latestFullyRealizedAt='';
  for(let originalIndex=0;originalIndex<analogPool.length;originalIndex+=1){
    const row=analogPool[originalIndex];
    if(!row?.state||!row?.labels||String(row.sessionDate)>P25_EXIT_V2_STATE_CONDITIONED_POLICY.developmentCutoff)continue;
    const direction=row.direction==='LONG'?'LONG':row.direction==='SHORT'?'SHORT':null,bucket=classifyP25ExitV2State(row.state);
    if(!direction||!buckets[direction][bucket])continue;
    latestFullyRealizedAt=String(row.fullyRealizedAt)>latestFullyRealizedAt?String(row.fullyRealizedAt):latestFullyRealizedAt;
    buckets[direction][bucket].push(Object.freeze({row,originalIndex,stateVector:Object.freeze(vector(row.state))}));
  }
  return Object.freeze({ready:true,status:'EXACT_V4_ANALOG_INDEX_READY',rowCount:analogPool.length,latestFullyRealizedAt,buckets:Object.freeze({LONG:Object.freeze(buckets.LONG),SHORT:Object.freeze(buckets.SHORT)}),validation,contract:PHASE57_EXIT_V4_INDEXED_REPLAY_CONTRACT});
}

export function scoreP25ExitV2ExactIndexed({entryPrice,direction,observedBars=[],timestamp,sessionDate,index,policy=P25_EXIT_V2_STATE_CONDITIONED_POLICY}={}){
  if(!index?.ready)throw new Error('exact indexed scorer requires a ready index');
  const bars=normalizeBars(observedBars),base=buildExitState({entryPrice,direction,bars});
  if(!base)return Object.freeze({ready:false,decision:'HOLD',reason:'STATE_NOT_READY'});
  const queryState={...base,elapsedBars:bars.length},stateBucket=classifyP25ExitV2State(queryState),ts=String(timestamp??bars.at(-1)?.timestamp??''),sd=String(sessionDate??'');
  if(sd<=policy.developmentCutoff||ts<=index.latestFullyRealizedAt)throw new Error('indexed replay is only exact after the complete frozen development pool is causal');
  if(stateBucket==='NEUTRAL_HOLD')return Object.freeze({ready:true,decision:'HOLD',reason:'NEUTRAL_STATE_FAIL_CLOSED',stateBucket,state:Object.freeze(queryState),neighborCount:0});
  const candidates=index.buckets?.[direction]?.[stateBucket]??[],queryVector=vector(queryState),heap=[];
  for(const candidate of candidates)heapPushTopK(heap,{...candidate,d2:distanceSquared(queryVector,candidate.stateVector)},policy.maxNeighbors);
  const eligible=heap.sort((a,b)=>a.d2-b.d2||a.originalIndex-b.originalIndex);
  if(eligible.length<policy.minNeighbors)return Object.freeze({ready:false,decision:'HOLD',reason:'INSUFFICIENT_STATE_CONDITIONED_CAUSAL_ANALOGS',stateBucket,neighborCount:eligible.length,state:Object.freeze(queryState)});
  const horizonScores=[];
  for(const h of policy.forecastHorizonsBars){
    const xs=eligible.map(item=>item.row.labels?.[h]).filter(finite).map(Number);
    if(xs.length<policy.minNeighbors)continue;
    const m=mean(xs),se=std(xs)/Math.sqrt(xs.length),upper90=m+policy.confidenceZ*se,downsideProbability=xs.filter(x=>x<0).length/xs.length;
    horizonScores.push(Object.freeze({horizonBars:h,n:xs.length,expectedDirectionalReturnPct:m,standardErrorPct:se,upper90Pct:upper90,downsideProbability}));
  }
  if(!horizonScores.length)return Object.freeze({ready:false,decision:'HOLD',reason:'INSUFFICIENT_STATE_CONDITIONED_HORIZON_LABELS',stateBucket,neighborCount:eligible.length,state:Object.freeze(queryState)});
  const best=[...horizonScores].sort((a,b)=>b.upper90Pct-a.upper90Pct)[0],exit=horizonScores.every(x=>Number(x.upper90Pct)<=policy.decisionBoundaryExpectedReturnPct);
  return Object.freeze({ready:true,decision:exit?'EXIT':'HOLD',reason:exit?'NO_POSITIVE_STATE_CONDITIONED_REMAINING_EDGE_AT_90CI':'POSITIVE_STATE_CONDITIONED_REMAINING_EDGE_NOT_REJECTED',stateBucket,neighborCount:eligible.length,state:Object.freeze(queryState),bestHorizonBars:best.horizonBars,bestUpper90Pct:best.upper90Pct,horizonScores:Object.freeze(horizonScores),nearestDistance:Math.sqrt(eligible[0].d2),furthestDistance:Math.sqrt(eligible.at(-1).d2),policySha256:P25_EXIT_V2_STATE_CONDITIONED_POLICY_SHA256});
}

export function simulateP25ExitV4ExactIndexed({row,index,roundTripCostPct=0.05}={}){
  if(row?.entryAccepted!==true||row?.frozenBeforeOutcome!==true||row?.currentOutcomeUsed!==false)throw new Error('EXIT v4 requires outcome-free frozen Entry');
  const future=normalizeBars(row.futureBars??[]);if(!future.length)throw new Error('EXIT v4 requires sequential futureBars');
  const context=normalizeBars(row.contextBars??[]),direction=signOf(row.signalDirection??row.direction)===1?'LONG':'SHORT',sign=signOf(direction),entryPrice=Number(row.entryPrice);
  const ranges=context.slice(-6).map(b=>(b.high-b.low)/b.close*100).filter(Number.isFinite),adverseExcursionScalePct=ranges.length?ranges.reduce((a,b)=>a+b,0)/ranges.length:null;
  const observed=[],decisions=[],downsideHistory=[];let exit=future.at(-1),exitReason='SESSION_END',winnerExitStreak=0,neutralLossStreak=0,mfe=0;
  for(const bar of future){
    observed.push(bar);const currentReturnPct=dirRet(entryPrice,bar.close,sign),barMfe=dirRet(entryPrice,sign===1?bar.high:bar.low,sign);mfe=Math.max(mfe,barMfe);const captureRatio=mfe>0?currentReturnPct/mfe:null;
    const baseScore=scoreP25ExitV2ExactIndexed({entryPrice,direction,observedBars:observed,timestamp:bar.timestamp,sessionDate:row.sessionDate,index});
    const h1=(baseScore?.horizonScores??[]).find(x=>Number(x?.horizonBars)===1);if(Number.isFinite(Number(h1?.downsideProbability)))downsideHistory.push(Number(h1.downsideProbability));
    const gate=decideP25ExitV4({baseScore,currentReturnPct,mfePct:mfe,captureRatio,downsideHistory:downsideHistory.slice(0,-1),neutralLossStreak,winnerExitStreak,adverseExcursionScalePct});neutralLossStreak=gate.neutralLossStreak;winnerExitStreak=gate.winnerExitStreak;
    decisions.push(Object.freeze({timestamp:bar.timestamp,baseScore,gate,currentReturnPct,mfePct:mfe,captureRatio}));if(gate.decision==='EXIT'){exit=bar;exitReason=gate.reason;break;}
  }
  const idx=future.findIndex(x=>x.timestamp===exit.timestamp),used=future.slice(0,idx+1),gross=dirRet(entryPrice,exit.close,sign),finalMfe=Math.max(0,...used.map(b=>dirRet(entryPrice,sign===1?b.high:b.low,sign))),mae=Math.min(0,...used.map(b=>dirRet(entryPrice,sign===1?b.low:b.high,sign)));
  return Object.freeze({exitTimestamp:exit.timestamp,exitPrice:exit.close,exitReason,barsHeld:used.length,grossReturnPct:gross,netReturnPct:gross-Number(roundTripCostPct),mfePct:finalMfe,maePct:mae,givebackPct:Math.max(0,finalMfe-gross),captureRatio:finalMfe>0?gross/finalMfe:null,policySha256:P25_EXIT_V4_POLICY_SHA256,managementDecisions:Object.freeze(decisions),methodology:P25_EXIT_V4_POLICY,safety:P25_EXIT_V4_SAFETY,indexedReplay:PHASE57_EXIT_V4_INDEXED_REPLAY_CONTRACT});
}

export default {buildExactExitV4AnalogIndex,scoreP25ExitV2ExactIndexed,simulateP25ExitV4ExactIndexed,PHASE57_EXIT_V4_INDEXED_REPLAY_CONTRACT};
