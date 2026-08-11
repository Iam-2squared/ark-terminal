import assert from 'node:assert/strict';
import {
  PHASE57_P23_14_SAFETY,
  stripOutcomeFields,
  buildBlindReasoningPrediction,
} from '../daytrade/phase57-p23-14-blind-reasoner-benchmark.js';

const source = {
  symbol:'TEST.T', sessionDate:'2026-08-10', featureCutoff:'2026-08-10T01:00:00.000Z',
  setup:'BREAKOUT_CONTINUATION_UP', direction:'UP', visualScore:0.70, visualBand:'V_B_GOOD',
  visualComponents:{structureCoherence:0.8,directionalPressure:0.7,wickControl:0.6,participation:0.5,extensionHealth:0.7,spaceToObstacle:0.8,volatilityTransition:0.6,setupGeometryFit:0.9},
  visualGeometry:{nearestObstacle:101}, visualNarrative:{primary:'CLEAN',observations:['OPEN_SPACE_AHEAD']},
  outcome30m:{hit:false,directionalReturnPct:-9}, outcome60m:{hit:false,directionalReturnPct:-9},
};
const stripped = stripOutcomeFields(source);
assert.equal('outcome30m' in stripped,false);
assert.equal('outcome60m' in stripped,false);
const p1 = buildBlindReasoningPrediction(source);
const p2 = buildBlindReasoningPrediction({...source,outcome30m:{hit:true,directionalReturnPct:99},outcome60m:{hit:true,directionalReturnPct:99}});
assert.deepEqual(p1,p2,'future outcome mutation must not alter blind prediction');
assert.equal(p1.direction,'UP');
assert.equal(p1.primaryScenario,'CONTINUATION_UP');
assert.equal(p1.futureOutcomeVisible,false);
assert.equal(p1.outcomeUsedForPrediction,false);
assert.equal(p1.thresholdSearchPerformed,false);
assert.equal(p1.predictionUsedAsEntryGate,false);
for (const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed','transmitted']) {
  assert.equal(PHASE57_P23_14_SAFETY[key],false,`${key} must remain false`);
  assert.equal(p1[key],false,`${key} must remain false on prediction`);
}
console.log('P23.14 blind reasoner benchmark tests passed');
