import { buildIntradayWalkForwardFolds } from './phase57-intraday-walkforward-cost.js';
import { selectInnerAdaptiveHorizon } from './phase57-nested-adaptive-horizon.js';
import { trainModel } from '../models/phase47-real-training.js';

export const PHASE57_P21_3_SIGNAL_REPLAY_SAFETY=Object.freeze({
  mode:'PHASE57_ADAPTIVE_OOS_SIGNAL_REPLAY_RESEARCH_ONLY',
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,
  overnightHoldingAllowed:false,humanApprovalRequired:true,
});

const finite=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const rowKey=row=>`${row?.symbol??''}|${row?.sessionDate??''}|${row?.featureCutoff??''}`;

function validRow(row){
  if(!row?.symbol||!row?.sessionDate||!row?.featureCutoff||!row?.outcomeAt) return false;
  if(Date.parse(row.featureCutoff)>=Date.parse(row.outcomeAt)) return false;
  if(row?.outcomeSessionDate&&row.outcomeSessionDate!==row.sessionDate) return false;
  return row?.pointInTimeValid!==false&&finite(row?.label)&&finite(row?.actualReturnPct);
}

function normalizeHorizonMap(input={}){
  const entries=input instanceof Map?[...input.entries()]:Object.entries(input??{});
  return new Map(entries.map(([h,rows])=>[Number(h),(Array.isArray(rows)?rows:[]).filter(validRow)])
    .filter(([h,rows])=>Number.isInteger(h)&&h>0&&rows.length).sort((a,b)=>a[0]-b[0]));
}

function commonKeys(horizonMap){
  const sets=[...horizonMap.values()].map(rows=>new Set(rows.map(rowKey)));
  if(!sets.length) return new Set();
  return new Set([...sets[0]].filter(key=>sets.every(set=>set.has(key))));
}

function rowsForKeys(rows,keys,cutoff=null){
  return rows.filter(row=>keys.has(rowKey(row))&&(!cutoff||Date.parse(row.outcomeAt)<=Date.parse(cutoff)));
}

function projectRows(rows,keys){
  if(!keys) return rows.slice();
  return rows.map(row=>({...row,features:Object.fromEntries(keys.filter(key=>finite(row?.features?.[key])).map(key=>[key,Number(row.features[key])]))}));
}

function defaultFitPredictor(rows,config){
  const model=trainModel({rows,modelType:config.type,options:config.options});
  return row=>model.predict(row);
}

function summarize(signals=[]){
  const n=signals.length;
  const positive=signals.filter(x=>x.netReturnPct>0).reduce((s,x)=>s+x.netReturnPct,0);
  const negative=-signals.filter(x=>x.netReturnPct<0).reduce((s,x)=>s+x.netReturnPct,0);
  return Object.freeze({
    signalCount:n,
    hitRate:n?signals.filter(x=>x.correct).length/n:null,
    netAverageReturnPct:n?signals.reduce((s,x)=>s+x.netReturnPct,0)/n:null,
    grossAverageReturnPct:n?signals.reduce((s,x)=>s+x.grossAlignedReturnPct,0)/n:null,
    profitFactor:negative>0?positive/negative:(positive>0?Infinity:null),
  });
}

function nearlyEqual(a,b,tolerance=1e-12){
  if(a===null||a===undefined||b===null||b===undefined) return a==null&&b==null;
  return Number.isFinite(Number(a))&&Number.isFinite(Number(b))&&Math.abs(Number(a)-Number(b))<=tolerance;
}

