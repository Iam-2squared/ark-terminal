import test from 'node:test';
import assert from 'node:assert/strict';
import { evaluateNestedAdaptiveHorizon } from '../daytrade/phase57-nested-adaptive-horizon.js';
import { replayNestedAdaptiveOosSignals, PHASE57_P21_3_SIGNAL_REPLAY_SAFETY } from '../daytrade/phase57-adaptive-oos-signal-replay.js';
import { evaluateNestedRealExitOos, SAFE_REAL_EXIT_POLICIES, PHASE57_P21_3_REAL_EXIT_SAFETY } from '../daytrade/phase57-real-exit-oos.js';

const adaptiveOptions={
  featureFamilies:{FULL:null},modelConfigs:[{id:'TEST',type:'TEST',options:{}}],thresholds:[0.55],
  innerTrainFraction:0.5,innerTestFraction:0.2,innerMinTrainRows:8,
  outerTrainFraction:0.6,outerTestFraction:0.1,outerMinTrainRows:20,
  minInnerSignals:5,minimumInnerNetReturnPct:0,roundTripCostPct:0.05,
  fitPredictor:()=>()=>0.9,
};

function horizonRows(horizonBars,{n=80,positive=true}={}){
  return Array.from({length:n},(_,i)=>{
    const featureCutoff=new Date(Date.UTC(2026,0,5,0,i*5));
    const outcomeAt=new Date(featureCutoff.getTime()+horizonBars*5*60*1000);
    const actualReturnPct=positive?0.4:-0.4;
    return {
      symbol:'7203.T',sessionDate:'2026-01-05',outcomeSessionDate:'2026-01-05',intradayOnly:true,
      featureCutoff:featureCutoff.toISOString(),outcomeAt:outcomeAt.toISOString(),pointInTimeValid:true,
      horizonBars,label:actualReturnPct>=0?1:0,actualReturnPct,features:{edge:i/100},
    };
  });
}

test('adaptive signal replay exactly reconciles the P21.1 outer OOS result',()=>{
  const datasets={1:horizonRows(1,{positive:true}),3:horizonRows(3,{positive:false})};
  const reference=evaluateNestedAdaptiveHorizon(datasets,adaptiveOptions);
  const replay=replayNestedAdaptiveOosSignals(datasets,{...adaptiveOptions,referenceResult:reference});
  assert.ok(reference.signalCount>0);
  assert.equal(replay.signalCount,reference.signalCount);
  assert.equal(replay.reconciliation.matches,true);
  assert.equal(replay.signals.length,replay.signalCount);
  assert.ok(replay.signals.every(signal=>signal.signalPointInTimeValid&&signal.selectionSource==='P21_1_OUTER_OOS_REPLAY'));
  assert.equal(replay.selectionIntegrity.outerTestNeverUsedForSelection,true);
});

function exitRows(n=100){
  return Array.from({length:n},(_,i)=>{
    const featureCutoff=new Date(Date.UTC(2026,0,5,0,i*30));
    const futureBars=Array.from({length:24},(_,j)=>{
      const timestamp=new Date(featureCutoff.getTime()+(j+1)*5*60*1000).toISOString();
      const close=j<3?100+(j+1)*0.3:100.1;
      return {timestamp,open:close,high:close+0.05,low:close-0.05,close,volume:1000};
    });
    return {
      symbol:'7203.T',sessionDate:'2026-01-05',outcomeSessionDate:'2026-01-05',
      featureCutoff:featureCutoff.toISOString(),outcomeAt:futureBars.at(-1).timestamp,label:1,
      pointInTimeValid:true,signalPointInTimeValid:true,entryPrice:100,signalDirection:1,
      baseHorizonBars:24,atrPctAtEntry:0.5,futureBars,
    };
  });
}

test('real exit OOS selects on inner rows and compares against the matched adaptive baseline',()=>{
  const result=evaluateNestedRealExitOos(exitRows(),{
    policies:[{id:'FAST',type:'FIXED',maxBars:3},{id:'SLOW',type:'FIXED',maxBars:24}],
    minSignals:5,minimumNetReturnPct:0,roundTripCostPct:0.05,
    outerTrainFraction:0.6,outerTestFraction:0.1,outerMinTrainRows:20,
    innerTrainFraction:0.5,innerTestFraction:0.2,innerMinTrainRows:8,
  });
  assert.ok(result.optimized.signalCount>0);
  assert.ok(result.baselineMatched.signalCount>0);
  assert.equal(result.optimized.signalCount,result.baselineMatched.signalCount);
  assert.ok(result.deltaMatchedNetAverageReturnPct>0);
  assert.ok(Object.keys(result.selectedPolicyCounts).includes('FAST'));
  assert.equal(result.selectionIntegrity.outerExitTestNeverUsedForSelection,true);
  assert.equal(result.selectionIntegrity.baselineComparedOnMatchedOuterRows,true);
});

test('real 5m exit policy universe quarantines trailing stops until intrabar ordering is conservative',()=>{
  assert.equal(SAFE_REAL_EXIT_POLICIES.some(policy=>policy.type==='TRAILING'),false);
});

test('P21.3 real exit and signal replay keep all execution/write paths disabled',()=>{
  for(const safety of [PHASE57_P21_3_SIGNAL_REPLAY_SAFETY,PHASE57_P21_3_REAL_EXIT_SAFETY]){
    for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed']){
      assert.equal(safety[key],false);
    }
    assert.equal(safety.overnightHoldingAllowed,false);
  }
});
