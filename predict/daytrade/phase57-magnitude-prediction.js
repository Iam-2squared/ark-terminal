import { evaluateNestedAdaptiveHorizon } from './phase57-nested-adaptive-horizon.js';

export const PHASE57_P21_2_SAFETY=Object.freeze({
  mode:'PHASE57_MAGNITUDE_PREDICTION_RESEARCH_ONLY',
  executionAllowed:false,
  brokerWriteAllowed:false,
  excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,
  paperTradingAllowed:false,
  automaticPromotionAllowed:false,
  productionUpdateAllowed:false,
  overnightHoldingAllowed:false,
  humanApprovalRequired:true,
});

export const DEFAULT_MOVE_THRESHOLDS_PCT=Object.freeze([0.5,1,2,3]);
const finite=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));

function validTarget(row){
  return row?.pointInTimeValid!==false&&row?.featureCutoff&&row?.outcomeAt&&
    Date.parse(row.featureCutoff)<Date.parse(row.outcomeAt)&&
    (!row?.outcomeSessionDate||row.outcomeSessionDate===row.sessionDate)&&
    finite(row?.actualReturnPct)&&finite(row?.absMovePct)&&finite(row?.mfePct)&&finite(row?.maePct);
}

function numericFeatureKeys(rows){
  const keys=new Set();
  for(const row of rows) for(const [key,value] of Object.entries(row?.features??{})) if(finite(value)) keys.add(key);
  return [...keys].sort();
}

function mean(values){return values.length?values.reduce((s,x)=>s+x,0)/values.length:null;}

function statsForFeatures(rows,keys){
  const out={};
  for(const key of keys){
    const values=rows.map(row=>Number(row?.features?.[key])).filter(Number.isFinite);
    const m=mean(values)??0;
    const variance=values.length?values.reduce((s,x)=>s+(x-m)**2,0)/values.length:0;
    out[key]={mean:m,std:Math.sqrt(variance)||1};
  }
  return out;
}

function vector(row,keys,stats){
  return keys.map(key=>{
    const value=Number(row?.features?.[key]);
    return Number.isFinite(value)?(value-stats[key].mean)/stats[key].std:0;
  });
}

function distanceSquared(a,b){
  let d=0;
  for(let i=0;i<a.length;i++) d+=(a[i]-b[i])**2;
  return d;
}

function weightedMean(neighbors,getter){
  let numerator=0,denominator=0;
  for(const n of neighbors){
    const value=Number(getter(n.row));
    if(!Number.isFinite(value)) continue;
    numerator+=value*n.weight;
    denominator+=n.weight;
  }
  return denominator?numerator/denominator:null;
}

export function fitMagnitudePredictor(trainRows=[],{
  k=25,
  featureKeys=null,
  moveThresholdsPct=DEFAULT_MOVE_THRESHOLDS_PCT,
}={}){
  const rows=(Array.isArray(trainRows)?trainRows:[]).filter(validTarget);
  if(!rows.length) return null;
  const keys=Array.isArray(featureKeys)?featureKeys:numericFeatureKeys(rows);
  const stats=statsForFeatures(rows,keys);
  const stored=rows.map(row=>({row,vector:vector(row,keys,stats)}));
  const neighborCount=Math.max(1,Math.min(Number(k)||25,stored.length));
  const thresholds=[...new Set(moveThresholdsPct.map(Number).filter(x=>Number.isFinite(x)&&x>0))].sort((a,b)=>a-b);

  const predict=row=>{
    const query=vector(row,keys,stats);
    let nearest;
    if(!keys.length){
      nearest=stored.map(item=>({row:item.row,weight:1}));
    }else{
      nearest=stored
        .map(item=>({row:item.row,distance:distanceSquared(query,item.vector)}))
        .sort((a,b)=>a.distance-b.distance)
        .slice(0,neighborCount)
        .map(item=>({...item,weight:1/(Math.sqrt(item.distance)+0.05)}));
    }
    const probabilityMoveGtPct=Object.fromEntries(thresholds.map(threshold=>[
      String(threshold),
      weightedMean(nearest,r=>Number(r.absMovePct)>=threshold?1:0),
    ]));
    return Object.freeze({
      expectedReturnPct:weightedMean(nearest,r=>r.actualReturnPct),
      expectedAbsMovePct:weightedMean(nearest,r=>r.absMovePct),
      expectedMfePct:weightedMean(nearest,r=>r.mfePct),
      expectedMaePct:weightedMean(nearest,r=>r.maePct),
      probabilityMoveGtPct:Object.freeze(probabilityMoveGtPct),
      neighborCount:nearest.length,
      featureCount:keys.length,
    });
  };

  return Object.freeze({
    predict,
    trainRows:rows.length,
    featureKeys:Object.freeze(keys),
    k:keys.length?neighborCount:rows.length,
    moveThresholdsPct:Object.freeze(thresholds),
    fitSource:'PRE_OUTER_TRAIN_ONLY',
  });
}

function brier(pairs){
  return pairs.length?pairs.reduce((s,x)=>s+(x.predicted-x.actual)**2,0)/pairs.length:null;
}

