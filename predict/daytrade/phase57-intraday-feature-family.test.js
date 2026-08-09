import test from 'node:test';
import assert from 'node:assert/strict';
import { selectInnerFeatureFamily, evaluateNestedIntradayFeatureFamily, PHASE57_P20_1_SAFETY } from './phase57-intraday-feature-family.js';

function rows(n=120){
  return Array.from({length:n},(_,i)=>({
    symbol:['7203.T','6758.T'][i%2],sessionDate:`2026-07-${String(1+(i%25)).padStart(2,'0')}`,
    featureCutoff:new Date(Date.UTC(2026,6,1,0,i,0)).toISOString(),outcomeAt:new Date(Date.UTC(2026,6,1,0,i+1,0)).toISOString(),
    pointInTimeValid:true,label:i%2,barrierBps:20,
    features:{
      returnFromOpen:i%2?0.2:-0.2,rangePosition:i%2?0.8:0.2,shortMomentum:i%2?0.1:-0.1,relativeVolume:1.1,vwapDistancePct:i%2?0.15:-0.15,
      ma5DistancePct:i%2?0.2:-0.2,ma10DistancePct:i%2?0.15:-0.15,ma20DistancePct:i%2?0.1:-0.1,ma5SlopePct:i%2?0.05:-0.05,
      rsi14:i%2?60:40,macd:i%2?0.2:-0.2,macdSignalGap:i%2?0.1:-0.1,atrPct:0.8,bbPosition:i%2?0.7:0.3,relativeVolume20:1.2,range20Position:i%2?0.75:0.25,
      openingMinutes:i%30,isOpening30:i%30<10?1:0,isLunchReturn:0,isClosing30:0,
    }
  }));
}

test('feature family is selected using inner walk-forward only',()=>{
  const sel=selectInnerFeatureFamily(rows(80),{innerMinTrainRows:20,minInnerSignals:1,thresholds:[0.5,0.6]});
  assert.equal(sel.selectionSource,'INNER_WALK_FORWARD_ONLY');
  assert.ok(sel.selected);
  assert.equal(sel.selected.selectionSource,'INNER_WALK_FORWARD_ONLY');
});

test('nested feature-family evaluation keeps outer test untouched',()=>{
  const out=evaluateNestedIntradayFeatureFamily(rows(140),{minTrainRows:40,innerMinTrainRows:20,minInnerSignals:1,thresholds:[0.5,0.6],trainFraction:0.6,testFraction:0.2});
  assert.ok(out.outerResults.length>0);
  assert.equal(out.selectionIntegrity.featureFamilySelectedOnInnerOnly,true);
  assert.equal(out.selectionIntegrity.outerTestNeverUsedForSelection,true);
  assert.equal(out.selectionIntegrity.outerTestNeverUsedForFit,true);
});

test('P20.1 remains research-only',()=>{
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed']) assert.equal(PHASE57_P20_1_SAFETY[key],false);
});
