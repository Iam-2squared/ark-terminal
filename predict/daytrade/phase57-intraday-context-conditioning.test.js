import test from 'node:test';
import assert from 'node:assert/strict';
import { buildPredeclaredIntradayContexts, applyIntradayContext, evaluateNestedIntradayContextConditioning, PHASE57_P20_3_SAFETY } from './phase57-intraday-context-conditioning.js';

function row(i,symbol='7203.T'){
  const up=i%2===0;
  return {
    symbol,
    sessionDate:`2026-08-${String(1+(i%20)).padStart(2,'0')}`,
    featureCutoff:new Date(Date.UTC(2026,7,1,0,i,0)).toISOString(),
    outcomeAt:new Date(Date.UTC(2026,7,1,0,i+1,0)).toISOString(),
    label:up?1:0,barrierBps:20,pointInTimeValid:true,
    features:{returnFromOpen:up?0.2:-0.2,rangePosition:up?0.8:0.2,shortMomentum:up?0.1:-0.1,relativeVolume:1.1,vwapDistancePct:up?0.15:-0.15,ma5DistancePct:up?0.2:-0.2,ma10DistancePct:up?0.15:-0.15,ma20DistancePct:up?0.1:-0.1,ma5SlopePct:up?0.05:-0.05,rsi14:up?60:40,macd:up?0.1:-0.1,macdSignalGap:up?0.05:-0.05,atrPct:i%3===0?1.2:0.5,bbPosition:up?0.7:0.3,relativeVolume20:1.1,range20Position:up?0.7:0.3,openingMinutes:i%4===0?10:120,isOpening30:i%4===0?1:0,isLunchReturn:i%4===1?1:0,isClosing30:i%4===2?1:0},
    interactions:{vwapFlow:0,rangeBookPressure:0},
  };
}

test('predeclared contexts are derived from train rows only',()=>{
  const rows=[...Array.from({length:20},(_,i)=>row(i,'7203.T')),...Array.from({length:20},(_,i)=>row(i+20,'6758.T'))];
  const contexts=buildPredeclaredIntradayContexts(rows,{maxSpecificity:2});
  assert.ok(contexts.some(c=>c.symbol==='7203.T'));
  assert.ok(contexts.some(c=>c.regime==='TREND_UP'));
  assert.ok(contexts.some(c=>c.time==='OPENING'));
  const opening=contexts.find(c=>c.symbol==='ALL'&&c.regime==='ALL'&&c.time==='OPENING');
  assert.ok(applyIntradayContext(rows,opening).every(r=>r.features.isOpening30===1));
});

test('nested context evaluation keeps outer test untouched',()=>{
  const rows=Array.from({length:180},(_,i)=>row(i,i%3===0?'6758.T':'7203.T'));
  const out=evaluateNestedIntradayContextConditioning(rows,{trainFraction:0.6,testFraction:0.1,minTrainRows:40,innerTrainFraction:0.6,innerTestFraction:0.15,innerMinTrainRows:20,thresholds:[0.5,0.55],minInnerSignals:1,minContextRows:20,minContextSignals:1,context:{maxSpecificity:1}});
  assert.equal(out.phase,'57.p20.3');
  assert.equal(out.selectionIntegrity.contextSelectedOnInnerOnly,true);
  assert.equal(out.selectionIntegrity.outerTestNeverUsedForSelection,true);
  assert.equal(out.selectionIntegrity.outerTestNeverUsedForFit,true);
});

test('P20.3 remains research only',()=>{
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed']) assert.equal(PHASE57_P20_3_SAFETY[key],false);
});
