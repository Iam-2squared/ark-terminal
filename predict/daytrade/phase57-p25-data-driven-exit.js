import {buildExitState} from './phase57-probabilistic-exit-reasoner.js';

export const P25_DATA_DRIVEN_EXIT_SAFETY=Object.freeze({
  phase:'57.p25.data-driven-exit.v1',mode:'CAUSAL_RESEARCH_ONLY',researchOnly:true,
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,
  transmitted:false,freshHoldoutConsumed:false,
});

export const P25_DATA_DRIVEN_EXIT_POLICY=Object.freeze({
  forecastHorizonsBars:Object.freeze([1,3,6]),
  maxNeighbors:80,minNeighbors:30,confidenceZ:1.645,
  decisionBoundaryExpectedReturnPct:0,
  decisionRule:'EXIT only when the upper 90% confidence bound of the best causal expected remaining directional return is <= 0; otherwise HOLD',
  fixedHoldMinutesUsedAsDecisionInput:false,fixedHorizonUsedAsDecisionInput:false,
  currentProspectiveOutcomeUsedForFitting:false,thresholdSearchAllowed:false,outcomeTuningAllowed:false,
});

const finite=v=>v!==null&&v!==undefined&&Number.isFinite(Number(v));
const mean=xs=>xs.length?xs.reduce((s,x)=>s+Number(x),0)/xs.length:null;
const std=xs=>{if(xs.length<2)return 0;const m=mean(xs);return Math.sqrt(xs.reduce((s,x)=>s+(Number(x)-m)**2,0)/(xs.length-1));};
const dirSign=d=>d==='LONG'||d==='UP'||d===1?1:-1;
const dirRet=(a,b,sign)=>(Number(b)/Number(a)-1)*100*sign;

function stateVector(state={}){
  return ['currentReturnPct','bestReturnPct','givebackPctPoints','atrPct','momentumPct','bodyPressure','directionalRangePos','elapsedBars'].map(k=>Number(state[k]??0));
}
function distance(a,b){
  const av=stateVector(a),bv=stateVector(b);
  return Math.sqrt(av.reduce((s,x,i)=>{const scale=i>=5&&i<=6?1:Math.max(0.05,Math.abs(x)+Math.abs(bv[i]));const d=(x-bv[i])/scale;return s+d*d;},0));
}
function normalizeBars(rows=[]){return rows.map(x=>({timestamp:new Date(Date.parse(x.timestamp??x.time)).toISOString(),open:Number(x.open),high:Number(x.high),low:Number(x.low),close:Number(x.close),volume:Number(x.volume??0)})).filter(x=>[x.open,x.high,x.low,x.close,x.volume].every(Number.isFinite)&&x.close>0).sort((a,b)=>a.timestamp.localeCompare(b.timestamp));}

export function buildP25DataDrivenExitAnalogPool({historicalSessions=[],policy=P25_DATA_DRIVEN_EXIT_POLICY}={}){
  const pool=[];
  for(const session of Array.isArray(historicalSessions)?historicalSessions:[]){
    const bars=normalizeBars(session?.bars5m??[]),sessionDate=String(session?.sessionDate??'');
    if(bars.length<12)continue;
    for(let anchor=0;anchor<bars.length-2;anchor+=1){
      const entryPrice=bars[anchor].close;
      for(const direction of ['LONG','SHORT']){
        const sign=dirSign(direction);
        for(let current=anchor+1;current<bars.length-1;current+=1){
          const observed=bars.slice(anchor+1,current+1);
          const base=buildExitState({entryPrice,direction,bars:observed});
          if(!base)continue;
          const labels={};let realizedAt=bars[current].timestamp;
          for(const h of policy.forecastHorizonsBars){
            const j=current+Number(h);if(j>=bars.length)continue;
            labels[h]=dirRet(bars[current].close,bars[j].close,sign);realizedAt=bars[j].timestamp>realizedAt?bars[j].timestamp:realizedAt;
          }
          if(!Object.keys(labels).length)continue;
          pool.push(Object.freeze({sessionDate,symbol:String(session?.symbol??''),direction,timestamp:bars[current].timestamp,fullyRealizedAt:realizedAt,state:Object.freeze({...base,elapsedBars:observed.length}),labels:Object.freeze(labels)}));
        }
      }
    }
  }
  return Object.freeze(pool);
}

