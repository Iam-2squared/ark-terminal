import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PHASE57_P21_3_SAFETY,
  simulateIntradayExit,
  evaluateExitPolicy,
  selectInnerExitPolicy,
  evaluateNestedExitOptimization,
} from '../daytrade/phase57-exit-optimization.js';

function bar(timestamp,{open=100,high=100,low=100,close=100}={}){return{timestamp,open,high,low,close,volume:1000};}

function makeRows({n=90,outerShockFrom=null}={}){
  return Array.from({length:n},(_,i)=>{
    const featureCutoff=new Date(Date.UTC(2026,0,5,0,i*30));
    const futureBars=Array.from({length:24},(_,j)=>{
      const timestamp=new Date(featureCutoff.getTime()+(j+1)*5*60*1000).toISOString();
      const earlyUp=j<3?100+(j+1)*0.25:100.75;
      const later=outerShockFrom!==null&&i>=outerShockFrom?98:earlyUp;
      return bar(timestamp,{open:100,high:later+0.10,low:later-0.10,close:later});
    });
    return {
      symbol:'7203.T',sessionDate:'2026-01-05',outcomeSessionDate:'2026-01-05',
      featureCutoff:featureCutoff.toISOString(),outcomeAt:futureBars.at(-1).timestamp,
      pointInTimeValid:true,signalPointInTimeValid:true,label:1,entryPrice:100,signalDirection:1,
      atrPctAtEntry:0.5,futureBars,
    };
  });
}

test('TP/SL uses conservative stop-first handling when both barriers touch in one bar',()=>{
  const featureCutoff='2026-01-05T00:00:00.000Z';
  const row={entryPrice:100,signalDirection:1,futureBars:[bar('2026-01-05T00:05:00.000Z',{open:100,high:101.2,low:98.8,close:100})]};
  const result=simulateIntradayExit(row,{id:'B',type:'TP_SL',takeProfitPct:1,stopLossPct:1,maxBars:1},{roundTripCostPct:0.05});
  assert.equal(result.exitReason,'AMBIGUOUS_BAR_STOP_FIRST');
  assert.equal(result.exitPrice,99);
  assert.ok(result.netReturnPct<0);
});

test('fixed exit and trailing exit return realized same-session outcomes net of cost',()=>{
  const row=makeRows({n:1})[0];
  const fixed=simulateIntradayExit(row,{id:'F',type:'FIXED',maxBars:3},{roundTripCostPct:0.05});
  const trailing=simulateIntradayExit(row,{id:'T',type:'TRAILING',trailingPct:0.5,maxBars:24},{roundTripCostPct:0.05});
  assert.equal(fixed.barsHeld,3);
  assert.ok(fixed.netReturnPct>0);
  assert.ok(trailing.barsHeld>=1&&trailing.barsHeld<=24);
  assert.ok(Number.isFinite(trailing.netReturnPct));
});

test('inner exit selection maximizes net expectancy subject to sample sufficiency',()=>{
  const rows=makeRows({n:50});
  const policies=[
    {id:'FAST',type:'FIXED',maxBars:3},
    {id:'SLOW',type:'FIXED',maxBars:24},
  ];
  const result=selectInnerExitPolicy(rows,{policies,minSignals:20,minimumNetReturnPct:0,roundTripCostPct:0.05});
  assert.ok(result.selected);
  assert.equal(result.selected.id,'FAST');
  assert.equal(result.selectionSource,'INNER_ONLY');
  assert.equal(result.outerDataUsedForSelection,false);
});

test('negative-net candidates abstain instead of forcing an exit policy',()=>{
  const rows=makeRows({n:40}).map(row=>({...row,futureBars:row.futureBars.map(b=>({...b,open:99,high:99.1,low:98.9,close:99}))}));
  const result=selectInnerExitPolicy(rows,{policies:[{id:'LOSE',type:'FIXED',maxBars:3}],minSignals:20,minimumNetReturnPct:0,roundTripCostPct:0.05});
  assert.equal(result.selected,null);
  assert.ok(result.bestObserved.netAverageReturnPct<0);
});

test('changing outer paths cannot change first-fold policy selected from inner data',()=>{
  const options={
    policies:[{id:'FAST',type:'FIXED',maxBars:3},{id:'SLOW',type:'FIXED',maxBars:24}],
    minSignals:5,minimumNetReturnPct:0,roundTripCostPct:0.05,
    outerTrainFraction:0.6,outerTestFraction:0.1,outerMinTrainRows:20,
    innerTrainFraction:0.5,innerTestFraction:0.2,innerMinTrainRows:8,
  };
  const baseline=evaluateNestedExitOptimization(makeRows(),options);
  assert.ok(baseline.outerResults.length>0);
  const first=baseline.outerResults.find(x=>x.status==='OUTER_EXIT_EVALUATED');
  assert.ok(first);
  const shockIndex=Math.round((Date.parse(first.testStart)-Date.UTC(2026,0,5,0,0))/(30*60*1000));
  const changed=evaluateNestedExitOptimization(makeRows({outerShockFrom:shockIndex}),options);
  const changedFirst=changed.outerResults.find(x=>x.status==='OUTER_EXIT_EVALUATED');
  assert.equal(changedFirst.selectedPolicyId,first.selectedPolicyId);
  assert.equal(changedFirst.outerUntouchedBySelection,true);
  assert.equal(changed.selectionIntegrity.outerTestNeverUsedForExitSelection,true);
});

test('cross-session research rows are rejected',()=>{
  const rows=makeRows({n:50}).map(row=>({...row,outcomeSessionDate:'2026-01-06'}));
  const result=evaluateNestedExitOptimization(rows,{outerMinTrainRows:10});
  assert.equal(result.outerFoldCount,0);
  assert.equal(result.status,'NO_OUTER_EXIT_OUTCOMES');
});

test('P21.3 keeps every trading/write path disabled and forbids overnight holding',()=>{
  for(const key of [
    'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
    'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed',
  ]) assert.equal(PHASE57_P21_3_SAFETY[key],false);
  assert.equal(PHASE57_P21_3_SAFETY.overnightHoldingAllowed,false);
});