function evaluatePredictions(records,thresholds){
  const returnErrors=[],absErrors=[],mfeErrors=[],maeErrors=[];
  const thresholdPairs=Object.fromEntries(thresholds.map(t=>[String(t),[]]));
  for(const record of records){
    const {prediction,row}=record;
    if(finite(prediction.expectedReturnPct)) returnErrors.push(Math.abs(prediction.expectedReturnPct-Number(row.actualReturnPct)));
    if(finite(prediction.expectedAbsMovePct)) absErrors.push(Math.abs(prediction.expectedAbsMovePct-Number(row.absMovePct)));
    if(finite(prediction.expectedMfePct)) mfeErrors.push(Math.abs(prediction.expectedMfePct-Number(row.mfePct)));
    if(finite(prediction.expectedMaePct)) maeErrors.push(Math.abs(prediction.expectedMaePct-Number(row.maePct)));
    for(const t of thresholds){
      const predicted=Number(prediction.probabilityMoveGtPct[String(t)]);
      if(Number.isFinite(predicted)) thresholdPairs[String(t)].push({predicted,actual:Number(row.absMovePct)>=t?1:0});
    }
  }
  return Object.freeze({
    sampleCount:records.length,
    expectedReturnMaePct:mean(returnErrors),
    expectedAbsMoveMaePct:mean(absErrors),
    expectedMfeMaePct:mean(mfeErrors),
    expectedMaeMaePct:mean(maeErrors),
    probabilityBrierByThreshold:Object.freeze(Object.fromEntries(thresholds.map(t=>[String(t),brier(thresholdPairs[String(t)])]))),
    actualMoveRateByThreshold:Object.freeze(Object.fromEntries(thresholds.map(t=>[String(t),mean(thresholdPairs[String(t)].map(x=>x.actual))]))),
    predictedMoveRateByThreshold:Object.freeze(Object.fromEntries(thresholds.map(t=>[String(t),mean(thresholdPairs[String(t)].map(x=>x.predicted))]))),
  });
}

function normalizeMap(input={}){
  const entries=input instanceof Map?[...input.entries()]:Object.entries(input??{});
  return new Map(entries.map(([h,rows])=>[Number(h),(Array.isArray(rows)?rows:[]).filter(validTarget)]).filter(([h,rows])=>Number.isInteger(h)&&h>0&&rows.length));
}

export function evaluateNestedMagnitudePrediction(horizonRowsByBars={},options={}){
  const thresholds=[...new Set((options.moveThresholdsPct??DEFAULT_MOVE_THRESHOLDS_PCT).map(Number).filter(x=>Number.isFinite(x)&&x>0))].sort((a,b)=>a-b);
  const adaptive=options.adaptiveResult??evaluateNestedAdaptiveHorizon(horizonRowsByBars,options.adaptiveOptions??options);
  const map=normalizeMap(horizonRowsByBars);
  const foldResults=[];
  const records=[];

  for(const fold of adaptive?.outerResults??[]){
    if(fold?.status!=='OUTER_EVALUATED'||!Number.isInteger(Number(fold.selectedHorizonBars))) continue;
    const horizonBars=Number(fold.selectedHorizonBars);
    const rows=map.get(horizonBars)??[];
    const train=rows.filter(row=>Date.parse(row.featureCutoff)<Date.parse(fold.testStart)&&Date.parse(row.outcomeAt)<=Date.parse(fold.trainCutoff));
    const test=rows.filter(row=>Date.parse(row.featureCutoff)>=Date.parse(fold.testStart)&&Date.parse(row.featureCutoff)<=Date.parse(fold.testEnd));
    const model=fitMagnitudePredictor(train,{k:options.k??25,featureKeys:options.featureKeys??null,moveThresholdsPct:thresholds});
    if(!model||!test.length){
      foldResults.push(Object.freeze({fold:fold.fold,status:'ABSTAIN_INSUFFICIENT_MAGNITUDE_DATA',selectedHorizonBars:horizonBars,outerUntouchedByFit:true}));
      continue;
    }
    const foldRecords=test.map(row=>Object.freeze({row,prediction:model.predict(row)}));
    records.push(...foldRecords);
    const metrics=evaluatePredictions(foldRecords,thresholds);
    foldResults.push(Object.freeze({
      fold:fold.fold,status:'MAGNITUDE_OUTER_EVALUATED',selectedHorizonBars:horizonBars,
      trainRows:model.trainRows,testRows:test.length,featureCount:model.featureKeys.length,k:model.k,
      ...metrics,outerUntouchedByFit:true,outerUntouchedByMagnitudeCalibration:true,
    }));
  }

  const metrics=evaluatePredictions(records,thresholds);
  return Object.freeze({
    phase:'57.p21.2',
    status:records.length?'NESTED_MAGNITUDE_OOS_READY':'NO_MAGNITUDE_OOS_PREDICTIONS',
    moveThresholdsPct:Object.freeze(thresholds),
    adaptiveHorizonStatus:adaptive?.status??null,
    foldResults:Object.freeze(foldResults),
    ...metrics,
    selectionIntegrity:Object.freeze({
      adaptiveHorizonSelectedBeforeMagnitudeOuterEvaluation:true,
      magnitudeFitUsesPreOuterRowsOnly:true,
      magnitudeCalibrationUsesPreOuterRowsOnly:true,
      outerTestNeverUsedForMagnitudeFit:true,
      sameSessionOnly:true,
      overnightHoldingForbidden:true,
    }),
    recommendationAllowed:false,paperTradingAllowed:false,executionAllowed:false,brokerWriteAllowed:false,
    excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,
    automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,humanApprovalRequired:true,
    safety:PHASE57_P21_2_SAFETY,
  });
}

export default {fitMagnitudePredictor,evaluateNestedMagnitudePrediction};
