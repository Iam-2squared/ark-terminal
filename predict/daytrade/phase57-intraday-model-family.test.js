import test from 'node:test';
import assert from 'node:assert/strict';
import { selectInnerIntradayModelFamily, evaluateNestedIntradayModelFamily } from './phase57-intraday-model-family.js';

const row=(n,label)=>({id:`7203.T:${n}`,symbol:'7203.T',sessionDate:'2026-08-08',featureCutoff:new Date(Date.UTC(2026,7,8,0,n,0)).toISOString(),outcomeAt:new Date(Date.UTC(2026,7,8,0,n+1,0)).toISOString(),label,barrierBps:20,pointInTimeValid:true,features:{retFromOpen:label?0.3:-0.3,rangePosition:label?0.8:0.2,momentum3:label?0.2:-0.2,lastBarRelativeVolume:1.3,spreadBps:4,bookImbalance:label?0.35:-0.35,depthImbalance:label?0.25:-0.25,aggressiveBuyRatio:label?0.7:0.3,tradeIntensity:1.2}});

test('model family selection is inner-walk-forward only',()=>{
  const rows=Array.from({length:80},(_,i)=>row(i,i%2));
  const out=selectInnerIntradayModelFamily(rows,{innerMinTrainRows:20,minInnerSignals:1});
  assert.equal(out.selectionSource,'INNER_WALK_FORWARD_ONLY');
  assert.ok(out.innerFoldCount>0);
  assert.ok(['LOGISTIC_REGRESSION','RANDOM_FOREST','GRADIENT_BOOSTING'].includes(out.selected.modelType));
});

test('outer evaluation remains untouched and all trade paths stay disabled',()=>{
  const rows=Array.from({length:120},(_,i)=>row(i,i%2));
  const out=evaluateNestedIntradayModelFamily(rows,{trainFraction:0.6,testFraction:0.1,minTrainRows:20,innerMinTrainRows:20});
  assert.equal(out.selectionIntegrity.modelFamilySelectedOnInnerOnly,true);
  assert.equal(out.selectionIntegrity.thresholdSelectedOnInnerOnly,true);
  assert.equal(out.selectionIntegrity.outerTestNeverUsedForSelection,true);
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed']) assert.equal(out[key],false,key);
});
