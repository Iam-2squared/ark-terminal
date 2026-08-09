import { materializeHorizonRows } from './phase57-adaptive-horizon-magnitude.js';
import { buildIntradayWalkForwardFolds } from './phase57-intraday-walkforward-cost.js';
import { DEFAULT_FEATURE_FAMILIES } from './phase57-intraday-feature-family.js';
import { trainModel } from '../models/phase47-real-training.js';

export const PHASE57_P21_1_SAFETY = Object.freeze({
  mode:'PHASE57_NESTED_ADAPTIVE_HORIZON_RESEARCH_ONLY',
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

export const DEFAULT_INTRADAY_HORIZONS_BARS = Object.freeze([1,3,6,12,24]);
export const DEFAULT_P21_MODEL_CONFIGS = Object.freeze([
  Object.freeze({id:'LOGIT',type:'LOGISTIC_REGRESSION',options:Object.freeze({iterations:160,learningRate:0.05,l2:0.001})}),
  Object.freeze({id:'RF12',type:'RANDOM_FOREST',options:Object.freeze({treeCount:12,maxThresholdCandidates:10})}),
  Object.freeze({id:'GB12',type:'GRADIENT_BOOSTING',options:Object.freeze({rounds:12,learningRate:0.08,maxThresholdCandidates:10})}),
]);

const finite=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const rowKey=row=>`${row?.symbol??''}|${row?.sessionDate??''}|${row?.featureCutoff??''}`;

function validIntradayRow(row){
  if(!row?.symbol||!row?.sessionDate||!row?.featureCutoff||!row?.outcomeAt) return false;
  if(Date.parse(row.featureCutoff)>=Date.parse(row.outcomeAt)) return false;
  if(row?.outcomeSessionDate && row.outcomeSessionDate!==row.sessionDate) return false;
  return row?.pointInTimeValid!==false && finite(row?.label) && finite(row?.actualReturnPct);
}

function normalizeHorizonMap(input={}){
  const entries=input instanceof Map?[...input.entries()]:Object.entries(input??{});
  return new Map(entries
    .map(([h,rows])=>[Number(h),(Array.isArray(rows)?rows:[]).filter(validIntradayRow)])
    .filter(([h,rows])=>Number.isInteger(h)&&h>0&&rows.length)
    .sort((a,b)=>a[0]-b[0]));
}

function projectRows(rows,keys){
  if(!keys) return rows.slice();
  return rows.map(row=>({
    ...row,
    features:Object.fromEntries(keys
      .filter(key=>finite(row?.features?.[key]))
      .map(key=>[key,Number(row.features[key])])),
  }));
}

function defaultFitPredictor(rows,config){
  const model=trainModel({rows,modelType:config.type,options:config.options});
  return row=>model.predict(row);
}

function scoreActualMagnitude(rows,predictor,{threshold=0.55,roundTripCostPct=0.05}={}){
  const signals=[];
  for(const row of rows){
    const raw=Number(predictor(row));
    if(!Number.isFinite(raw)) continue;
    const probability=Math.max(0.001,Math.min(0.999,raw));
    const confidence=Math.max(probability,1-probability);
    if(confidence<threshold) continue;
    const direction=probability>=0.5?1:0;
    const alignedReturnPct=direction===1?Number(row.actualReturnPct):-Number(row.actualReturnPct);
    const netReturnPct=alignedReturnPct-Number(roundTripCostPct||0);
    signals.push(Object.freeze({
      symbol:row.symbol,sessionDate:row.sessionDate,featureCutoff:row.featureCutoff,outcomeAt:row.outcomeAt,
      direction,probability,confidence,correct:direction===Number(row.label),
      grossAlignedReturnPct:alignedReturnPct,netReturnPct,horizonBars:Number(row.horizonBars),
    }));
  }
  const signalCount=signals.length;
  const positive=signals.filter(x=>x.netReturnPct>0).reduce((s,x)=>s+x.netReturnPct,0);
  const negative=-signals.filter(x=>x.netReturnPct<0).reduce((s,x)=>s+x.netReturnPct,0);
  return Object.freeze({
    signalCount,
    hitRate:signalCount?signals.filter(x=>x.correct).length/signalCount:null,
    grossAverageReturnPct:signalCount?signals.reduce((s,x)=>s+x.grossAlignedReturnPct,0)/signalCount:null,
    netAverageReturnPct:signalCount?signals.reduce((s,x)=>s+x.netReturnPct,0)/signalCount:null,
    profitFactor:negative>0?positive/negative:(positive>0?Infinity:null),
    signals:Object.freeze(signals),
  });
}

function summarizeSignals(signals=[]){
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

function candidateRank(a,b){
  const an=finite(a?.netAverageReturnPct)?Number(a.netAverageReturnPct):-Infinity;
  const bn=finite(b?.netAverageReturnPct)?Number(b.netAverageReturnPct):-Infinity;
  if(bn!==an) return bn-an;
  const ap=finite(a?.profitFactor)?Number(a.profitFactor):-Infinity;
  const bp=finite(b?.profitFactor)?Number(b.profitFactor):-Infinity;
  if(bp!==ap) return bp-ap;
  const ah=finite(a?.hitRate)?Number(a.hitRate):-Infinity;
  const bh=finite(b?.hitRate)?Number(b.hitRate):-Infinity;
  if(bh!==ah) return bh-ah;
  return Number(b?.signalCount??0)-Number(a?.signalCount??0);
}

function commonKeys(horizonMap){
  const sets=[...horizonMap.values()].map(rows=>new Set(rows.map(rowKey)));
  if(!sets.length) return new Set();
  return new Set([...sets[0]].filter(key=>sets.every(set=>set.has(key))));
}

function rowsForKeys(rows,keys,cutoff=null){
  return rows.filter(row=>keys.has(rowKey(row)) && (!cutoff || Date.parse(row.outcomeAt)<=Date.parse(cutoff)));
}

export function buildIntradayHorizonDatasets(baseRows=[],{
  horizons=DEFAULT_INTRADAY_HORIZONS_BARS,
  featureRows=[],
}={}){
  const featureMap=new Map((Array.isArray(featureRows)?featureRows:[]).map(row=>[rowKey(row),row?.features??{}]));
  const out={};
  for(const h of [...new Set(horizons.map(Number).filter(x=>Number.isInteger(x)&&x>0))].sort((a,b)=>a-b)){
    out[h]=Object.freeze(materializeHorizonRows(baseRows,h).map(row=>Object.freeze({
      ...row,
      outcomeSessionDate:row.outcomeSessionDate??row.sessionDate,
      intradayOnly:true,
      features:row.features??featureMap.get(rowKey(row))??{},
    })).filter(validIntradayRow));
  }
  return Object.freeze(out);
}

export function selectInnerAdaptiveHorizon(horizonRowsByBars={},options={}){
  const horizonMap=normalizeHorizonMap(horizonRowsByBars);
  const featureFamilies=options.featureFamilies??DEFAULT_FEATURE_FAMILIES;
  const modelConfigs=options.modelConfigs??DEFAULT_P21_MODEL_CONFIGS;
  const thresholds=options.thresholds??[0.55,0.60,0.65];
  const fitPredictor=options.fitPredictor??defaultFitPredictor;
  const candidates=[];

  for(const [horizonBars,rows] of horizonMap){
    const innerFolds=buildIntradayWalkForwardFolds(rows,{
      trainFraction:options.innerTrainFraction??0.6,
      testFraction:options.innerTestFraction??0.15,
      minTrainRows:options.innerMinTrainRows??20,
    });
    for(const [featureFamily,featureKeys] of Object.entries(featureFamilies)){
      for(const config of modelConfigs){
        for(const threshold of thresholds){
          const allSignals=[];
          for(const fold of innerFolds){
            const train=projectRows(fold.train,featureKeys);
            const test=projectRows(fold.test,featureKeys);
            const predictor=fitPredictor(train,config,{horizonBars,featureFamily,threshold,fold:fold.fold,stage:'INNER'});
            if(typeof predictor!=='function') throw new TypeError('fitPredictor must return a predictor function');
            const scored=scoreActualMagnitude(test,predictor,{threshold,roundTripCostPct:options.roundTripCostPct??0.05});
            allSignals.push(...scored.signals);
          }
          const summary=summarizeSignals(allSignals);
          candidates.push(Object.freeze({
            horizonBars,featureFamily,featureKeys,configId:config.id,modelType:config.type,modelOptions:config.options,
            threshold,innerFoldCount:innerFolds.length,...summary,selectionSource:'INNER_WALK_FORWARD_ONLY',
          }));
        }
      }
    }
  }

  const minimumSignals=options.minInnerSignals??20;
  const minimumNetReturnPct=options.minimumInnerNetReturnPct??0;
  const eligible=candidates.filter(c=>c.signalCount>=minimumSignals&&finite(c.netAverageReturnPct)&&Number(c.netAverageReturnPct)>=minimumNetReturnPct);
  const ranked=(eligible.length?eligible:candidates.filter(c=>finite(c.netAverageReturnPct))).slice().sort(candidateRank);
  return Object.freeze({
    selected:eligible.length?(ranked[0]??null):null,
    bestObserved:ranked[0]??null,
    eligibleCount:eligible.length,
    candidates:Object.freeze(candidates),
    minimumSignals,minimumNetReturnPct,
    selectionSource:'INNER_WALK_FORWARD_ONLY',
    outerDataUsedForSelection:false,
  });
}

export function evaluateNestedAdaptiveHorizon(horizonRowsByBars={},options={}){
  const horizonMap=normalizeHorizonMap(horizonRowsByBars);
  const horizons=[...horizonMap.keys()];
  if(!horizons.length) return Object.freeze({phase:'57.p21.1',status:'NO_INTRADAY_HORIZON_ROWS',outerResults:Object.freeze([]),safety:PHASE57_P21_1_SAFETY});

  const common=commonKeys(horizonMap);
  const anchorHorizon=horizons[0];
  const anchorRows=horizonMap.get(anchorHorizon).filter(row=>common.has(rowKey(row)));
  const outerFolds=buildIntradayWalkForwardFolds(anchorRows,{
    trainFraction:options.outerTrainFraction??0.6,
    testFraction:options.outerTestFraction??0.1,
    minTrainRows:options.outerMinTrainRows??30,
  });
  const fitPredictor=options.fitPredictor??defaultFitPredictor;
  const outerResults=[];
  const allOuterSignals=[];

  for(const fold of outerFolds){
    const trainKeys=new Set(fold.train.map(rowKey));
    const testKeys=new Set(fold.test.map(rowKey));
    const innerMap={};
    for(const [h,rows] of horizonMap) innerMap[h]=rowsForKeys(rows,trainKeys,fold.trainCutoff);

    const selection=selectInnerAdaptiveHorizon(innerMap,options);
    if(!selection.selected){
      outerResults.push(Object.freeze({fold:fold.fold,status:'ABSTAIN_NO_ELIGIBLE_INNER_HORIZON',trainCutoff:fold.trainCutoff,testStart:fold.testStart,testEnd:fold.testEnd,outerUntouchedBySelection:true}));
      continue;
    }

    const picked=selection.selected;
    const sourceRows=horizonMap.get(picked.horizonBars)??[];
    const train=projectRows(rowsForKeys(sourceRows,trainKeys,fold.trainCutoff),picked.featureKeys);
    const test=projectRows(rowsForKeys(sourceRows,testKeys),picked.featureKeys);
    if(!train.length||!test.length){
      outerResults.push(Object.freeze({fold:fold.fold,status:'ABSTAIN_MISSING_SELECTED_HORIZON_ROWS',selectedHorizonBars:picked.horizonBars,outerUntouchedBySelection:true}));
      continue;
    }
    const config={id:picked.configId,type:picked.modelType,options:picked.modelOptions};
    const predictor=fitPredictor(train,config,{horizonBars:picked.horizonBars,featureFamily:picked.featureFamily,threshold:picked.threshold,fold:fold.fold,stage:'OUTER_FIT'});
    if(typeof predictor!=='function') throw new TypeError('fitPredictor must return a predictor function');
    const scored=scoreActualMagnitude(test,predictor,{threshold:picked.threshold,roundTripCostPct:options.roundTripCostPct??0.05});
    allOuterSignals.push(...scored.signals);
    outerResults.push(Object.freeze({
      fold:fold.fold,status:'OUTER_EVALUATED',selectedHorizonBars:picked.horizonBars,
      selectedFeatureFamily:picked.featureFamily,selectedModelType:picked.modelType,selectedConfigId:picked.configId,
      selectedThreshold:picked.threshold,innerEligibleCount:selection.eligibleCount,
      trainRows:train.length,testRows:test.length,trainCutoff:fold.trainCutoff,testStart:fold.testStart,testEnd:fold.testEnd,
      signalCount:scored.signalCount,hitRate:scored.hitRate,netAverageReturnPct:scored.netAverageReturnPct,profitFactor:scored.profitFactor,
      outerUntouchedBySelection:true,outerNeverUsedForFit:true,
    }));
  }

  const summary=summarizeSignals(allOuterSignals);
  return Object.freeze({
    phase:'57.p21.1',
    status:allOuterSignals.length?'NESTED_ADAPTIVE_HORIZON_OOS_READY':'NO_OUTER_SIGNALS',
    horizonsBars:Object.freeze(horizons),anchorHorizonBars:anchorHorizon,commonRowCount:common.size,outerFoldCount:outerFolds.length,
    outerResults:Object.freeze(outerResults),...summary,
    selectionIntegrity:Object.freeze({
      horizonSelectedOnInnerOnly:true,featureFamilySelectedOnInnerOnly:true,modelFamilySelectedOnInnerOnly:true,thresholdSelectedOnInnerOnly:true,
      candidateTrainingRequiresOutcomeBeforeOuterCutoff:true,outerTestNeverUsedForSelection:true,outerTestNeverUsedForFit:true,
      sameSessionOnly:true,overnightHoldingForbidden:true,
    }),
    recommendationAllowed:false,paperTradingAllowed:false,executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,
    rssOrderFunctionAllowed:false,liveTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,
    transmitted:false,humanApprovalRequired:true,safety:PHASE57_P21_1_SAFETY,
  });
}

export default {buildIntradayHorizonDatasets,selectInnerAdaptiveHorizon,evaluateNestedAdaptiveHorizon};