export function replayNestedAdaptiveOosSignals(horizonRowsByBars={},options={}){
  const horizonMap=normalizeHorizonMap(horizonRowsByBars);
  const horizons=[...horizonMap.keys()];
  if(!horizons.length) return Object.freeze({phase:'57.p21.3-signal-replay',status:'NO_INTRADAY_HORIZON_ROWS',signals:Object.freeze([]),outerResults:Object.freeze([]),safety:PHASE57_P21_3_SIGNAL_REPLAY_SAFETY});

  const common=commonKeys(horizonMap);
  const anchorHorizon=horizons[0];
  const anchorRows=horizonMap.get(anchorHorizon).filter(row=>common.has(rowKey(row)));
  const outerFolds=buildIntradayWalkForwardFolds(anchorRows,{
    trainFraction:options.outerTrainFraction??0.6,
    testFraction:options.outerTestFraction??0.1,
    minTrainRows:options.outerMinTrainRows??30,
  });
  const fitPredictor=options.fitPredictor??defaultFitPredictor;
  const signals=[];
  const outerResults=[];

  for(const fold of outerFolds){
    const trainKeys=new Set(fold.train.map(rowKey));
    const testKeys=new Set(fold.test.map(rowKey));
    const innerMap={};
    for(const [h,rows] of horizonMap) innerMap[h]=rowsForKeys(rows,trainKeys,fold.trainCutoff);
    const selection=selectInnerAdaptiveHorizon(innerMap,options);
    if(!selection.selected){
      outerResults.push(Object.freeze({fold:fold.fold,status:'ABSTAIN_NO_ELIGIBLE_INNER_HORIZON',trainCutoff:fold.trainCutoff,testStart:fold.testStart,testEnd:fold.testEnd}));
      continue;
    }
    const picked=selection.selected;
    const sourceRows=horizonMap.get(picked.horizonBars)??[];
    const train=projectRows(rowsForKeys(sourceRows,trainKeys,fold.trainCutoff),picked.featureKeys);
    const test=projectRows(rowsForKeys(sourceRows,testKeys),picked.featureKeys);
    if(!train.length||!test.length){
      outerResults.push(Object.freeze({fold:fold.fold,status:'ABSTAIN_MISSING_SELECTED_HORIZON_ROWS',selectedHorizonBars:picked.horizonBars}));
      continue;
    }
    const config={id:picked.configId,type:picked.modelType,options:picked.modelOptions};
    const predictor=fitPredictor(train,config,{horizonBars:picked.horizonBars,featureFamily:picked.featureFamily,threshold:picked.threshold,fold:fold.fold,stage:'OUTER_REPLAY'});
    if(typeof predictor!=='function') throw new TypeError('fitPredictor must return a predictor function');
    let foldSignals=0;
    for(const row of test){
      const raw=Number(predictor(row));
      if(!Number.isFinite(raw)) continue;
      const probability=Math.max(0.001,Math.min(0.999,raw));
      const confidence=Math.max(probability,1-probability);
      if(confidence<Number(picked.threshold)) continue;
      const direction=probability>=0.5?1:0;
      const alignedReturnPct=direction===1?Number(row.actualReturnPct):-Number(row.actualReturnPct);
      const netReturnPct=alignedReturnPct-Number(options.roundTripCostPct??0.05);
      signals.push(Object.freeze({
        baseOuterFold:fold.fold,symbol:row.symbol,sessionDate:row.sessionDate,featureCutoff:row.featureCutoff,outcomeAt:row.outcomeAt,
        horizonBars:Number(row.horizonBars),direction,probability,confidence,label:Number(row.label),correct:direction===Number(row.label),
        grossAlignedReturnPct:alignedReturnPct,netReturnPct,
        selectedFeatureFamily:picked.featureFamily,selectedModelType:picked.modelType,selectedConfigId:picked.configId,selectedThreshold:picked.threshold,
        signalPointInTimeValid:true,selectionSource:'P21_1_OUTER_OOS_REPLAY',
      }));
      foldSignals++;
    }
    outerResults.push(Object.freeze({
      fold:fold.fold,status:'OUTER_REPLAYED',selectedHorizonBars:picked.horizonBars,selectedFeatureFamily:picked.featureFamily,
      selectedModelType:picked.modelType,selectedConfigId:picked.configId,selectedThreshold:picked.threshold,
      trainRows:train.length,testRows:test.length,signalCount:foldSignals,trainCutoff:fold.trainCutoff,testStart:fold.testStart,testEnd:fold.testEnd,
      outerUntouchedBySelection:true,outerNeverUsedForFit:true,
    }));
  }

  const summary=summarize(signals);
  const reference=options.referenceResult??null;
  const reconciliation=reference?Object.freeze({
    referenceSignalCount:Number(reference.signalCount??0),replaySignalCount:summary.signalCount,
    signalCountMatches:Number(reference.signalCount??0)===summary.signalCount,
    hitRateMatches:nearlyEqual(reference.hitRate,summary.hitRate),
    netAverageReturnMatches:nearlyEqual(reference.netAverageReturnPct,summary.netAverageReturnPct,1e-10),
    matches:Number(reference.signalCount??0)===summary.signalCount&&nearlyEqual(reference.hitRate,summary.hitRate)&&nearlyEqual(reference.netAverageReturnPct,summary.netAverageReturnPct,1e-10),
  }):null;

  return Object.freeze({
    phase:'57.p21.3-signal-replay',status:signals.length?'ADAPTIVE_OUTER_OOS_SIGNALS_REPLAYED':'NO_OUTER_SIGNALS',
    horizonsBars:Object.freeze(horizons),outerFoldCount:outerFolds.length,commonRowCount:common.size,...summary,
    signals:Object.freeze(signals),outerResults:Object.freeze(outerResults),reconciliation,
    selectionIntegrity:Object.freeze({horizonSelectedOnInnerOnly:true,featureFamilySelectedOnInnerOnly:true,modelFamilySelectedOnInnerOnly:true,thresholdSelectedOnInnerOnly:true,outerTestNeverUsedForSelection:true,outerTestNeverUsedForFit:true,sameSessionOnly:true,overnightHoldingForbidden:true}),
    executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,
    safety:PHASE57_P21_3_SIGNAL_REPLAY_SAFETY,
  });
}

export default {replayNestedAdaptiveOosSignals};
