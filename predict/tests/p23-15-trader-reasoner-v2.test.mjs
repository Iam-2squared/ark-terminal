import assert from 'node:assert/strict';
import { buildTraderReasoningDecision, PHASE57_P23_15_SAFETY } from '../daytrade/phase57-p23-15-trader-reasoner-v2.js';

const base={symbol:'TEST.T',sessionDate:'2026-08-01',featureCutoff:'2026-08-01T01:00:00.000Z',setup:'BREAKOUT_CONTINUATION_UP',direction:'UP',visualComponents:{structureCoherence:.82,directionalPressure:.72,wickControl:.75,participation:.66,extensionHealth:.71,spaceToObstacle:.80,volatilityTransition:.64,setupGeometryFit:.78},visualGeometry:{nearestObstacle:null},visualNarrative:{primary:'CLEAN_VISUAL_STRUCTURE',observations:['OPEN_SPACE_AHEAD']},outcome60m:{hit:false,directionalReturnPct:-99,mfePct:99,maePct:-99}};

const strong=buildTraderReasoningDecision(base);
assert.equal(strong.decision,'QUALIFIED');
assert.equal(strong.futureOutcomeVisible,false);
assert.equal(strong.outcomeUsedForDecision,false);
assert.equal(strong.thresholdSearchPerformed,false);
assert.ok(!('directionalReturnPct' in strong));

const crowded=buildTraderReasoningDecision({...base,visualComponents:{...base.visualComponents,spaceToObstacle:.15}});
assert.equal(crowded.decision,'WAIT');
assert.ok(crowded.vetoReasons.includes('INSUFFICIENT_ROOM_TO_OBSTACLE'));

const weakShort=buildTraderReasoningDecision({...base,setup:'BREAKOUT_CONTINUATION_DOWN',direction:'DOWN',visualComponents:{...base.visualComponents,structureCoherence:.60}});
assert.equal(weakShort.decision,'WAIT');
assert.ok(weakShort.vetoReasons.includes('HTF_NOT_ALIGNED_ENOUGH'));

for(const k of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed','transmitted']) assert.equal(PHASE57_P23_15_SAFETY[k],false,k);
console.log('p23.15 trader reasoner tests passed');
