const finite=v=>v!==null&&v!==undefined&&Number.isFinite(Number(v));
const mean=a=>a.length?a.reduce((s,v)=>s+Number(v),0)/a.length:null;
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));

export const P23_18_EXIT_EVIDENCE_POLICY=Object.freeze({
  horizonBars:3,
  maxNeighbors:40,
  minNeighbors:20,
  betaPriorAlpha:1,
  betaPriorBeta:1,
  confidenceZ:1.645,
  requireExactSetup:true,
  requireExactDirection:true,
  requirePriorSession:true,
  requireFullyRealizedBeforeDecision:true,
  decisionRule:'EXIT only when lower 90% bound of reversal probability > 0.50 AND analog expected next-15m directional return < 0',
  thresholdSearchAllowed:false,
  outcomeTuningAllowed:false,
});

function tr(b,p){return Math.max(b.high-b.low,Math.abs(b.high-p),Math.abs(b.low-p));}
function atr(bars,n=8){if(!bars.length)return null;const x=bars.map((b,i)=>tr(b,i?bars[i-1].close:b.open));return mean(x.slice(-Math.max(2,n)));}
function dirRet(a,b,sign){return (Number(b)/Number(a)-1)*100*sign;}

export function buildExitState({entryPrice,direction,bars}){
  if(!bars?.length||!finite(entryPrice))return null;
  const sign=direction==='UP'||direction==='LONG'||direction===1?1:-1;
  const last=bars.at(-1),recent=bars.slice(-4);
  const best=sign===1?Math.max(entryPrice,...bars.map(b=>b.high)):Math.min(entryPrice,...bars.map(b=>b.low));
  const currentReturn=dirRet(entryPrice,last.close,sign);
  const bestReturn=Math.max(0,dirRet(entryPrice,best,sign));
  const a=atr(bars,8)??entryPrice*0.005;
  const momentum=recent.length>1?dirRet(recent[0].close,last.close,sign):0;
  const bodyPressure=((last.close-last.open)/Math.max(1e-12,last.high-last.low))*sign;
  const range=bars.slice(-12),hi=Math.max(...range.map(b=>b.high)),lo=Math.min(...range.map(b=>b.low));
  const pos=hi>lo?(last.close-lo)/(hi-lo):0.5;
  return Object.freeze({currentReturnPct:currentReturn,bestReturnPct:bestReturn,givebackPctPoints:Math.max(0,bestReturn-currentReturn),atrPct:a/entryPrice*100,momentumPct:momentum,bodyPressure,directionalRangePos:sign===1?pos:1-pos});
}

function distance(a,b){const keys=['currentReturnPct','bestReturnPct','givebackPctPoints','atrPct','momentumPct','bodyPressure','directionalRangePos'];return Math.sqrt(keys.reduce((s,k)=>{const scale=k==='bodyPressure'||k==='directionalRangePos'?1:Math.max(0.05,Math.abs(Number(a[k]))+Math.abs(Number(b[k])));const d=(Number(a[k])-Number(b[k]))/scale;return s+d*d;},0));}

export function estimateExitEvidence(query,pool,policy=P23_18_EXIT_EVIDENCE_POLICY){
  const candidates=(pool??[]).filter(x=>{
    if(policy.requireExactSetup&&x.setup!==query.setup)return false;
    if(policy.requireExactDirection&&x.direction!==query.direction)return false;
    if(policy.requirePriorSession&&x.sessionDate===query.sessionDate)return false;
    if(policy.requireFullyRealizedBeforeDecision&&String(x.fullyRealizedAt)>=String(query.timestamp))return false;
    return x.state&&finite(x.nextDirectionalReturnPct);
  }).map(x=>({...x,d:distance(query.state,x.state)})).sort((a,b)=>a.d-b.d).slice(0,policy.maxNeighbors);
  if(candidates.length<policy.minNeighbors)return Object.freeze({ready:false,neighborCount:candidates.length,reason:'INSUFFICIENT_CAUSAL_ANALOGS'});
  const n=candidates.length,reversals=candidates.filter(x=>Number(x.nextDirectionalReturnPct)<0).length,continuations=n-reversals;
  const alpha=policy.betaPriorAlpha+reversals,beta=policy.betaPriorBeta+continuations;
  const pReversal=alpha/(alpha+beta),pContinuation=1-pReversal,se=Math.sqrt(pReversal*(1-pReversal)/(alpha+beta+1));
  const lowerReversal=clamp(pReversal-policy.confidenceZ*se,0,1),expectedNextDirectionalReturnPct=mean(candidates.map(x=>x.nextDirectionalReturnPct));
  const exit=lowerReversal>0.5&&expectedNextDirectionalReturnPct<0;
  return Object.freeze({ready:true,neighborCount:n,pReversal,pContinuation,lowerReversal90:lowerReversal,expectedNextDirectionalReturnPct,decision:exit?'EXIT':'HOLD',reason:exit?'REVERSAL_PROBABILITY_CONFIRMED':'REVERSAL_NOT_CONFIRMED',evidenceSummary:{reversals,continuations,nearestDistance:candidates[0]?.d??null,furthestDistance:candidates.at(-1)?.d??null}});
}

export function summarizeProbabilityCalibration(rows=[]){
  const valid=rows.filter(r=>finite(r.pContinuation)&&[0,1].includes(Number(r.actualContinuation)));
  if(!valid.length)return {count:0,brier:null,calibration:[]};
  const brier=mean(valid.map(r=>(Number(r.pContinuation)-Number(r.actualContinuation))**2)),bins=[];
  for(let lo=0;lo<1;lo+=0.1){const hi=lo+0.1,xs=valid.filter(r=>Number(r.pContinuation)>=lo&&(hi>=1?Number(r.pContinuation)<=hi:Number(r.pContinuation)<hi));if(xs.length)bins.push({bin:`${lo.toFixed(1)}-${hi.toFixed(1)}`,count:xs.length,meanPredicted:mean(xs.map(r=>r.pContinuation)),actualRate:mean(xs.map(r=>r.actualContinuation))});}
  return {count:valid.length,brier,calibration:bins};
}
