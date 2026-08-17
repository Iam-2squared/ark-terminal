import test from 'node:test';
import assert from 'node:assert/strict';
import {buildProspectiveP21HistoricalRows} from '../daytrade/phase57-p21-prospective-history.js';
import {buildPhase57ProspectiveSnapshotPipeline,PHASE58_P13_FROZEN_POLICY,PHASE58_TARGET_MODES,PHASE58_P13_SAFETY} from '../scalping/phase58-phase57-prospective-pipeline.js';

function sessionBars(date,{count=32,start=100}={}){
  const startMs=Date.parse(`${date}T00:00:00.000Z`); // 09:00 JST
  return Array.from({length:count},(_,i)=>{
    const base=start+i*0.1;
    return {
      timestamp:new Date(startMs+i*5*60_000).toISOString(),
      open:base,
      high:base+0.4,
      low:base-0.3,
      close:base+0.2,
      volume:1000+i*20,
    };
  });
}

function historicalSessions(){
  return ['2026-08-10','2026-08-11','2026-08-12','2026-08-13'].map((sessionDate,index)=>({
    symbol:'7203.T',sessionDate,bars5m:sessionBars(sessionDate,{start:100+index}),
  }));
}

function currentPrefix(){
  return {
    status:'PHASE58_RSSCHART_5M_PREFIX_READY',
    symbol:'7203.T',sessionDate:'2026-08-17',latestBarClosed:true,
    bars5m:sessionBars('2026-08-17',{count:8,start:110}),
  };
}

const TEST_POLICY={
  policyId:'TEST_ONLY_MINI_POLICY',
  horizonsBars:[1],
  selectionOptions:{
    featureFamilies:{TEST:['returnFromOpen']},
    modelConfigs:[{id:'TEST',type:'LOGISTIC_REGRESSION',options:{}}],
    thresholds:[0.55],
    innerTrainFraction:0.6,
    innerTestFraction:0.2,
    innerMinTrainRows:10,
    minInnerSignals:3,
    minimumInnerNetReturnPct:-999,
    roundTripCostPct:0.05,
    fitPredictor:()=>()=>0.8,
  },
};

test('materializes P21 historical horizon rows with P24-parity features and realized historical outcomes',()=>{
  const out=buildProspectiveP21HistoricalRows({sessions:historicalSessions(),horizons:[1,3,6]});
  assert.equal(out.complete,true);
  assert.equal(out.status,'PROSPECTIVE_P21_HISTORICAL_ROWS_READY');
  assert.equal(out.sessionCount,4);
  for(const horizon of [1,3,6]){
    assert.ok(out.rowCounts[horizon]>0);
    const row=out.historicalHorizonRowsByBars[horizon][0];
    assert.equal(row.horizonBars,horizon);
    assert.equal(row.pointInTimeValid,true);
    assert.ok(Number.isFinite(Number(row.label)));
    assert.ok(Number.isFinite(Number(row.actualReturnPct)));
    assert.ok(Date.parse(row.featureCutoff)<Date.parse(row.outcomeAt));
    assert.ok(Number.isFinite(Number(row.features.returnFromOpen)));
    assert.ok(Number.isFinite(Number(row.features.vwapDistancePct)));
  }
});

test('rejects historical sessions containing bars from a different JST session date',()=>{
  const sessions=historicalSessions();
  sessions[0]={...sessions[0],bars5m:[...sessions[0].bars5m,{...sessions[0].bars5m[0],timestamp:'2026-08-11T00:00:00.000Z'}]};
  const out=buildProspectiveP21HistoricalRows({sessions,horizons:[1]});
  assert.equal(out.complete,false);
  assert.equal(out.status,'BLOCKED_INVALID_OR_CROSS_SESSION_HISTORY');
});

