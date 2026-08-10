import { ENTRY_OPPORTUNITY_FEATURES } from './phase57-entry-opportunity-intelligence.js';

export const PHASE57_P23_9B_SAFETY = Object.freeze({
  mode:'PHASE57_NONLINEAR_MFE_MAE_HISTORICAL_RESEARCH_ONLY',
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,
  overnightHoldingAllowed:false,humanApprovalRequired:true,
});

export const P23_9B_CONFIG = Object.freeze({
  k:64,
  minTrainRows:1200,
  roundTripCostPct:0.05,
  expectedRatchetNetFloorPct:0.02,
  winProbabilityFloor:0.55,
  opportunityProbabilityFloor:0.55,
  mfeMinusAdverseFloorPct:0.10,
  sameSessionTrainingForbidden:true,
});

const finite=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const mean=xs=>xs.length?xs.reduce((a,b)=>a+Number(b),0)/xs.length:0;
const clamp=(x,a,b)=>Math.max(a,Math.min(b,Number(x)));
const q=(xs,p)=>{const a=xs.map(Number).filter(Number.isFinite).sort((x,y)=>x-y);if(!a.length)return null;const i=(a.length-1)*p,l=Math.floor(i),h=Math.ceil(i);return l===h?a[l]:a[l]+(a[h]-a[l])*(i-l);};
const median=xs=>q(xs,0.5);

const FEATURE_WEIGHTS=Object.freeze(Object.fromEntries(ENTRY_OPPORTUNITY_FEATURES.map(key=>[key,
  key.includes('Momentum')||key.includes('ReturnFromOpen')||key.includes('Ma5Slope')?1.25:
  key.includes('rangePosition')||key.includes('Vwap')||key.includes('Ma5Distance')||key.includes('Breakout')?1.05:
  key.includes('atr')||key.includes('compression')||key.includes('Volume')?0.85:
  key.includes('minutesFromOpen')?0.70:0.75
])));

function robustScaler(rows){
  const out={};
  for(const key of ENTRY_OPPORTUNITY_FEATURES){
    const values=rows.map(r=>Number(r.features?.[key])).filter(Number.isFinite);
    if(values.length!==rows.length) throw new Error(`non-finite feature ${key}`);
    const med=median(values); const iqr=(q(values,0.75)-q(values,0.25))||1;
    out[key]={median:med,scale:Math.max(1e-9,iqr/1.349)};
  }
  return out;
}
function directionOf(row){return row?.direction===1||row?.direction==='LONG'||row?.direction==='long'?'LONG':'SHORT';}
function z(features,scaler,key){return clamp((Number(features[key])-scaler[key].median)/scaler[key].scale,-5,5);}
function distance(a,b,scaler){
  let s=0,w=0;
  for(const key of ENTRY_OPPORTUNITY_FEATURES){const wt=FEATURE_WEIGHTS[key];const d=z(a,scaler,key)-z(b,scaler,key);s+=wt*d*d;w+=wt;}
  return Math.sqrt(s/Math.max(1e-12,w));
}
function weightedMean(rows,key){let sw=0,s=0;for(const r of rows){const v=Number(r[key]),wt=Number(r._weight);if(Number.isFinite(v)&&wt>0){s+=v*wt;sw+=wt;}}return sw?s/sw:null;}
function winsorizedWeightedMean(rows,key){
  const vals=rows.map(r=>Number(r[key])).filter(Number.isFinite); if(!vals.length)return null;
  const lo=q(vals,0.10),hi=q(vals,0.90); return weightedMean(rows.map(r=>({...r,[key]:clamp(r[key],lo,hi)})),key);
}
function pearson(xs,ys){if(xs.length!==ys.length||xs.length<2)return null;const mx=mean(xs),my=mean(ys);let n=0,dx=0,dy=0;for(let i=0;i<xs.length;i++){const a=Number(xs[i])-mx,b=Number(ys[i])-my;n+=a*b;dx+=a*a;dy+=b*b;}return dx>0&&dy>0?n/Math.sqrt(dx*dy):null;}
function summarize(values){const a=values.map(Number).filter(Number.isFinite),pos=a.filter(x=>x>0).reduce((s,x)=>s+x,0),neg=-a.filter(x=>x<0).reduce((s,x)=>s+x,0);return Object.freeze({signalCount:a.length,hitRate:a.length?a.filter(x=>x>0).length/a.length:null,netAverageReturnPct:a.length?mean(a):null,profitFactor:neg>0?pos/neg:(pos>0?Infinity:null)});}

