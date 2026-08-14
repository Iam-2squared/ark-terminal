const finite=v=>v!==null&&v!==undefined&&Number.isFinite(Number(v));
const mean=a=>a.length?a.reduce((s,v)=>s+Number(v),0)/a.length:null;
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));

export const P23_20_PROTECT_POLICY=Object.freeze({
  horizonBars:3,
  maxNeighbors:40,
  minNeighbors:20,
  downsideQuantile:0.10,
  roundTripCostPct:0.05,
  exactSetup:true,
  exactDirection:true,
  fullyRealizedHistoricalLabelsOnly:true,
  monotonicProtection:true,
  protectionRequiresPositiveAfterCostProfit:true,
  thresholdSearchAllowed:false,
  outcomeTuningAllowed:false,
  description:'HOLD/PROTECT/EXIT: EXIT uses calibrated EV; PROTECT uses causal empirical 10th-percentile downside from prior fully-realized same-setup/direction analogs and a monotonic stop; otherwise HOLD',
});

function distance(a,b){
  const keys=['currentReturnPct','bestReturnPct','givebackPctPoints','atrPct','momentumPct','bodyPressure','directionalRangePos'];
  return Math.sqrt(keys.reduce((s,k)=>{const av=Number(a?.[k]),bv=Number(b?.[k]);const scale=(k==='bodyPressure'||k==='directionalRangePos')?1:Math.max(0.05,Math.abs(av)+Math.abs(bv));const d=(av-bv)/scale;return s+d*d;},0));
}
function quantile(values,q){const a=[...values].map(Number).filter(Number.isFinite).sort((x,y)=>x-y);if(!a.length)return null;const p=(a.length-1)*clamp(q,0,1),lo=Math.floor(p),hi=Math.ceil(p);return lo===hi?a[lo]:a[lo]+(a[hi]-a[lo])*(p-lo);}

export function estimateProtectionEvidence(query,pool,policy=P23_20_PROTECT_POLICY){
  const rows=(pool??[]).filter(x=>{
    if(policy.exactSetup&&x.setup!==query.setup)return false;
    if(policy.exactDirection&&x.direction!==query.direction)return false;
    if(policy.fullyRealizedHistoricalLabelsOnly&&String(x.fullyRealizedAt)>=String(query.timestamp))return false;
    return x.state&&finite(x.nextDirectionalReturnPct);
  }).map(x=>({...x,d:distance(query.state,x.state)})).sort((a,b)=>a.d-b.d).slice(0,policy.maxNeighbors);
  if(rows.length<policy.minNeighbors)return Object.freeze({ready:false,neighborCount:rows.length,reason:'INSUFFICIENT_CAUSAL_ANALOGS'});
  const returns=rows.map(x=>Number(x.nextDirectionalReturnPct));
  return Object.freeze({ready:true,neighborCount:rows.length,q10DirectionalReturnPct:quantile(returns,policy.downsideQuantile),meanDirectionalReturnPct:mean(returns),negativeRate:returns.filter(v=>v<0).length/returns.length,nearestDistance:rows[0]?.d??null,furthestDistance:rows.at(-1)?.d??null});
}

export function deriveProtectionStop({entryPrice,currentPrice,direction,currentGrossReturnPct,priorStop,evidence},policy=P23_20_PROTECT_POLICY){
  if(!evidence?.ready)return Object.freeze({state:'HOLD',stop:priorStop??null,reason:evidence?.reason??'EVIDENCE_NOT_READY'});
  if(Number(currentGrossReturnPct)<=Number(policy.roundTripCostPct))return Object.freeze({state:'HOLD',stop:priorStop??null,reason:'PROFIT_NOT_ABOVE_COST'});
  const q10=Number(evidence.q10DirectionalReturnPct);
  if(!Number.isFinite(q10)||q10>=0)return Object.freeze({state:'HOLD',stop:priorStop??null,reason:'DOWNSIDE_QUANTILE_NOT_NEGATIVE'});
  const sign=direction==='UP'||direction==='LONG'||direction===1?1:-1;
  const empirical=currentPrice*(1+sign*q10/100);
  const breakeven=sign===1?entryPrice*(1+policy.roundTripCostPct/100):entryPrice*(1-policy.roundTripCostPct/100);
  let candidate=sign===1?Math.max(empirical,breakeven):Math.min(empirical,breakeven);
  candidate=sign===1?Math.min(candidate,currentPrice):Math.max(candidate,currentPrice);
  if(finite(priorStop))candidate=sign===1?Math.max(candidate,Number(priorStop)):Math.min(candidate,Number(priorStop));
  return Object.freeze({state:'PROTECT',stop:candidate,reason:'CAUSAL_DOWNSIDE_QUANTILE_PROTECTION',q10DirectionalReturnPct:q10,neighborCount:evidence.neighborCount,negativeRate:evidence.negativeRate});
}

export function stopFill(bar,stop,direction){if(!finite(stop))return null;const sign=direction==='UP'||direction==='LONG'||direction===1?1:-1;if(sign===1){if(bar.open<=stop)return bar.open;if(bar.low<=stop)return stop;}else{if(bar.open>=stop)return bar.open;if(bar.high>=stop)return stop;}return null;}