test('composes historical rows plus an outcome-free completed 5m prefix into a frozen Phase57 snapshot',()=>{
  const out=buildPhase57ProspectiveSnapshotPipeline({historicalSessions:historicalSessions(),currentPrefix:currentPrefix(),policy:TEST_POLICY});
  assert.equal(out.complete,true);
  assert.equal(out.status,'PHASE57_PROSPECTIVE_SNAPSHOT_READY');
  assert.equal(out.policyFrozen,false);
  assert.equal(out.promotionEvidence,false);
  assert.equal(out.snapshot.direction,1);
  assert.equal(out.snapshot.frozen,true);
  assert.equal(out.snapshot.futureOutcomeUsed,false);
  assert.equal(out.snapshot.thresholdSearchAfterCapture,false);
  assert.equal(out.snapshot.entryRetunedAfterCapture,false);
  assert.match(out.snapshot.artifactSha256,/^[a-f0-9]{64}$/);
  assert.equal(out.methodology.phase58MayReverseDirection,false);
  for(const key of ['label','actualReturnPct','outcomeAt','futureBars','mfePct','maePct']){
    assert.equal(Object.prototype.hasOwnProperty.call(out.snapshot,key),false,key);
  }
});

test('reusable research target mode can score a different target without changing the training history',()=>{
  const prefix={...currentPrefix(),symbol:'285A.T'};
  const out=buildPhase57ProspectiveSnapshotPipeline({
    historicalSessions:historicalSessions(),
    currentPrefix:prefix,
    policy:TEST_POLICY,
    targetMode:PHASE58_TARGET_MODES.REUSABLE_RESEARCH_TARGET,
  });
  assert.equal(out.complete,true);
  assert.equal(out.targetMode,PHASE58_TARGET_MODES.REUSABLE_RESEARCH_TARGET);
  assert.equal(out.provenance.currentSymbol,'285A.T');
  assert.equal(out.methodology.reusableTargetChangesTrainingUniverse,false);
  assert.equal(out.promotionEvidence,false);
  assert.equal(out.targetGeneralizationClaimAllowed,false);
});

test('invalid target mode fails closed',()=>{
  const out=buildPhase57ProspectiveSnapshotPipeline({historicalSessions:historicalSessions(),currentPrefix:currentPrefix(),policy:TEST_POLICY,targetMode:'ANYTHING'});
  assert.equal(out.complete,false);
  assert.equal(out.status,'BLOCKED_INVALID_TARGET_MODE');
});

test('policy id alone cannot spoof the frozen production-research policy',()=>{
  const spoofed={
    policyId:PHASE58_P13_FROZEN_POLICY.policyId,
    horizonsBars:[1],
    selectionOptions:TEST_POLICY.selectionOptions,
  };
  const out=buildPhase57ProspectiveSnapshotPipeline({historicalSessions:historicalSessions(),currentPrefix:currentPrefix(),policy:spoofed});
  assert.equal(out.complete,true);
  assert.equal(out.policyFrozen,false);
});

test('frozen P24 prospective policy fails closed if the historical combined universe is incomplete',()=>{
  const out=buildPhase57ProspectiveSnapshotPipeline({
    historicalSessions:historicalSessions(),
    currentPrefix:currentPrefix(),
    policy:PHASE58_P13_FROZEN_POLICY,
  });
  assert.equal(out.complete,false);
  assert.equal(out.status,'BLOCKED_FROZEN_HISTORICAL_UNIVERSE_MISMATCH');
  assert.deepEqual([...out.expectedHistoricalUniverse],['7203.T','6758.T','9984.T','8306.T','8035.T']);
});

test('fails closed when the current prefix is not explicitly completed-bar safe',()=>{
  const prefix={...currentPrefix(),latestBarClosed:false};
  const out=buildPhase57ProspectiveSnapshotPipeline({historicalSessions:historicalSessions(),currentPrefix:prefix,policy:TEST_POLICY});
  assert.equal(out.complete,false);
  assert.equal(out.status,'BLOCKED_CURRENT_PREFIX_NOT_COMPLETED_BAR_SAFE');
});

test('all write, trading, promotion, and holdout flags remain false',()=>{
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed','transmitted','freshHoldoutConsumed']){
    assert.equal(PHASE58_P13_SAFETY[key],false,key);
  }
});
