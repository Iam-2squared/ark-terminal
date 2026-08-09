import { buildIntradayWalkForwardFolds } from './phase57-intraday-walkforward-cost.js';
import { selectInnerFeatureFamily } from './phase57-intraday-feature-family.js';
import { trainModel } from '../models/phase47-real-training.js';
import { evaluateCostAwareStrategy } from '../strategy/cost-aware-evaluation.js';

export const PHASE57_P20_3_SAFETY = Object.freeze({
  mode: 'PHASE57_INTRADAY_CONTEXT_CONDITIONING_RESEARCH_ONLY',
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
const finite = v => Number.isFinite(Number(v));

function median(xs) {
  const a = xs.filter(finite).map(Number).sort((x,y)=>x-y);
  if (!a.length) return 0;
  const m = Math.floor(a.length/2);
  return a.length%2 ? a[m] : (a[m-1]+a[m])/2;
}

function timeBucket(row) {
  const f = row?.features ?? {};
  if (Number(f.isOpening30) === 1) return 'OPENING';
  if (Number(f.isLunchReturn) === 1) return 'LUNCH_RETURN';
  if (Number(f.isClosing30) === 1) return 'CLOSING';
  return 'MIDSESSION';
}

function regimeBucket(row, atrMedian) {
  const f = row?.features ?? {};
  const slope = Number(f.ma5SlopePct ?? 0);
  const dist = Number(f.ma5DistancePct ?? 0);
  const atr = Number(f.atrPct ?? 0);
  if (slope > 0 && dist > 0) return atr > atrMedian ? 'TREND_UP_HIGH_VOL' : 'TREND_UP';
  if (slope < 0 && dist < 0) return atr > atrMedian ? 'TREND_DOWN_HIGH_VOL' : 'TREND_DOWN';
  return atr > atrMedian ? 'RANGE_HIGH_VOL' : 'RANGE_LOW_VOL';
}

function contextKey(symbol, regime, time) { return `${symbol}|${regime}|${time}`; }

export function buildPredeclaredIntradayContexts(trainRows = [], options = {}) {
  const symbols = [...new Set(trainRows.map(r=>r.symbol).filter(Boolean))].sort();
  const atrMedian = median(trainRows.map(r=>r?.features?.atrPct));
  const regimes = ['ALL','TREND_UP','TREND_UP_HIGH_VOL','TREND_DOWN','TREND_DOWN_HIGH_VOL','RANGE_HIGH_VOL','RANGE_LOW_VOL'];
  const times = ['ALL','OPENING','LUNCH_RETURN','CLOSING','MIDSESSION'];
  const symbolLevels = options.includeSymbolSpecific === false ? ['ALL'] : ['ALL', ...symbols];
  const contexts = [];
  for (const symbol of symbolLevels) for (const regime of regimes) for (const time of times) {
    if (symbol === 'ALL' && regime === 'ALL' && time === 'ALL') {
      contexts.push({ key: contextKey(symbol,regime,time), symbol, regime, time, atrMedian });
      continue;
    }
    const specificity = Number(symbol !== 'ALL') + Number(regime !== 'ALL') + Number(time !== 'ALL');
    if (specificity > (options.maxSpecificity ?? 2)) continue;
    contexts.push({ key: contextKey(symbol,regime,time), symbol, regime, time, atrMedian });
  }
  return Object.freeze(contexts.map(Object.freeze));
}

export function applyIntradayContext(rows = [], context) {
  if (!context) return [];
  return rows.filter(row => {
    if (context.symbol !== 'ALL' && row.symbol !== context.symbol) return false;
    if (context.regime !== 'ALL' && regimeBucket(row, context.atrMedian) !== context.regime) return false;
    if (context.time !== 'ALL' && timeBucket(row) !== context.time) return false;
    return true;
  });
}

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

function rank(a,b) {
  const an=finite(a.netAverageReturn)?Number(a.netAverageReturn):-Infinity;
  const bn=finite(b.netAverageReturn)?Number(b.netAverageReturn):-Infinity;
  if (bn!==an) return bn-an;
  const ah=finite(a.hitRate)?Number(a.hitRate):-Infinity;
  const bh=finite(b.hitRate)?Number(b.hitRate):-Infinity;
  if (bh!==ah) return bh-ah;
  return (b.signalCount??0)-(a.signalCount??0);
}

export function selectInnerIntradayContext(trainRows = [], options = {}) {
  const contexts=buildPredeclaredIntradayContexts(trainRows, options.context);
  const minContextRows=options.minContextRows ?? 120;
  const minContextSignals=options.minContextSignals ?? 20;
  const candidates=[];
  for (const context of contexts) {
    const rows=applyIntradayContext(trainRows, context);
    if (rows.length < minContextRows) continue;
    const selected=selectInnerFeatureFamily(rows, options);
    const s=selected?.selected?.selected;
    if (!s) continue;
    candidates.push({
      context,
      rowCount: rows.length,
      featureFamily: selected.selected.family,
      featureKeys: selected.selected.keys,
      modelSelection: s,
      signalCount: s.signalCount ?? 0,
      hitRate: s.hitRate ?? null,
      netAverageReturn: s.netAverageReturn ?? null,
      selectionSource: 'INNER_WALK_FORWARD_ONLY',
    });
  }
  const eligible=candidates.filter(c=>c.signalCount>=minContextSignals).sort(rank);
  return Object.freeze({
    selected: eligible[0] ? Object.freeze(eligible[0]) : null,
    candidates: Object.freeze(candidates.map(Object.freeze)),
    selectionSource: 'INNER_WALK_FORWARD_ONLY',
  });
}

function projectRow(row, keys) {
  if (!keys) return row;
  const features=Object.fromEntries(keys.filter(k=>finite(row?.features?.[k])).map(k=>[k,Number(row.features[k])]));
  return {...row,features};
}

export function evaluateNestedIntradayContextConditioning(rows = [], options = {}) {
  const folds=buildIntradayWalkForwardFolds(rows,{trainFraction:options.trainFraction??0.6,testFraction:options.testFraction??0.1,minTrainRows:options.minTrainRows??200});
  const costs={feePercent:options.feePercent??0,slippagePercent:options.slippagePercent??0.05,delayCostPercent:options.delayCostPercent??0};
  const outer=[];
  for (const fold of folds) {
    const contextSel=selectInnerIntradayContext(fold.train, options);
    const picked=contextSel.selected;
    if (!picked) continue;
    const conditionedTrain=applyIntradayContext(fold.train,picked.context).map(r=>projectRow(r,picked.featureKeys));
    const conditionedTest=applyIntradayContext(fold.test,picked.context).map(r=>projectRow(r,picked.featureKeys));
    if (!conditionedTrain.length || !conditionedTest.length) continue;
    const m=picked.modelSelection;
    const model=trainModel({rows:conditionedTrain,modelType:m.modelType,options:m.options});
    const s=score(conditionedTest,model,m.threshold,costs);
    outer.push(Object.freeze({
      fold:fold.fold,
      context:picked.context.key,
      symbolCondition:picked.context.symbol,
      regimeCondition:picked.context.regime,
      timeCondition:picked.context.time,
      selectedFeatureFamily:picked.featureFamily,
      selectedModelType:m.modelType,
      selectedThreshold:m.threshold,
      trainRows:conditionedTrain.length,
      testRows:conditionedTest.length,
      ...s,
      outerUntouchedBySelection:true,
    }));
  }
  const signalCount=outer.reduce((n,r)=>n+r.signalCount,0);
  const hitRate=signalCount?outer.reduce((n,r)=>n+(r.hitRate??0)*r.signalCount,0)/signalCount:null;
  const netAverageReturn=signalCount?outer.reduce((n,r)=>n+(r.netAverageReturn??0)*r.signalCount,0)/signalCount:null;
  return Object.freeze({
    phase:'57.p20.3',
    status:outer.length?'NESTED_INTRADAY_CONTEXT_OOS_READY':'NO_CONTEXT_FOLDS',
    outerResults:Object.freeze(outer),signalCount,hitRate,netAverageReturn,
    selectionIntegrity:Object.freeze({contextSelectedOnInnerOnly:true,featureFamilySelectedOnInnerOnly:true,modelFamilySelectedOnInnerOnly:true,thresholdSelectedOnInnerOnly:true,outerTestNeverUsedForSelection:true,outerTestNeverUsedForFit:true}),
    recommendationAllowed:false,paperTradingAllowed:false,executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,humanApprovalRequired:true,safety:PHASE57_P20_3_SAFETY,
  });
}

export default {buildPredeclaredIntradayContexts,applyIntradayContext,selectInnerIntradayContext,evaluateNestedIntradayContextConditioning};
