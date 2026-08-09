import test from 'node:test';
import assert from 'node:assert/strict';
import { runPredeclaredRealIntradayReplayOos, PHASE57_P10_SAFETY } from './phase57-real-intraday-replay-oos.js';

function rows(n=80){
  return Array.from({length:n},(_,i)=>({
    symbol:['7203.T','6758.T','8306.T'][i%3], sessionDate:`2026-07-${String(1+(i%25)).padStart(2,'0')}`,
    featureCutoff:new Date(Date.UTC(2026,6,1,0,i,0)).toISOString(), outcomeAt:new Date(Date.UTC(2026,6,1,0,i+1,0)).toISOString(),
    pointInTimeValid:true, label:i%2, barrierBps:20,
    features:{returnFromOpen:i%2?0.2:-0.2,rangePosition:i%2?0.8:0.2,shortMomentum:i%2?0.1:-0.1,relativeVolume:1.2,spreadBps:4,bookImbalance:i%2?0.3:-0.3,depthImbalance:i%2?0.2:-0.2,aggressiveBuyRatio:i%2?0.7:0.3,tradeIntensity:1.1},
    interactions:{vwapFlow:i%2?0.1:-0.1,rangeBookPressure:i%2?0.1:-0.1},
  }));
}

test('blocks real OOS claim when predeclared readiness evidence is insufficient',()=>{
  const out=runPredeclaredRealIntradayReplayOos(rows(40),{protocol:{minTrainRows:10,innerMinTrainRows:5,minInnerSignals:1},readiness:{minRows:1000,minSessions:20,minSymbols:3,minMicroCoverage:0.8,minOuterSignals:200,minOuterFolds:3}});
  assert.equal(out.status,'REAL_INTRADAY_REPLAY_OOS_BLOCKED_BY_READINESS');
  assert.equal(out.nestedOos,null);
  assert.equal(out.edgeClaimAllowed,false);
});

test('exposes measured nested OOS only after readiness passes',()=>{
  const out=runPredeclaredRealIntradayReplayOos(rows(120),{protocol:{minTrainRows:20,innerMinTrainRows:10,minInnerSignals:1},readiness:{minRows:100,minSessions:20,minSymbols:3,minMicroCoverage:0.8,minOuterSignals:1,minOuterFolds:1}});
  assert.equal(out.status,'REAL_INTRADAY_REPLAY_OOS_MEASURED');
  assert.ok(out.observed);
  assert.equal(out.readiness.evidence.outerTestUntouchedBySelection,true);
  assert.equal(out.readiness.evidence.outerTestNeverUsedForFit,true);
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed']) assert.equal(out[key],false);
  assert.equal(PHASE57_P10_SAFETY.executionAllowed,false);
});