export function scoreP25DataDrivenExit({entryPrice,direction,observedBars=[],timestamp,sessionDate,analogPool=[],policy=P25_DATA_DRIVEN_EXIT_POLICY}={}){
  const bars=normalizeBars(observedBars),base=buildExitState({entryPrice,direction,bars});
  if(!base)return Object.freeze({ready:false,decision:'HOLD',reason:'STATE_NOT_READY'});
  const queryState={...base,elapsedBars:bars.length},ts=String(timestamp??bars.at(-1)?.timestamp??''),sd=String(sessionDate??'');
  const eligible=(Array.isArray(analogPool)?analogPool:[]).filter(row=>row?.direction===direction&&String(row.sessionDate)<sd&&String(row.fullyRealizedAt)<ts&&row.state&&row.labels).map(row=>({...row,d:distance(queryState,row.state)})).sort((a,b)=>a.d-b.d).slice(0,policy.maxNeighbors);
  if(eligible.length<policy.minNeighbors)return Object.freeze({ready:false,decision:'HOLD',reason:'INSUFFICIENT_CAUSAL_ANALOGS',neighborCount:eligible.length,state:Object.freeze(queryState)});
  const horizonScores=[];
  for(const h of policy.forecastHorizonsBars){
    const xs=eligible.map(row=>row.labels?.[h]).filter(finite).map(Number);if(xs.length<policy.minNeighbors)continue;
    const m=mean(xs),se=std(xs)/Math.sqrt(xs.length),upper90=m+policy.confidenceZ*se,downsideProbability=xs.filter(x=>x<0).length/xs.length;
    horizonScores.push(Object.freeze({horizonBars:h,n:xs.length,expectedDirectionalReturnPct:m,standardErrorPct:se,upper90Pct:upper90,downsideProbability}));
  }
  if(!horizonScores.length)return Object.freeze({ready:false,decision:'HOLD',reason:'INSUFFICIENT_HORIZON_LABELS',neighborCount:eligible.length,state:Object.freeze(queryState)});
  const best=[...horizonScores].sort((a,b)=>b.upper90Pct-a.upper90Pct)[0];
  const exit=horizonScores.every(x=>Number(x.upper90Pct)<=policy.decisionBoundaryExpectedReturnPct);
  return Object.freeze({ready:true,decision:exit?'EXIT':'HOLD',reason:exit?'NO_POSITIVE_REMAINING_EDGE_AT_90CI':'POSITIVE_REMAINING_EDGE_NOT_REJECTED',neighborCount:eligible.length,state:Object.freeze(queryState),bestHorizonBars:best.horizonBars,bestUpper90Pct:best.upper90Pct,horizonScores:Object.freeze(horizonScores),nearestDistance:eligible[0]?.d??null,furthestDistance:eligible.at(-1)?.d??null});
}

export function simulateP25DataDrivenExit({row,analogPool,roundTripCostPct=0.05,policy=P25_DATA_DRIVEN_EXIT_POLICY}={}){
  if(row?.entryAccepted!==true||row?.frozenBeforeOutcome!==true||row?.currentOutcomeUsed!==false)throw new Error('data-driven EXIT requires outcome-free frozen Entry');
  const future=normalizeBars(row.futureBars??[]),observed=[],decisions=[];if(!future.length)throw new Error('data-driven EXIT requires sequential futureBars');
  const direction=dirSign(row.signalDirection??row.direction)===1?'LONG':'SHORT',sign=dirSign(direction),entryPrice=Number(row.entryPrice);
  let exit=future.at(-1),exitReason='SESSION_END';
  for(const bar of future){observed.push(bar);const score=scoreP25DataDrivenExit({entryPrice,direction,observedBars:observed,timestamp:bar.timestamp,sessionDate:row.sessionDate,analogPool,policy});decisions.push(Object.freeze({timestamp:bar.timestamp,...score}));if(score.ready&&score.decision==='EXIT'){exit=bar;exitReason='DATA_DRIVEN_EXPECTED_VALUE_EXIT';break;}}
  const used=future.slice(0,future.findIndex(x=>x.timestamp===exit.timestamp)+1),gross=dirRet(entryPrice,exit.close,sign),mfe=Math.max(0,...used.map(b=>dirRet(entryPrice,sign===1?b.high:b.low,sign))),mae=Math.min(0,...used.map(b=>dirRet(entryPrice,sign===1?b.low:b.high,sign)));
  return Object.freeze({exitTimestamp:exit.timestamp,exitPrice:exit.close,exitReason,barsHeld:used.length,grossReturnPct:gross,netReturnPct:gross-Number(roundTripCostPct),mfePct:mfe,maePct:mae,givebackPct:Math.max(0,mfe-gross),captureRatio:mfe>0?gross/mfe:null,managementDecisions:Object.freeze(decisions)});
}

export default {buildP25DataDrivenExitAnalogPool,scoreP25DataDrivenExit,simulateP25DataDrivenExit,P25_DATA_DRIVEN_EXIT_POLICY,P25_DATA_DRIVEN_EXIT_SAFETY};
