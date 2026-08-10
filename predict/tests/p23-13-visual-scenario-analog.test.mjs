import assert from 'node:assert/strict';
import {
  P23_13_VISUAL_ANALOG_FEATURE_KEYS,
  P23_13_VISUAL_ANALOG_POLICY,
  PHASE57_P23_13_SAFETY,
  visualRecordFeatures,
  visualRecordToAnalogCandidate,
  findVisualScenarioAnalogs,
} from '../daytrade/phase57-visual-scenario-analog.js';

for (const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed','transmitted']) {
  assert.equal(PHASE57_P23_13_SAFETY[key], false, `${key} must remain false`);
}
assert.equal(P23_13_VISUAL_ANALOG_POLICY.outcomeTuned, false);
assert.equal(P23_13_VISUAL_ANALOG_POLICY.predictionUsedAsEntryGate, false);
assert.equal(P23_13_VISUAL_ANALOG_POLICY.sameSetupOnly, true);
assert.equal(P23_13_VISUAL_ANALOG_POLICY.sameSessionAnalogsAllowed, false);
assert.ok(P23_13_VISUAL_ANALOG_FEATURE_KEYS.every(key => !/(future|outcome|label|target|actualreturn|netreturn|grossreturn|mfe|mae|profit|pnl|direction)/i.test(key)));

function record({
  symbol='TEST.T',
  sessionDate='2026-07-01',
  featureCutoff='2026-07-01T00:30:00.000Z',
  outcomeAt='2026-07-01T01:30:00.000Z',
  setup='BREAKOUT_CONTINUATION_UP',
  direction='UP',
  returnPct=0.2,
  shift=0,
}={}) {
  return {
    symbol,sessionDate,featureCutoff,setup,direction,
    visualComponents:{
      structureCoherence:0.7+shift,
      directionalPressure:0.6+shift,
      wickControl:0.65,
      participation:0.55,
      extensionHealth:0.75,
      spaceToObstacle:0.8,
      volatilityTransition:0.7,
      setupGeometryFit:0.9,
    },
    visualGeometry:{
      slope5mPctPerBar:0.03+shift*0.01,
      slope15mPctPerBar:0.02,
      slope60mPctPerBar:0.01,
      slope1dPctPerBar:0.005,
      openSpaceAhead:true,
    },
    outcome60m:{
      directionalReturnPct:returnPct,
      hit:returnPct>0,
      mfePct:Math.max(0,returnPct+0.3),
      maePct:Math.min(0,returnPct-0.4),
      outcomeAt,
    },
  };
}

const base=record();
const features=visualRecordFeatures(base);
assert.equal(features.openSpaceFlag,1);
assert.ok(features.alignedSlope5m>0);
const candidate=visualRecordToAnalogCandidate(base);
assert.equal(candidate.horizonBars,12);
assert.equal(candidate.actualReturnPct,0.2);
assert.equal(candidate.context.regime,'BREAKOUT_CONTINUATION_UP');

const history=[];
for(let i=0;i<28;i+=1){
  const day=String(1+i).padStart(2,'0');
  history.push(record({
    symbol:`S${i}.T`,sessionDate:`2026-07-${day}`,
    featureCutoff:`2026-07-${day}T00:30:00.000Z`,
    outcomeAt:`2026-07-${day}T01:30:00.000Z`,
    returnPct:i%3===0?-0.15:0.25,
    shift:(i%5)*0.01,
  }));
}
history.push(record({
  symbol:'WRONG.T',sessionDate:'2026-07-20',featureCutoff:'2026-07-20T00:30:00.000Z',outcomeAt:'2026-07-20T01:30:00.000Z',
  setup:'FAILED_BREAKOUT_REVERSAL_DOWN',direction:'DOWN',returnPct:9,shift:0,
}));
const query=record({
  symbol:'QUERY.T',sessionDate:'2026-08-10',featureCutoff:'2026-08-10T00:30:00.000Z',outcomeAt:'2026-08-10T01:30:00.000Z',returnPct:0.1,
});
history.push(query);

const result=findVisualScenarioAnalogs({record:query,historyRecords:history});
assert.equal(result.status,'INTRADAY_ANALOGS_READY');
assert.ok(result.analogCount>=20);
assert.equal(result.candidateAudit.currentSessionExcluded,true);
assert.equal(result.candidateAudit.candidateOutcomesFullyRealizedBeforeQuery,true);
assert.ok(result.selectedAnalogs.every(row=>row.context.regime==='BREAKOUT_CONTINUATION_UP'));
assert.equal(result.distanceUsesOutcomeLabels,false);
assert.equal(result.outcomeDerivedFeaturesAllowed,false);
assert.equal(result.futureOutcomeUsedForSimilarity,false);
assert.equal(result.predictionUsedAsEntryGate,false);
assert.equal(result.recommendationAllowed,false);
assert.equal(result.edgeClaimAllowed,false);
assert.equal(result.transmitted,false);
assert.ok(Number.isFinite(result.expectedAlignedReturnPct));
assert.ok(Number.isFinite(result.expectedSetupSuccessProbability));

const changedOutcomes=history.map(row=>row===query?row:{...row,outcome60m:row.outcome60m?{...row.outcome60m,directionalReturnPct:-row.outcome60m.directionalReturnPct}:row.outcome60m});
const changed=findVisualScenarioAnalogs({record:query,historyRecords:changedOutcomes});
assert.deepEqual(result.selectedAnalogs.map(row=>row.id),changed.selectedAnalogs.map(row=>row.id),'future labels must not affect similarity ranking');

console.log('P23.13 visual scenario analog tests passed');
