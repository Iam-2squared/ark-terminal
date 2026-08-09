import { buildIntradayWalkForwardFolds } from './phase57-intraday-walkforward-cost.js';
import { selectInnerIntradayContext, applyIntradayContext } from './phase57-intraday-context-conditioning.js';
import { trainModel } from '../models/phase47-real-training.js';
import { evaluateCostAwareStrategy } from '../strategy/cost-aware-evaluation.js';

export const PHASE57_P20_5_SAFETY = Object.freeze({
  mode:'PHASE57_INNER_STABILITY_ABSTENTION_RESEARCH_ONLY',
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,
  humanApprovalRequired:true,
});

const finite=v=>Number.isFinite(Number(v));
const clamp01=v=>Math.max(0.001,Math.min(0.999,Number(v)));

export function passesInnerStabilityGate(selected, options={}) {
  if (!selected) return false;
  const minSignals=options.minStableInnerSignals ?? 30;
  const minHitRate=options.minStableInnerHitRate ?? 0.56;
  const minNet=options.minStableInnerNetReturn ?? 0;
  return Number(selected.signalCount??0)>=minSignals && finite(selected.hitRate) && Number(selected.hitRate)>=minHitRate && finite(selected.netAverageReturn) && Number(selected.netAverageReturn)>=minNet;
}

function projectRow(row,keys){
  if(!keys) return row;
  const features=Object.fromEntries(keys.filter(k=>finite(row?.features?.[k])).map(k=>[k,Number(row.features[k])]));
  return {...row,features};
}

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

export function evaluateNestedIntradayStabilityGate(rows=[],options={}){
  const folds=buildIntradayWalkForwardFolds(rows,{trainFraction:options.trainFraction??0.6,testFraction:options.testFraction??0.1,minTrainRows:options.minTrainRows??200});
  const costs={feePercent:options.feePercent??0,slippagePercent:options.slippagePercent??0.05,delayCostPercent:options.delayCostPercent??0};
  const outer=[]; let abstainedFolds=0;
  for(const fold of folds){
    const sel=selectInnerIntradayContext(fold.train,options);
    const picked=sel.selected;
    if(!passesInnerStabilityGate(picked,options)){abstainedFolds++;continue;}
    const train=applyIntradayContext(fold.train,picked.context).map(r=>projectRow(r,picked.featureKeys));
    const test=applyIntradayContext(fold.test,picked.context).map(r=>projectRow(r,picked.featureKeys));
    if(!train.length||!test.length){abstainedFolds++;continue;}
    const m=picked.modelSelection;
    const model=trainModel({rows:train,modelType:m.modelType,options:m.options});
    const s=score(test,model,m.threshold,costs);
    outer.push(Object.freeze({fold:fold.fold,context:picked.context.key,selectedFeatureFamily:picked.featureFamily,innerSignalCount:picked.signalCount,innerHitRate:picked.hitRate,innerNetAverageReturn:picked.netAverageReturn,...s,outerUntouchedBySelection:true}));
  }
  const signalCount=outer.reduce((n,r)=>n+r.signalCount,0);
  const hitRate=signalCount?outer.reduce((n,r)=>n+(r.hitRate??0)*r.signalCount,0)/signalCount:null;
  const netAverageReturn=signalCount?outer.reduce((n,r)=>n+(r.netAverageReturn??0)*r.signalCount,0)/signalCount:null;
  return Object.freeze({phase:'57.p20.5',status:outer.length?'INNER_STABILITY_GATED_OOS_READY':'ABSTAIN_ALL_FOLDS',outerResults:Object.freeze(outer),abstainedFolds,eligibleFolds:outer.length,signalCount,hitRate,netAverageReturn,selectionIntegrity:Object.freeze({stabilityGateUsesInnerOnly:true,contextSelectedOnInnerOnly:true,featureFamilySelectedOnInnerOnly:true,modelFamilySelectedOnInnerOnly:true,thresholdSelectedOnInnerOnly:true,outerTestNeverUsedForSelection:true,outerTestNeverUsedForFit:true}),...PHASE57_P20_5_SAFETY});
}

export default {passesInnerStabilityGate,evaluateNestedIntradayStabilityGate};