export function fitHistoricalAnalogOpportunity(rows=[],options={}){
  const config={...P23_9B_CONFIG,...options};
  const training=(Array.isArray(rows)?rows:[]).filter(r=>r?.pointInTimeFeaturesOnly===true&&r?.futureTargetsEvaluationOnly===true&&finite(r?.realizedRatchetNetReturnPct));
  if(training.length<Math.max(20,Number(config.k))) throw new Error('insufficient historical analog rows');
  const scaler=robustScaler(training);
  return Object.freeze({
    trainingCount:training.length,config:Object.freeze(config),
    predict(row){
      const dir=directionOf(row);const pool=training.filter(r=>directionOf(r)===dir);
      if(pool.length<Number(config.k)) return null;
      const neighbors=pool.map(r=>({r,d:distance(row.features,r.features,scaler)})).sort((a,b)=>a.d-b.d).slice(0,Number(config.k));
      const expanded=neighbors.map(({r,d})=>({...r,_distance:d,_weight:1/((0.20+d)*(0.20+d))}));
      const expectedMfePct=Math.max(0,winsorizedWeightedMean(expanded.map(r=>({...r,mfePct:Number(r.targets.mfePct)})),'mfePct'));
      const expectedAdversePct=Math.max(0,winsorizedWeightedMean(expanded.map(r=>({...r,adversePct:Number(r.targets.adversePct)})),'adversePct'));
      const expectedRatchetNetReturnPct=winsorizedWeightedMean(expanded,'realizedRatchetNetReturnPct');
      const sw=expanded.reduce((s,r)=>s+r._weight,0);
      const winProbability=sw?expanded.reduce((s,r)=>s+r._weight*(Number(r.realizedRatchetNetReturnPct)>0?1:0),0)/sw:0;
      const opportunityProbability=sw?expanded.reduce((s,r)=>s+r._weight*((Number(r.targets.mfePct)-Number(r.targets.adversePct)-Number(config.roundTripCostPct))>0?1:0),0)/sw:0;
      const sameSymbolWeight=sw?expanded.reduce((s,r)=>s+r._weight*(String(r.symbol)===String(row.symbol)?1:0),0)/sw:0;
      const gatePass=expectedRatchetNetReturnPct>Number(config.expectedRatchetNetFloorPct)&&
        winProbability>=Number(config.winProbabilityFloor)&&opportunityProbability>=Number(config.opportunityProbabilityFloor)&&
        (expectedMfePct-expectedAdversePct)>=Number(config.mfeMinusAdverseFloorPct);
      return Object.freeze({expectedMfePct,expectedAdversePct,expectedRatchetNetReturnPct,winProbability,opportunityProbability,
        expectedMfeMinusAdversePct:expectedMfePct-expectedAdversePct,neighborSameSymbolWeight:sameSymbolWeight,
        nearestDistance:neighbors[0]?.d??null,medianNeighborDistance:median(neighbors.map(n=>n.d)),gatePass,
        gateRule:'ANALOG_NET_GT_0_02_AND_WIN_P_GE_0_55_AND_OPPORTUNITY_P_GE_0_55_AND_MFE_MINUS_ADVERSE_GE_0_10',
        futureOutcomeUsedForPrediction:false,outerOutcomeUsedForPrediction:false});
    },
  });
}

