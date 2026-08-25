import test from 'node:test';
import assert from 'node:assert/strict';
import {buildProspectiveP21FrozenDecision} from '../daytrade/phase57-p21-prospective-frozen-base.js';

function historicalRows({count=80,horizonBars=1}={}){
  const start=Date.parse('2026-08-10T00:00:00.000Z');
  return Array.from({length:count},(_,i)=>({
    symbol:'7203.T',
    sessionDate:'2026-08-10',
    featureCutoff:new Date(start+i*10*60_000).toISOString(),
    outcomeAt:new Date(start+i*10*60_000+5*60_000).toISOString(),
    outcomeSessionDate:'2026-08-10',
    pointInTimeValid:true,
    horizonBars,
    label:1,
    actualReturnPct:0.2,
    features:{x:i/100},
  }));
}

function currentRow(symbol,cutoff='2026-08-11T00:00:00.000Z'){
  return {symbol,sessionDate:'2026-08-11',featureCutoff:cutoff,pointInTimeValid:true,horizonBars:1,features:{x:0.9}};
}

function countedOptions(counter){
  return {
    featureFamilies:{TEST:['x']},
    modelConfigs:[{id:'TEST',type:'LOGISTIC_REGRESSION',options:{}}],
    thresholds:[0.55],
    innerTrainFraction:0.6,
    innerTestFraction:0.15,
    innerMinTrainRows:20,
    minInnerSignals:5,
    minimumInnerNetReturnPct:0,
    roundTripCostPct:0.05,
    fitPredictor:()=>{
      counter.count+=1;
      return ()=>0.8;
    },
  };
}

test('prior-only cache reuses selection/refit across symbols at the exact same cutoff without changing the frozen result',()=>{
  const history={1:historicalRows()};

  const uncachedCounter={count:0};
  const uncachedOptions=countedOptions(uncachedCounter);
  const uncachedA=buildProspectiveP21FrozenDecision({historicalHorizonRowsByBars:history,currentRowsByHorizon:{1:[currentRow('7203.T')]},options:uncachedOptions});
  const uncachedB=buildProspectiveP21FrozenDecision({historicalHorizonRowsByBars:history,currentRowsByHorizon:{1:[currentRow('6758.T')]},options:uncachedOptions});
  assert.equal(uncachedA.complete,true);
  assert.equal(uncachedB.complete,true);
  const uncachedFitCount=uncachedCounter.count;
  assert.ok(uncachedFitCount>0);

  const cachedCounter={count:0};
  const cachedOptions=countedOptions(cachedCounter);
  const cache=new Map();
  const cachedA=buildProspectiveP21FrozenDecision({historicalHorizonRowsByBars:history,currentRowsByHorizon:{1:[currentRow('7203.T')]},options:cachedOptions,priorOnlyCache:cache});
  const fitCountAfterFirst=cachedCounter.count;
  const cachedB=buildProspectiveP21FrozenDecision({historicalHorizonRowsByBars:history,currentRowsByHorizon:{1:[currentRow('6758.T')]},options:cachedOptions,priorOnlyCache:cache});

  assert.equal(cachedA.priorOnlyCacheHit,false);
  assert.equal(cachedB.priorOnlyCacheHit,true);
  assert.equal(cache.size,1);
  assert.equal(cachedCounter.count,fitCountAfterFirst,'second symbol at same cutoff must not refit prior-only models');
  assert.ok(cachedCounter.count<uncachedFitCount,'cached path must perform fewer model fits than two uncached calls');

  for(const [cached,uncached] of [[cachedA,uncachedA],[cachedB,uncachedB]]){
    assert.equal(cached.status,uncached.status);
    assert.deepEqual(cached.decision,uncached.decision);
    assert.equal(cached.modelId,uncached.modelId);
    assert.equal(cached.artifactSha256,uncached.artifactSha256);
    assert.deepEqual(cached.selection,uncached.selection);
  }
});

test('prior-only cache is cutoff-exact and never reuses a model across later cutoffs',()=>{
  const history={1:historicalRows()};
  const counter={count:0};
  const options=countedOptions(counter);
  const cache=new Map();
  const first=buildProspectiveP21FrozenDecision({historicalHorizonRowsByBars:history,currentRowsByHorizon:{1:[currentRow('7203.T','2026-08-11T00:00:00.000Z')]},options,priorOnlyCache:cache});
  const afterFirst=counter.count;
  const later=buildProspectiveP21FrozenDecision({historicalHorizonRowsByBars:history,currentRowsByHorizon:{1:[currentRow('7203.T','2026-08-11T00:05:00.000Z')]},options,priorOnlyCache:cache});
  assert.equal(first.complete,true);
  assert.equal(later.complete,true);
  assert.equal(first.priorOnlyCacheHit,false);
  assert.equal(later.priorOnlyCacheHit,false);
  assert.equal(cache.size,2);
  assert.ok(counter.count>afterFirst,'later cutoff must run an independent prior-only selection/refit');
});
