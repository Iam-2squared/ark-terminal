import test from 'node:test';
import assert from 'node:assert/strict';
import { selectInnerIntradayConfig, evaluateNestedIntradaySelection } from './phase57-intraday-nested-selection.js';

const row=(n,label)=>({symbol:'7203.T',sessionDate:'2026-08-08',featureCutoff:new Date(Date.UTC(2026,7,8,0,n,0)).toISOString(),outcomeAt:new Date(Date.UTC(2026,7,8,0,n+1,0)).toISOString(),label,barrierBps:20,pointInTimeValid:true,features:{returnFromOpen:label?0.3:-0.3,rangePosition:label?0.8:0.2,shortMomentum:label?0.2:-0.2,relativeVolume:1.3,spreadBps:4,bookImbalance:label?0.35:-0.35,depthImbalance:label?0.25:-0.25,aggressiveBuyRatio:label?0.7:0.3,tradeIntensity:1.2},interactions:{vwapFlow:label?0.2:-0.2,rangeBookPressure:label?0.15:-0.15}});

test('inner selection uses validation-only contract',()=>{
  const rows=Array.from({length:60},(_,i)=>row(i,i%2));
  const selected=selectInnerIntradayConfig(rows,{minInnerTrainRows:20});
  assert.equal(selected.selectionSource,'INNER_VALIDATION_ONLY');
  assert.ok([0.55,0.60,0.65].includes(selected.threshold));
});

test('outer test remains untouched and trading locks stay false',()=>{
  const rows=Array.from({length:100},(_,i)=>row(i,i%2));
  const out=evaluateNestedIntradaySelection(rows,{trainFraction:0.6,testFraction:0.1,minTrainRows:20,minInnerTrainRows:20});
  assert.equal(out.pointInTime.innerSelectionOnly,true);
  assert.equal(out.pointInTime.outerTestUntouchedBySelection,true);
  assert.equal(out.pointInTime.thresholdNeverSelectedOnOuter,true);
  assert.equal(out.pointInTime.modelHyperparametersNeverSelectedOnOuter,true);
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed']) assert.equal(out[key],false,key);
});
