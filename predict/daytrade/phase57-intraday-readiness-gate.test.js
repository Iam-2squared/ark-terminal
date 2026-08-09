import test from 'node:test';
import assert from 'node:assert/strict';
import { assessIntradayResearchReadiness, PHASE57_P9_SAFETY } from './phase57-intraday-readiness-gate.js';

function row(i, symbol='7203.T') {
  const t = new Date(Date.UTC(2026,7,1 + Math.floor(i/10),0,i%10,0));
  const outcome = new Date(t.getTime()+60000);
  return { symbol, sessionDate:t.toISOString().slice(0,10), featureCutoff:t.toISOString(), outcomeAt:outcome.toISOString(), pointInTimeValid:true, features:{spreadBps:4,bookImbalance:.2,depthImbalance:.1,aggressiveBuyRatio:.6,tradeIntensity:1.2} };
}

test('readiness gate blocks insufficient evidence instead of claiming edge',()=>{
  const rows = Array.from({length:30},(_,i)=>row(i));
  const out = assessIntradayResearchReadiness({rows,nestedOos:{signalCount:5,outerFoldCount:1,selectionIntegrity:{outerTestNeverUsedForSelection:true,outerTestNeverUsedForFit:true}}});
  assert.equal(out.status,'INTRADAY_RESEARCH_DATA_NOT_READY');
  assert.ok(out.blockers.includes('INSUFFICIENT_POINT_IN_TIME_ROWS'));
  assert.equal(out.edgeClaimAllowed,false);
});

test('readiness can pass only when point-in-time, diversity, microstructure and untouched OOS evidence are sufficient',()=>{
  const symbols=['7203.T','6758.T','8306.T'];
  const rows = Array.from({length:120},(_,i)=>row(i,symbols[i%symbols.length]));
  const out = assessIntradayResearchReadiness({rows,nestedOos:{signalCount:60,outerFoldCount:4,selectionIntegrity:{outerTestNeverUsedForSelection:true,outerTestNeverUsedForFit:true}},config:{minRows:100,minSessions:10,minSymbols:3,minMicroCoverage:.8,minOuterSignals:50,minOuterFolds:3}});
  assert.equal(out.status,'INTRADAY_RESEARCH_EVIDENCE_READY');
  assert.equal(out.nextStep,'RUN_PREDECLARED_REAL_REPLAY_OOS');
});

test('all trading and write permissions stay disabled',()=>{
  const out=assessIntradayResearchReadiness();
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed']) assert.equal(out[key],false,key);
  assert.equal(PHASE57_P9_SAFETY.executionAllowed,false);
});
