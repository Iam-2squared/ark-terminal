import { buildIntradayWalkForwardFolds } from './phase57-intraday-walkforward-cost.js';
import { selectInnerIntradayModelFamily } from './phase57-intraday-model-family.js';
import { trainModel } from '../models/phase47-real-training.js';
import { evaluateCostAwareStrategy } from '../strategy/cost-aware-evaluation.js';

export const PHASE57_P20_1_SAFETY = Object.freeze({
  mode:'PHASE57_INTRADAY_FEATURE_FAMILY_RESEARCH_ONLY',
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,
  automaticPromotionAllowed:false,productionUpdateAllowed:false,humanApprovalRequired:true,
});

export const DEFAULT_FEATURE_FAMILIES = Object.freeze({
  BASE:['returnFromOpen','rangePosition','shortMomentum','relativeVolume','vwapDistancePct'],
  TREND:['returnFromOpen','rangePosition','shortMomentum','vwapDistancePct','ma5DistancePct','ma10DistancePct','ma20DistancePct','ma5SlopePct'],
  MOMENTUM:['shortMomentum','rsi14','macd','macdSignalGap','range20Position'],
  VOLATILITY:['atrPct','bbPosition','range20Position','relativeVolume20'],
  TIME_CONTEXT:['openingMinutes','isOpening30','isLunchReturn','isClosing30','returnFromOpen','vwapDistancePct','relativeVolume20'],
  FULL:null,
});

const clamp01=v=>Math.max(0.001,Math.min(0.999,Number(v)));

function projectRow(row, keys){
  if(!keys) return row;
  const features=Object.fromEntries(keys.filter(k=>Number.isFinite(Number(row?.features?.[k]))).map(k=>[k,Number(row.features[k])]));
  return {...row,features};
}

function projectRows(rows,keys){return rows.map(r=>projectRow(r,keys));}

function score(rows,model,threshold,costs){
  const signals=[];
  for(const row of rows){
    const p=clamp01(model.predict(row));
    const confidence=Math.max(p,1-p);
    if(confidence<threshold) continue;
    const prediction=p>=0.5?1:0;
    const correct=prediction===Number(row.label);
    const grossReturn=correct?Number(row.barrierBps??20)/100:-Number(row.barrierBps??20)/100;
    signals.push({correct,grossReturn,feePercent:costs.feePercent,slippagePercent:costs.slippagePercent,delayCostPercent:costs.delayCostPercent});
  }
  const cost=evaluateCostAwareStrategy(signals,costs);
  return {signalCount:signals.length,hitRate:signals.length?signals.filter(x=>x.correct).length/signals.length:null,netAverageReturn:cost.netAverageReturn,profitFactor:cost.profitFactor};
}

function rankCandidate(a,b){
  const an=Number.isFinite(a?.selected?.netAverageReturn)?a.selected.netAverageReturn:-Infinity;
  const bn=Number.isFinite(b?.selected?.netAverageReturn)?b.selected.netAverageReturn:-Infinity;
  if(bn!==an) return bn-an;
  const ah=Number.isFinite(a?.selected?.hitRate)?a.selected.hitRate:-Infinity;
  const bh=Number.isFinite(b?.selected?.hitRate)?b.selected.hitRate:-Infinity;
  if(bh!==ah) return bh-ah;
  return (b?.selected?.signalCount??0)-(a?.selected?.signalCount??0);
}

export function selectInnerFeatureFamily(trainRows=[],options={}){
  const families=options.featureFamilies??DEFAULT_FEATURE_FAMILIES;
  const candidates=[];
  for(const [family,keys] of Object.entries(families)){
    const projected=projectRows(trainRows,keys);
    const selection=selectInnerIntradayModelFamily(projected,options);
    candidates.push({family,keys,selected:selection.selected,innerFoldCount:selection.innerFoldCount,selectionSource:'INNER_WALK_FORWARD_ONLY'});
  }
  const eligible=candidates.filter(c=>c.selected && c.selected.signalCount>=(options.minInnerSignals??1));
  const selected=(eligible.length?eligible:candidates.filter(c=>c.selected)).slice().sort(rankCandidate)[0]??null;
  return Object.freeze({selected:selected?Object.freeze(selected):null,candidates:Object.freeze(candidates),selectionSource:'INNER_WALK_FORWARD_ONLY'});
}

export function evaluateNestedIntradayFeatureFamily(rows=[],options={}){
  const folds=buildIntradayWalkForwardFolds(rows,{trainFraction:options.trainFraction??0.6,testFraction:options.testFraction??0.1,minTrainRows:options.minTrainRows??20});
  const costs={feePercent:options.feePercent??0,slippagePercent:options.slippagePercent??0.05,delayCostPercent:options.delayCostPercent??0};
  const outer=[];
  for(const fold of folds){
    const familySel=selectInnerFeatureFamily(fold.train,options);
    const picked=familySel.selected;
    if(!picked?.selected) continue;
    const projectedTrain=projectRows(fold.train,picked.keys);
    const projectedTest=projectRows(fold.test,picked.keys);
    const model=trainModel({rows:projectedTrain,modelType:picked.selected.modelType,options:picked.selected.options});
    const s=score(projectedTest,model,picked.selected.threshold,costs);
    outer.push(Object.freeze({fold:fold.fold,selectedFeatureFamily:picked.family,selectedModelType:picked.selected.modelType,selectedThreshold:picked.selected.threshold,trainRows:projectedTrain.length,testRows:projectedTest.length,...s,outerUntouchedBySelection:true}));
  }
  const signalCount=outer.reduce((n,r)=>n+r.signalCount,0);
  const hitRate=signalCount?outer.reduce((n,r)=>n+(r.hitRate??0)*r.signalCount,0)/signalCount:null;
  const netAverageReturn=signalCount?outer.reduce((n,r)=>n+(r.netAverageReturn??0)*r.signalCount,0)/signalCount:null;
  return Object.freeze({
    phase:'57.p20.1',status:outer.length?'NESTED_INTRADAY_FEATURE_FAMILY_OOS_READY':'NO_FEATURE_FAMILY_FOLDS',
    outerResults:Object.freeze(outer),signalCount,hitRate,netAverageReturn,
    selectionIntegrity:Object.freeze({featureFamilySelectedOnInnerOnly:true,modelFamilySelectedOnInnerOnly:true,thresholdSelectedOnInnerOnly:true,outerTestNeverUsedForSelection:true,outerTestNeverUsedForFit:true}),
    recommendationAllowed:false,paperTradingAllowed:false,executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,humanApprovalRequired:true,safety:PHASE57_P20_1_SAFETY,
  });
}

export default {selectInnerFeatureFamily,evaluateNestedIntradayFeatureFamily};
