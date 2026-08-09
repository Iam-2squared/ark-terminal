import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PHASE57_P21_2_SAFETY,
  fitMagnitudePredictor,
  evaluateNestedMagnitudePrediction,
} from '../daytrade/phase57-magnitude-prediction.js';

function rows({n=60,shockFrom=null,shockValue=5}={}){
  return Array.from({length:n},(_,i)=>{
    const featureCutoff=new Date(Date.UTC(2026,0,5,0,i*5));
    const outcomeAt=new Date(featureCutoff.getTime()+5*60*1000);
    const base=0.2+(i%10)*0.12;
    const actualReturnPct=shockFrom!==null&&i>=shockFrom?shockValue:base;
    return {
      symbol:'7203.T',sessionDate:'2026-01-05',outcomeSessionDate:'2026-01-05',intradayOnly:true,
      featureCutoff:featureCutoff.toISOString(),outcomeAt:outcomeAt.toISOString(),pointInTimeValid:true,
      horizonBars:1,label:actualReturnPct>=0?1:0,actualReturnPct,absMovePct:Math.abs(actualReturnPct),
      mfePct:Math.abs(actualReturnPct)+0.15,maePct:-0.10-(i%3)*0.02,
      features:{x:i/100,vol:(i%10)/10},
    };
  });
}

test('P21.2 kNN baseline predicts return, absolute move, MFE, MAE and move probabilities',()=>{
  const model=fitMagnitudePredictor(rows({n:40}),{k:8,moveThresholdsPct:[0.5,1,2,3]});
  assert.ok(model);
  const prediction=model.predict(rows({n:41})[40]);
  assert.ok(Number.isFinite(prediction.expectedReturnPct));
  assert.ok(Number.isFinite(prediction.expectedAbsMovePct));
  assert.ok(Number.isFinite(prediction.expectedMfePct));
  assert.ok(Number.isFinite(prediction.expectedMaePct));
  for(const threshold of ['0.5','1','2','3']){
    assert.ok(prediction.probabilityMoveGtPct[threshold]>=0);
    assert.ok(prediction.probabilityMoveGtPct[threshold]<=1);
  }
  assert.equal(model.fitSource,'PRE_OUTER_TRAIN_ONLY');
});

test('outer outcomes cannot alter magnitude predictions fitted before the outer cutoff',()=>{
  const baselineRows=rows();
  const adaptiveResult={
    status:'NESTED_ADAPTIVE_HORIZON_OOS_READY',
    outerResults:[{
      fold:0,status:'OUTER_EVALUATED',selectedHorizonBars:1,
      trainCutoff:baselineRows[39].featureCutoff,
      testStart:baselineRows[40].featureCutoff,
      testEnd:baselineRows[49].featureCutoff,
    }],
  };
  const baseline=evaluateNestedMagnitudePrediction({1:baselineRows},{adaptiveResult,k:8});
  const shocked=evaluateNestedMagnitudePrediction({1:rows({shockFrom:40,shockValue:9})},{adaptiveResult,k:8});
  assert.equal(baseline.status,'NESTED_MAGNITUDE_OOS_READY');
  assert.equal(shocked.status,'NESTED_MAGNITUDE_OOS_READY');
  assert.deepEqual(shocked.predictedMoveRateByThreshold,baseline.predictedMoveRateByThreshold);
  assert.notEqual(shocked.expectedReturnMaePct,baseline.expectedReturnMaePct);
  assert.equal(baseline.foldResults[0].outerUntouchedByFit,true);
  assert.equal(baseline.foldResults[0].outerUntouchedByMagnitudeCalibration,true);
});

test('P21.2 reports Brier scores and 0.5/1/2/3 percent opportunity rates',()=>{
  const data=rows();
  const adaptiveResult={
    status:'NESTED_ADAPTIVE_HORIZON_OOS_READY',
    outerResults:[{
      fold:0,status:'OUTER_EVALUATED',selectedHorizonBars:1,
      trainCutoff:data[39].featureCutoff,testStart:data[40].featureCutoff,testEnd:data[49].featureCutoff,
    }],
  };
  const result=evaluateNestedMagnitudePrediction({1:data},{adaptiveResult,k:10});
  assert.deepEqual(result.moveThresholdsPct,[0.5,1,2,3]);
  for(const threshold of ['0.5','1','2','3']){
    const b=result.probabilityBrierByThreshold[threshold];
    assert.ok(b===null||(b>=0&&b<=1));
    assert.ok(result.actualMoveRateByThreshold[threshold]>=0&&result.actualMoveRateByThreshold[threshold]<=1);
    assert.ok(result.predictedMoveRateByThreshold[threshold]>=0&&result.predictedMoveRateByThreshold[threshold]<=1);
  }
});

test('cross-session rows are excluded from magnitude fitting',()=>{
  const bad=rows({n:20}).map(row=>({...row,outcomeSessionDate:'2026-01-06'}));
  assert.equal(fitMagnitudePredictor(bad),null);
});

test('P21.2 remains research-only and forbids overnight holding',()=>{
  for(const key of [
    'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
    'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed',
  ]) assert.equal(PHASE57_P21_2_SAFETY[key],false);
  assert.equal(PHASE57_P21_2_SAFETY.overnightHoldingAllowed,false);
});
