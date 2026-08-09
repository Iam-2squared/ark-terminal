import { buildIntradayWalkForwardFolds } from './phase57-intraday-walkforward-cost.js';
import { selectInnerIntradayContext, applyIntradayContext } from './phase57-intraday-context-conditioning.js';
import { trainModel } from '../models/phase47-real-training.js';
import { evaluateCostAwareStrategy } from '../strategy/cost-aware-evaluation.js';

export const PHASE57_P20_7_SAFETY = Object.freeze({
  mode:'PHASE57_REGIME_PERSISTENCE_TRANSFERABILITY_RESEARCH_ONLY',
  executionAllowed:false,
  brokerWriteAllowed:false,
  excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,
  paperTradingAllowed:false,
  automaticPromotionAllowed:false,
  productionUpdateAllowed:false,
  humanApprovalRequired:true,
});

const finite=v=>Number.isFinite(Number(v));
const clamp01=v=>Math.max(0.001,Math.min(0.999,Number(v)));

function splitChronological(rows=[],fraction=0.75){
  const sorted=[...rows].sort((a,b)=>String(a.featureCutoff??a.timestamp??'').localeCompare(String(b.featureCutoff??b.timestamp??'')));
  const cut=Math.max(1,Math.min(sorted.length-1,Math.floor(sorted.length*fraction)));
  return {selection:sorted.slice(0,cut),recent:sorted.slice(cut)};
}

export function assessContextTransferability(selectionRows=[],recentRows=[],context,options={}){
  if(!context||!selectionRows.length||!recentRows.length) return Object.freeze({passes:false,reason:'INSUFFICIENT_ROWS'});
  const selectionMatches=applyIntradayContext(selectionRows,context).length;
  const recentMatches=applyIntradayContext(recentRows,context).length;
  const selectionShare=selectionMatches/selectionRows.length;
  const recentShare=recentMatches/recentRows.length;
  const shareRatio=selectionShare>0?recentShare/selectionShare:0;
  const minRecentRows=options.minTransferRecentRows??30;
  const minShareRatio=options.minTransferShareRatio??0.60;
  const maxShareRatio=options.maxTransferShareRatio??1.80;
  const passes=recentMatches>=minRecentRows && shareRatio>=minShareRatio && shareRatio<=maxShareRatio;
  return Object.freeze({passes,selectionMatches,recentMatches,selectionShare,recentShare,shareRatio,minRecentRows,minShareRatio,maxShareRatio,usesLabels:false,usesOuterTest:false});
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

export function evaluateNestedIntradayTransferability(rows=[],options={}){
  const folds=buildIntradayWalkForwardFolds(rows,{trainFraction:options.trainFraction??0.6,testFraction:options.testFraction??0.1,minTrainRows:options.minTrainRows??200});
  const costs={feePercent:options.feePercent??0,slippagePercent:options.slippagePercent??0.05,delayCostPercent:options.delayCostPercent??0};
  const selectionFraction=options.transferSelectionFraction??0.75;
  const outer=[]; let abstainedFolds=0;
  for(const fold of folds){
    const {selection,recent}=splitChronological(fold.train,selectionFraction);
    const picked=selectInnerIntradayContext(selection,options).selected;
    if(!picked){abstainedFolds++;continue;}
    const transfer=assessContextTransferability(selection,recent,picked.context,options);
    if(!transfer.passes){abstainedFolds++;continue;}
    const conditionedTrain=applyIntradayContext(fold.train,picked.context).map(r=>projectRow(r,picked.featureKeys));
    const conditionedTest=applyIntradayContext(fold.test,picked.context).map(r=>projectRow(r,picked.featureKeys));
    if(!conditionedTrain.length||!conditionedTest.length){abstainedFolds++;continue;}
    const m=picked.modelSelection;
    const model=trainModel({rows:conditionedTrain,modelType:m.modelType,options:m.options});
    const s=score(conditionedTest,model,m.threshold,costs);
    outer.push(Object.freeze({fold:fold.fold,context:picked.context.key,selectedFeatureFamily:picked.featureFamily,transferability:transfer,...s,outerUntouchedBySelection:true}));
  }
  const signalCount=outer.reduce((n,r)=>n+r.signalCount,0);
  const hitRate=signalCount?outer.reduce((n,r)=>n+(r.hitRate??0)*r.signalCount,0)/signalCount:null;
  const netAverageReturn=signalCount?outer.reduce((n,r)=>n+(r.netAverageReturn??0)*r.signalCount,0)/signalCount:null;
  return Object.freeze({
    phase:'57.p20.7',
    status:outer.length?'TRANSFERABILITY_GATED_OOS_READY':'ABSTAIN_ALL_FOLDS',
    outerResults:Object.freeze(outer),
    eligibleFolds:outer.length,
    abstainedFolds,
    signalCount,
    hitRate,
    netAverageReturn,
    selectionIntegrity:Object.freeze({contextSelectedOnPastTrainSegmentOnly:true,transferabilityUsesRecentTrainSegmentOnly:true,transferabilityUsesLabels:false,featureFamilySelectedOnPastTrainSegmentOnly:true,modelFamilySelectedOnPastTrainSegmentOnly:true,thresholdSelectedOnPastTrainSegmentOnly:true,outerTestNeverUsedForSelection:true,outerTestNeverUsedForFit:true}),
    ...PHASE57_P20_7_SAFETY,
  });
}

export default {assessContextTransferability,evaluateNestedIntradayTransferability};
