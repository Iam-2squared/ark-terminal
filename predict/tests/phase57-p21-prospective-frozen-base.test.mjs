import test from 'node:test';
import assert from 'node:assert/strict';
import {buildProspectiveP21FrozenDecision} from '../daytrade/phase57-p21-prospective-frozen-base.js';
import {buildProspectivePhase57Phase58Record} from '../scalping/phase58-phase57-runtime-adapter.js';

function historicalRows({count=80,horizonBars=1,probabilityDirection=1}={}){
  const start=Date.parse('2026-08-10T00:00:00.000Z');
  return Array.from({length:count},(_,i)=>{
    const featureCutoff=new Date(start+i*10*60_000).toISOString();
    const outcomeAt=new Date(start+i*10*60_000+5*60_000).toISOString();
    const up=probabilityDirection===1;
    return {
      symbol:'7203.T',sessionDate:'2026-08-10',featureCutoff,outcomeAt,outcomeSessionDate:'2026-08-10',
      pointInTimeValid:true,horizonBars,label:up?1:0,actualReturnPct:up?0.2:-0.2,features:{x:i/100,y:1},
    };
  });
}

const options={
  featureFamilies:{TEST:['x']},
  modelConfigs:[{id:'TEST',type:'LOGISTIC_REGRESSION',options:{}}],
  thresholds:[0.55],
  innerTrainFraction:0.6,
  innerTestFraction:0.15,
  innerMinTrainRows:20,
  minInnerSignals:5,
  minimumInnerNetReturnPct:0,
  roundTripCostPct:0.05,
  fitPredictor:()=>()=>0.8,
};

function currentRow(cutoff='2026-08-11T00:00:00.000Z'){
  return {symbol:'7203.T',sessionDate:'2026-08-11',featureCutoff:cutoff,pointInTimeValid:true,horizonBars:1,features:{x:0.9,y:1}};
}

test('builds a prospective frozen Phase57 decision using only fully realized prior rows',()=>{
  const out=buildProspectiveP21FrozenDecision({historicalHorizonRowsByBars:{1:historicalRows()},currentRowsByHorizon:{1:[currentRow()]},options});
  assert.equal(out.complete,true);
  assert.equal(out.status,'PROSPECTIVE_PHASE57_FROZEN_SIGNAL_READY');
  assert.equal(out.decision.direction,1);
  assert.equal(out.decision.frozenByPhase57,true);
  assert.equal(out.decision.pointInTimeOnly,true);
  assert.equal(out.decision.futureOutcomeUsed,false);
  assert.equal(out.decision.context.selectedHorizonBars,1);
  assert.match(out.artifactSha256,/^[a-f0-9]{64}$/);
  assert.ok(Date.parse(out.decision.context.maxPriorOutcomeAt)<=Date.parse(out.decision.asOf));
});

test('rejects current rows containing labels or realized outcomes',()=>{
  const unsafe={...currentRow(),label:1,actualReturnPct:1.2,outcomeAt:'2026-08-11T00:05:00.000Z'};
  const out=buildProspectiveP21FrozenDecision({historicalHorizonRowsByBars:{1:historicalRows()},currentRowsByHorizon:{1:[unsafe]},options});
  assert.equal(out.complete,false);
  assert.equal(out.status,'BLOCKED_CURRENT_ROW_INTEGRITY');
  assert.ok(out.blockers.some(x=>x.startsWith('CURRENT_ROW_CONTAINS_OUTCOME_FIELDS:')));
});

test('excludes prior rows whose outcomes are not realized by the current cutoff',()=>{
  const rows=historicalRows();
  rows.push({
    symbol:'7203.T',sessionDate:'2026-08-11',featureCutoff:'2026-08-10T23:59:00.000Z',outcomeAt:'2026-08-11T00:10:00.000Z',
    outcomeSessionDate:'2026-08-11',pointInTimeValid:true,horizonBars:1,label:1,actualReturnPct:99,features:{x:999},
  });
  const out=buildProspectiveP21FrozenDecision({historicalHorizonRowsByBars:{1:rows},currentRowsByHorizon:{1:[currentRow()]},options});
  assert.equal(out.complete,true);
  assert.ok(Date.parse(out.decision.context.maxPriorOutcomeAt)<=Date.parse(out.decision.asOf));
  assert.equal(out.decision.context.priorTrainingRows,80);
});

test('encodes a confident downside score as SHORT=-1 rather than historical label encoding 0',()=>{
  const shortOptions={...options,fitPredictor:()=>()=>0.2};
  const out=buildProspectiveP21FrozenDecision({historicalHorizonRowsByBars:{1:historicalRows({probabilityDirection:0})},currentRowsByHorizon:{1:[currentRow()]},options:shortOptions});
  assert.equal(out.complete,true);
  assert.equal(out.decision.direction,-1);
});

test('feeds the produced frozen decision through the Phase58 prospective synchronization adapter without direction reconstruction',()=>{
  const base=buildProspectiveP21FrozenDecision({historicalHorizonRowsByBars:{1:historicalRows()},currentRowsByHorizon:{1:[currentRow()]},options});
  assert.equal(base.complete,true);
  const synced=buildProspectivePhase57Phase58Record({
    decision:base.decision,
    modelId:base.modelId,
    artifactSha256:base.artifactSha256,
    capturedAt:'2026-08-11T00:02:00.000Z',
    microstructure:{orderBook:{ready:true},tickFlow:{ready:true}},
  });
  assert.equal(synced.complete,true);
  assert.equal(synced.synchronized.phase57.direction,1);
  assert.equal(synced.synchronized.methodology.phase58MayReverseDirection,false);
});

test('all safety write/trading/promotion flags remain false',()=>{
  const out=buildProspectiveP21FrozenDecision({historicalHorizonRowsByBars:{1:historicalRows()},currentRowsByHorizon:{1:[currentRow()]},options});
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed']){
    assert.equal(out.safety[key],false,key);
  }
});