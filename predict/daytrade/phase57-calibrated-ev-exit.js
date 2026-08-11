const finite=v=>v!==null&&v!==undefined&&Number.isFinite(Number(v));
const mean=a=>a.length?a.reduce((s,v)=>s+Number(v),0)/a.length:null;
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));

export const P23_19_POLICY=Object.freeze({
  horizonBars:3,
  maxNeighbors:40,
  minNeighbors:20,
  minCalibrationRows:30,
  calibrationHalfWidth:0.10,
  betaPriorAlpha:2,
  betaPriorBeta:2,
  confidenceZ:1.645,
  exactSetup:true,
  exactDirection:true,
  priorSessionCalibrationOnly:true,
  fullyRealizedHistoricalLabelsOnly:true,
  decisionRule:'EXIT only if calibrated reversal lower-90% > 0.50 and calibrated expected next-15m directional return < 0; otherwise HOLD',
  thresholdSearchAllowed:false,
  outcomeTuningAllowed:false,
});

function stateDistance(a,b){
  const keys=['currentReturnPct','bestReturnPct','givebackPctPoints','atrPct','momentumPct','bodyPressure','directionalRangePos'];
  return Math.sqrt(keys.reduce((s,k)=>{
    const av=Number(a?.[k]),bv=Number(b?.[k]);
    const scale=(k==='bodyPressure'||k==='directionalRangePos')?1:Math.max(0.05,Math.abs(av)+Math.abs(bv));
    const d=(av-bv)/scale;
    return s+d*d;
  },0));
}

export function estimateRawExitDistribution(query,pool,policy=P23_19_POLICY){
  const rows=(pool??[]).filter(x=>{
    if(policy.exactSetup&&x.setup!==query.setup)return false;
    if(policy.exactDirection&&x.direction!==query.direction)return false;
    if(policy.fullyRealizedHistoricalLabelsOnly&&String(x.fullyRealizedAt)>=String(query.timestamp))return false;
    return x.state&&finite(x.nextDirectionalReturnPct);
  }).map(x=>({...x,d:stateDistance(query.state,x.state)})).sort((a,b)=>a.d-b.d).slice(0,policy.maxNeighbors);
  if(rows.length<policy.minNeighbors)return Object.freeze({ready:false,neighborCount:rows.length,reason:'INSUFFICIENT_CAUSAL_ANALOGS'});
  const pos=rows.filter(x=>Number(x.nextDirectionalReturnPct)>0),neg=rows.filter(x=>Number(x.nextDirectionalReturnPct)<0),flat=rows.length-pos.length-neg.length;
  const a=policy.betaPriorAlpha+pos.length,b=policy.betaPriorBeta+neg.length+flat;
  const rawPContinuation=a/(a+b);
  return Object.freeze({
    ready:true,
    neighborCount:rows.length,
    rawPContinuation,
    rawPReversal:1-rawPContinuation,
    meanContinuationReturnPct:pos.length?mean(pos.map(x=>x.nextDirectionalReturnPct)):0,
    meanReversalReturnPct:neg.length?mean(neg.map(x=>x.nextDirectionalReturnPct)):0,
    rawExpectedReturnPct:mean(rows.map(x=>x.nextDirectionalReturnPct)),
    nearestDistance:rows[0]?.d??null,
    furthestDistance:rows.at(-1)?.d??null,
    positiveCount:pos.length,
    negativeCount:neg.length,
    flatCount:flat,
  });
}

export function calibrateContinuationProbability(rawP,query,calibrationRows,policy=P23_19_POLICY){
  const eligible=(calibrationRows??[]).filter(r=>{
    if(policy.exactSetup&&r.setup!==query.setup)return false;
    if(policy.exactDirection&&r.direction!==query.direction)return false;
    if(policy.priorSessionCalibrationOnly&&String(r.sessionDate)>=String(query.sessionDate))return false;
    if(String(r.fullyRealizedAt)>=String(query.timestamp))return false;
    if(!finite(r.rawPContinuation)||![0,1].includes(Number(r.actualContinuation)))return false;
    return Math.abs(Number(r.rawPContinuation)-Number(rawP))<=policy.calibrationHalfWidth;
  });
  if(eligible.length<policy.minCalibrationRows)return Object.freeze({ready:false,count:eligible.length,reason:'INSUFFICIENT_PRIOR_CALIBRATION'});
  const successes=eligible.filter(r=>Number(r.actualContinuation)===1).length;
  const failures=eligible.length-successes;
  const alpha=policy.betaPriorAlpha+successes,beta=policy.betaPriorBeta+failures;
  const pContinuation=alpha/(alpha+beta),pReversal=1-pContinuation;
  const se=Math.sqrt(pReversal*(1-pReversal)/(alpha+beta+1));
  const lowerReversal90=clamp(pReversal-policy.confidenceZ*se,0,1);
  return Object.freeze({ready:true,count:eligible.length,pContinuation,pReversal,lowerReversal90,successes,failures});
}

export function calibratedExpectedValue(raw,cal){
  if(!raw?.ready||!cal?.ready)return null;
  return Number(cal.pContinuation)*Number(raw.meanContinuationReturnPct)+(1-Number(cal.pContinuation))*Number(raw.meanReversalReturnPct);
}

export function decideCalibratedEvExit({raw,calibration}){
  if(!raw?.ready)return Object.freeze({decision:'HOLD',ready:false,reason:raw?.reason??'RAW_NOT_READY'});
  if(!calibration?.ready)return Object.freeze({decision:'HOLD',ready:false,reason:calibration?.reason??'CALIBRATION_NOT_READY'});
  const expectedReturnPct=calibratedExpectedValue(raw,calibration);
  const exit=Number(calibration.lowerReversal90)>0.50&&Number(expectedReturnPct)<0;
  return Object.freeze({
    decision:exit?'EXIT':'HOLD',ready:true,
    reason:exit?'CALIBRATED_REVERSAL_EV_CONFIRMED':'HOLD_EDGE_NOT_BROKEN',
    expectedReturnPct,
    pContinuation:calibration.pContinuation,
    pReversal:calibration.pReversal,
    lowerReversal90:calibration.lowerReversal90,
    rawPContinuation:raw.rawPContinuation,
    calibrationCount:calibration.count,
  });
}

export function summarizeCalibration(rows=[]){
  const valid=rows.filter(r=>finite(r.pContinuation)&&[0,1].includes(Number(r.actualContinuation)));
  if(!valid.length)return {count:0,brier:null,ece:null,bins:[]};
  const brier=mean(valid.map(r=>(Number(r.pContinuation)-Number(r.actualContinuation))**2));
  const bins=[];
  for(let lo=0;lo<1;lo+=0.1){
    const hi=lo+0.1;
    const xs=valid.filter(r=>Number(r.pContinuation)>=lo&&(hi>=1?Number(r.pContinuation)<=hi:Number(r.pContinuation)<hi));
    if(xs.length)bins.push({bin:`${lo.toFixed(1)}-${hi.toFixed(1)}`,count:xs.length,meanPredicted:mean(xs.map(r=>r.pContinuation)),actualRate:mean(xs.map(r=>r.actualContinuation))});
  }
  const ece=bins.reduce((s,b)=>s+(b.count/valid.length)*Math.abs(b.meanPredicted-b.actualRate),0);
  return {count:valid.length,brier,ece,bins};
}