export function evaluateNonlinearOpportunityWalkForward({trainingExamples=[],frozenTestExamples=[],config={}}={}){
  const cfg={...P23_9B_CONFIG,...config};
  const dates=[...new Set(frozenTestExamples.map(r=>String(r.sessionDate)))].sort();
  const predictions=[]; const dateDiagnostics=[];
  for(const date of dates){
    const historical=trainingExamples.filter(r=>String(r.sessionDate)<date);
    const test=frozenTestExamples.filter(r=>String(r.sessionDate)===date);
    if(historical.length<Number(cfg.minTrainRows)){dateDiagnostics.push({sessionDate:date,status:'ABSTAIN_INSUFFICIENT_PRIOR_HISTORY',priorTrainingRows:historical.length,frozenSignalCount:test.length});continue;}
    const model=fitHistoricalAnalogOpportunity(historical,cfg);
    for(const row of test){const p=model.predict(row);if(!p)continue;predictions.push(Object.freeze({symbol:row.symbol,sessionDate:row.sessionDate,featureCutoff:row.featureCutoff,direction:row.direction,...p,
      realizedMfePct:Number(row.targets.mfePct),realizedAdversePct:Number(row.targets.adversePct),realizedRatchetNetReturnPct:Number(row.realizedRatchetNetReturnPct),priorTrainingRows:historical.length}));}
    dateDiagnostics.push({sessionDate:date,status:'EVALUATED',priorTrainingRows:historical.length,frozenSignalCount:test.length});
  }
  const gated=predictions.filter(r=>r.gatePass);const all=summarize(predictions.map(r=>r.realizedRatchetNetReturnPct));const gate=summarize(gated.map(r=>r.realizedRatchetNetReturnPct));
  return Object.freeze({phase:'57.p23.9b-nonlinear-mfe-mae',status:predictions.length?'NONLINEAR_HISTORICAL_ANALOG_EVALUATED':'NO_PREDICTIONS',predictionCount:predictions.length,
    frozenTestCount:frozenTestExamples.length,evaluatedCoverage:frozenTestExamples.length?predictions.length/frozenTestExamples.length:0,gateCoverage:predictions.length?gated.length/predictions.length:0,
    allFrozenRatchet:all,gatedFrozenRatchet:gate,deltas:Object.freeze({netAverageReturnPct:gate.netAverageReturnPct==null||all.netAverageReturnPct==null?null:gate.netAverageReturnPct-all.netAverageReturnPct,
      profitFactor:finite(gate.profitFactor)&&finite(all.profitFactor)?gate.profitFactor-all.profitFactor:null,hitRate:gate.hitRate==null||all.hitRate==null?null:gate.hitRate-all.hitRate}),
    correlations:Object.freeze({expectedMfeVsRealizedMfe:pearson(predictions.map(r=>r.expectedMfePct),predictions.map(r=>r.realizedMfePct)),
      expectedAdverseVsRealizedAdverse:pearson(predictions.map(r=>r.expectedAdversePct),predictions.map(r=>r.realizedAdversePct)),
      expectedRatchetNetVsRealizedRatchetNet:pearson(predictions.map(r=>r.expectedRatchetNetReturnPct),predictions.map(r=>r.realizedRatchetNetReturnPct)),
      winProbabilityVsRealizedRatchetNet:pearson(predictions.map(r=>r.winProbability),predictions.map(r=>r.realizedRatchetNetReturnPct))}),
    diagnostics:Object.freeze({meanNeighborSameSymbolWeight:mean(predictions.map(r=>r.neighborSameSymbolWeight)),medianNeighborDistance:median(predictions.map(r=>r.medianNeighborDistance)),dateDiagnostics:Object.freeze(dateDiagnostics)}),
    predictions:Object.freeze(predictions),config:Object.freeze(cfg),integrity:Object.freeze({trainingUsesPriorSessionsOnly:true,sameSessionTrainingForbidden:true,
      futureTargetsEvaluationOnly:true,futureExtremaUsedAsFeatures:false,historicalRatchetOutcomeUsedAsLabelOnly:true,frozenEntryDirectionAndTimestampChanged:false,
      thresholdsTunedOnFrozenOuterOutcomes:false,developmentWindowReused:true,finalUntouchedOosEdgeClaimAllowed:false}),
    edgeClaimAllowed:false,recommendationAllowed:false,executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,
    liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,overnightHoldingAllowed:false,transmitted:false,safety:PHASE57_P23_9B_SAFETY});
}

export default {PHASE57_P23_9B_SAFETY,P23_9B_CONFIG,fitHistoricalAnalogOpportunity,evaluateNonlinearOpportunityWalkForward};
