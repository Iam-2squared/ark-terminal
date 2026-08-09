import { buildIntradayWalkForwardFolds } from './phase57-intraday-walkforward-cost.js';
import { evaluateCostAwareStrategy } from '../strategy/cost-aware-evaluation.js';
import { trainModel } from '../models/phase47-real-training.js';

export const PHASE57_P8_SAFETY = Object.freeze({
  mode: 'PHASE57_INTRADAY_MODEL_FAMILY_RESEARCH_ONLY',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  humanApprovalRequired: true,
});

const clamp01 = v => Math.max(0.001, Math.min(0.999, Number(v)));
const configs = Object.freeze([
  { id:'LOGIT', type:'LOGISTIC_REGRESSION', options:{ iterations:160, learningRate:0.05, l2:0.001 } },
  { id:'RF12', type:'RANDOM_FOREST', options:{ treeCount:12, maxThresholdCandidates:10 } },
  { id:'GB12', type:'GRADIENT_BOOSTING', options:{ rounds:12, learningRate:0.08, maxThresholdCandidates:10 } },
]);

function score(rows, model, threshold, costs) {
  const signals=[];
  for (const row of rows) {
    const p=clamp01(model.predict(row));
    const confidence=Math.max(p,1-p);
    if (confidence<threshold) continue;
    const prediction=p>=0.5?1:0;
    const correct=prediction===Number(row.label);
    const grossReturn=correct?Number(row.barrierBps??20)/100:-Number(row.barrierBps??20)/100;
    signals.push({correct,grossReturn,feePercent:costs.feePercent,slippagePercent:costs.slippagePercent,delayCostPercent:costs.delayCostPercent});
  }
  const cost=evaluateCostAwareStrategy(signals,costs);
  return {signalCount:signals.length,hitRate:signals.length?signals.filter(x=>x.correct).length/signals.length:null,netAverageReturn:cost.netAverageReturn,profitFactor:cost.profitFactor};
}

function innerRank(a,b){
  const an=Number.isFinite(a.netAverageReturn)?a.netAverageReturn:-Infinity;
  const bn=Number.isFinite(b.netAverageReturn)?b.netAverageReturn:-Infinity;
  if (bn!==an) return bn-an;
  const ah=Number.isFinite(a.hitRate)?a.hitRate:-Infinity;
  const bh=Number.isFinite(b.hitRate)?b.hitRate:-Infinity;
  if (bh!==ah) return bh-ah;
  return b.signalCount-a.signalCount;
}

export function selectInnerIntradayModelFamily(trainRows=[], options={}){
  const thresholds=options.thresholds??[0.55,0.60,0.65];
  const modelConfigs=options.modelConfigs??configs;
  const innerFolds=buildIntradayWalkForwardFolds(trainRows,{trainFraction:options.innerTrainFraction??0.6,testFraction:options.innerTestFraction??0.15,minTrainRows:options.innerMinTrainRows??20});
  const costs={feePercent:options.feePercent??0,slippagePercent:options.slippagePercent??0.05,delayCostPercent:options.delayCostPercent??0};
  const candidates=[];
  for(const cfg of modelConfigs){
    for(const threshold of thresholds){
      let signalCount=0,hitWeighted=0,netWeighted=0;
      for(const fold of innerFolds){
        const model=trainModel({rows:fold.train,modelType:cfg.type,options:cfg.options});
        const s=score(fold.test,model,threshold,costs);
        signalCount+=s.signalCount;
        hitWeighted+=(s.hitRate??0)*s.signalCount;
        netWeighted+=(s.netAverageReturn??0)*s.signalCount;
      }
      candidates.push({configId:cfg.id,modelType:cfg.type,options:cfg.options,threshold,signalCount,hitRate:signalCount?hitWeighted/signalCount:null,netAverageReturn:signalCount?netWeighted/signalCount:null});
    }
  }
  const eligible=candidates.filter(c=>c.signalCount>=(options.minInnerSignals??1));
  const best=(eligible.length?eligible:candidates).slice().sort(innerRank)[0]??null;
  return Object.freeze({selected:best?Object.freeze(best):null,candidates:Object.freeze(candidates),innerFoldCount:innerFolds.length,selectionSource:'INNER_WALK_FORWARD_ONLY'});
}

export function evaluateNestedIntradayModelFamily(rows=[], options={}){
  const outerFolds=buildIntradayWalkForwardFolds(rows,{trainFraction:options.trainFraction??0.6,testFraction:options.testFraction??0.1,minTrainRows:options.minTrainRows??20});
  const costs={feePercent:options.feePercent??0,slippagePercent:options.slippagePercent??0.05,delayCostPercent:options.delayCostPercent??0};
  const outer=[];
  for(const fold of outerFolds){
    const sel=selectInnerIntradayModelFamily(fold.train,options);
    if(!sel.selected) continue;
    const model=trainModel({rows:fold.train,modelType:sel.selected.modelType,options:sel.selected.options});
    const s=score(fold.test,model,sel.selected.threshold,costs);
    outer.push(Object.freeze({fold:fold.fold,selectedConfigId:sel.selected.configId,selectedModelType:sel.selected.modelType,selectedThreshold:sel.selected.threshold,innerFoldCount:sel.innerFoldCount,trainRows:fold.train.length,testRows:fold.test.length,...s,outerUntouchedBySelection:true}));
  }
  const signalCount=outer.reduce((x,r)=>x+r.signalCount,0);
  const hitWeighted=outer.reduce((x,r)=>x+(r.hitRate??0)*r.signalCount,0);
  const netWeighted=outer.reduce((x,r)=>x+(r.netAverageReturn??0)*r.signalCount,0);
  return Object.freeze({phase:'57.p8',status:outer.length?'NESTED_INTRADAY_MODEL_FAMILY_OOS_READY':'NO_NESTED_MODEL_FAMILY_FOLDS',outerResults:Object.freeze(outer),signalCount,hitRate:signalCount?hitWeighted/signalCount:null,netAverageReturn:signalCount?netWeighted/signalCount:null,selectionIntegrity:Object.freeze({modelFamilySelectedOnInnerOnly:true,thresholdSelectedOnInnerOnly:true,outerTestNeverUsedForSelection:true,outerTestNeverUsedForFit:true}),recommendationAllowed:false,paperTradingAllowed:false,executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,humanApprovalRequired:true,safety:PHASE57_P8_SAFETY});
}

export default {selectInnerIntradayModelFamily,evaluateNestedIntradayModelFamily};
