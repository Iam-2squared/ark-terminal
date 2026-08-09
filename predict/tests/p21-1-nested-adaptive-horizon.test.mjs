import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PHASE57_P21_1_SAFETY,
  selectInnerAdaptiveHorizon,
  evaluateNestedAdaptiveHorizon,
} from '../daytrade/phase57-nested-adaptive-horizon.js';

const testOptions={
  featureFamilies:{FULL:null},
  modelConfigs:[{id:'TEST',type:'TEST',options:{}}],
  thresholds:[0.55],
  innerTrainFraction:0.5,
  innerTestFraction:0.2,
  innerMinTrainRows:8,
  outerTrainFraction:0.6,
  outerTestFraction:0.1,
  outerMinTrainRows:20,
  minInnerSignals:5,
  minimumInnerNetReturnPct:0,
  roundTripCostPct:0.05,
  fitPredictor:()=>()=>0.9,
};

function horizonRows(horizonBars,{n=80,positive=true,outerShockFrom=null}={}){
  return Array.from({length:n},(_,i)=>{
    const featureCutoff=new Date(Date.UTC(2026,0,5,0,i*5));
    const outcomeAt=new Date(featureCutoff.getTime()+horizonBars*5*60*1000);
    const shock=outerShockFrom!==null&&i>=outerShockFrom;
    const up=shock?!positive:positive;
    const actualReturnPct=up?0.40:-0.40;
    return {
      symbol:'7203.T',sessionDate:'2026-01-05',outcomeSessionDate:'2026-01-05',intradayOnly:true,
      featureCutoff:featureCutoff.toISOString(),outcomeAt:outcomeAt.toISOString(),pointInTimeValid:true,
      horizonBars,label:actualReturnPct>=0?1:0,actualReturnPct,features:{edge:i/100},
    };
  });
}

test('P21.1 selects the positive-net horizon using inner walk-forward only',()=>{
  const result=selectInnerAdaptiveHorizon({
    1:horizonRows(1,{positive:true}),
    3:horizonRows(3,{positive:false}),
  },testOptions);
  assert.ok(result.selected);
  assert.equal(result.selected.horizonBars,1);
  assert.ok(result.selected.netAverageReturnPct>0);
  assert.equal(result.selectionSource,'INNER_WALK_FORWARD_ONLY');
  assert.equal(result.outerDataUsedForSelection,false);
});

test('changing first-fold outer observations cannot change its inner horizon selection',()=>{
  const baseline=evaluateNestedAdaptiveHorizon({
    1:horizonRows(1,{positive:true}),
    3:horizonRows(3,{positive:false}),
  },testOptions);
  assert.ok(baseline.outerResults.length>0);
  const first=baseline.outerResults[0];
  assert.equal(first.status,'OUTER_EVALUATED');

  const testStartIndex=Math.round((Date.parse(first.testStart)-Date.UTC(2026,0,5,0,0))/300000);
  const changed=evaluateNestedAdaptiveHorizon({
    1:horizonRows(1,{positive:true,outerShockFrom:testStartIndex}),
    3:horizonRows(3,{positive:false,outerShockFrom:testStartIndex}),
  },testOptions);
  assert.equal(changed.outerResults[0].selectedHorizonBars,first.selectedHorizonBars);
  assert.equal(changed.outerResults[0].selectedThreshold,first.selectedThreshold);
  assert.equal(changed.outerResults[0].outerUntouchedBySelection,true);
});

test('nested result records strict outer-OOS and intraday-only integrity',()=>{
  const result=evaluateNestedAdaptiveHorizon({
    1:horizonRows(1,{positive:true}),
    3:horizonRows(3,{positive:false}),
  },testOptions);
  assert.equal(result.selectionIntegrity.horizonSelectedOnInnerOnly,true);
  assert.equal(result.selectionIntegrity.featureFamilySelectedOnInnerOnly,true);
  assert.equal(result.selectionIntegrity.modelFamilySelectedOnInnerOnly,true);
  assert.equal(result.selectionIntegrity.thresholdSelectedOnInnerOnly,true);
  assert.equal(result.selectionIntegrity.outerTestNeverUsedForSelection,true);
  assert.equal(result.selectionIntegrity.outerTestNeverUsedForFit,true);
  assert.equal(result.selectionIntegrity.sameSessionOnly,true);
  assert.equal(result.selectionIntegrity.overnightHoldingForbidden,true);
});

test('negative-net horizons abstain instead of forcing a selection',()=>{
  const result=selectInnerAdaptiveHorizon({3:horizonRows(3,{positive:false})},testOptions);
  assert.equal(result.selected,null);
  assert.ok(result.bestObserved);
  assert.ok(result.bestObserved.netAverageReturnPct<0);
});

test('cross-session outcomes are rejected from P21.1 candidates',()=>{
  const bad=horizonRows(1,{n:30,positive:true}).map(row=>({...row,outcomeSessionDate:'2026-01-06'}));
  const result=selectInnerAdaptiveHorizon({1:bad},testOptions);
  assert.equal(result.selected,null);
  assert.equal(result.candidates.length,0);
});

test('P21.1 keeps every write/trading path disabled and forbids overnight holding',()=>{
  for(const key of [
    'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
    'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed',
  ]) assert.equal(PHASE57_P21_1_SAFETY[key],false);
  assert.equal(PHASE57_P21_1_SAFETY.overnightHoldingAllowed,false);
});
