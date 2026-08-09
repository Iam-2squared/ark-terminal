import test from 'node:test';
import assert from 'node:assert/strict';
import { buildIntradayWalkForwardFolds, evaluateIntradayWalkForward } from '../daytrade/phase57-intraday-walkforward-cost.js';

function rows(n=60){
  const out=[];
  const base=Date.parse('2026-01-01T00:00:00Z');
  for(let i=0;i<n;i++){
    const cutoff=new Date(base+i*60000).toISOString();
    const outcome=new Date(base+(i+1)*60000).toISOString();
    out.push({symbol:i%2?'7203.T':'8306.T',featureCutoff:cutoff,outcomeAt:outcome,label:i%2,barrierBps:20,pointInTimeValid:true,features:{momentum3:i%2?1:-1}});
  }
  return out;
}

test('P5 builds expanding walk-forward folds and resolves outcomes before train cutoff',()=>{
  const folds=buildIntradayWalkForwardFolds(rows(),{trainFraction:.5,testFraction:.2,minTrainRows:10});
  assert.ok(folds.length>=2);
  for(const fold of folds){
    for(const row of fold.train) assert.ok(Date.parse(row.outcomeAt)<=Date.parse(fold.trainCutoff));
    for(const row of fold.test) assert.ok(Date.parse(row.featureCutoff)>=Date.parse(fold.testStart));
  }
});

test('P5 evaluates untouched OOS signals with explicit costs',()=>{
  const r=evaluateIntradayWalkForward(rows(),{
    trainFraction:.5,testFraction:.2,minTrainRows:10,threshold:.5,feePercent:.01,slippagePercent:.02,delayCostPercent:.01,
    fitPredictor:()=>row=>row.features.momentum3>0?.8:.2,
  });
  assert.equal(r.status,'INTRADAY_WALK_FORWARD_OOS_READY');
  assert.equal(r.hitRate,1);
  assert.equal(r.pointInTime.trainingRequiresOutcomeAtOnOrBeforeFoldCutoff,true);
  assert.equal(r.pointInTime.testRowsNeverUsedForFit,true);
  assert.equal(r.outerOnly,true);
  assert.ok(r.costAware.netAverageReturn<r.costAware.grossAverageReturn);
  assert.ok(r.costAware.profitFactor>1);
});

test('P5 cannot write, trade, promote or update production',()=>{
  const r=evaluateIntradayWalkForward(rows(),{trainFraction:.5,testFraction:.2,minTrainRows:10,threshold:.5,fitPredictor:()=>()=>.8});
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed']) assert.equal(r[key],false,key);
  assert.equal(r.paperTradingAllowed,false);
  assert.equal(r.transmitted,false);
  assert.equal(r.humanApprovalRequired,true);
});
