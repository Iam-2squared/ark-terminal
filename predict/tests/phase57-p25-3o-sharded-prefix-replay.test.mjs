import assert from 'node:assert/strict';
import test from 'node:test';
import {replayP252FrozenDaySession} from '../daytrade/phase57-p25-2f-postsession-point-in-time-replay.js';
import {
  replayP253PrefixShard,
  recombineP253PrefixShards,
  PHASE57_P25_3O_SAFETY,
} from '../daytrade/phase57-p25-3o-sharded-prefix-replay.js';

const FROZEN5=['7203.T','6758.T','9984.T','8306.T','8035.T'];
const OLD30=Array.from({length:30},(_,i)=>`${2001+i}.T`);
const D50=Array.from({length:50},(_,i)=>`${1001+i}.T`);
const D40=D50.slice(0,40),D30=D50.slice(0,30);
function universe(){
  return {
    ready:true,
    sessionDate:'2026-08-19',
    variants:{FIXED_5:FROZEN5,OLD_FIXED_30:OLD30,DYNAMIC_30:D30,DYNAMIC_40:D40,DYNAMIC_50:D50},
    rankAudit:{day50:D50.map((symbol,index)=>({symbol,sector:`S${index%7}`}))},
  };
}
function targets(){return [...new Set([...FROZEN5,...OLD30,...D50])].sort();}
function sixBars(){
  return Array.from({length:6},(_,i)=>({
    timestamp:`2026-08-19T00:${String(i*5).padStart(2,'0')}:00.000Z`,
    open:100+i,high:101+i,low:99+i,close:100.5+i,volume:1000+i*10,
  }));
}
function barsBySymbol(){return Object.fromEntries(targets().map(symbol=>[symbol,sixBars()]));}
function scorer({currentPrefix,symbol,featureCutoff}){
  assert.equal(currentPrefix.bars5m.at(-1).timestamp,featureCutoff);
  const signal=symbol==='1001.T'||symbol==='7203.T';
  return {
    complete:true,
    status:'PHASE57_PROSPECTIVE_SNAPSHOT_READY',
    policyId:'PHASE57_P24_COMBINED_PROSPECTIVE_V1',
    currentSymbol:symbol,
    snapshot:{asOf:featureCutoff,context:{sourceBarCloseAt:'2026-08-19T00:30:00.000Z'}},
    phase57:{
      status:signal?'PROSPECTIVE_PHASE57_FROZEN_SIGNAL_READY':'PROSPECTIVE_PHASE57_FROZEN_WAIT_READY',
      modelId:'phase57-p21-prospective-logit-h6',
      artifactSha256:'b'.repeat(64),
      decision:{
        direction:signal?1:0,
        confidence:signal?0.72:0.51,
        setup:signal?'TECHNICAL':null,
        asOf:featureCutoff,
        frozenByPhase57:true,
        pointInTimeOnly:true,
        futureOutcomeUsed:false,
        thresholdSearchAfterCapture:false,
        entryRetunedAfterCapture:false,
        context:{
          probability:signal?0.72:0.51,
          signalEligible:signal,
          selectedHorizonBars:signal?6:null,
          selectedFeatureFamily:signal?'TECHNICAL':null,
          selectedModelType:signal?'LOGISTIC_REGRESSION':null,
          selectedConfigId:signal?'LOGIT':null,
          selectedThreshold:signal?0.55:null,
        },
      },
    },
    provenance:{currentSymbol:symbol,currentFeatureCutoff:featureCutoff,currentSessionDate:'2026-08-19'},
  };
}

test('shard scorer invokes expensive scorer only for assigned symbols while preserving full fair cutoff grid',()=>{
  const selected=targets().slice(0,10);
  let calls=0;
  const shard=replayP253PrefixShard({
    universeRecord:universe(),
    sessionBarsBySymbol:barsBySymbol(),
    scoreSymbols:selected,
    scorePrefix:args=>{calls+=1;return scorer(args);},
  });
  assert.equal(shard.fullTargetSymbolCount,85);
  assert.equal(shard.shardSymbolCount,10);
  assert.equal(shard.commonFairCutoffCount,1);
  assert.equal(calls,10);
  assert.equal(shard.successfulDecisionCount,10);
  assert.equal(shard.methodology.fullTargetUnionUsedForFairCutoffGrid,true);
  assert.equal(shard.methodology.placeholderWaitMayEnterRecombinedEvidence,false);
});

test('disjoint shard checkpoints recombine to the same frozen ledger as monolithic replay',()=>{
  const all=targets();
  const monolithic=replayP252FrozenDaySession({
    universeRecord:universe(),
    sessionBarsBySymbol:barsBySymbol(),
    scorePrefix:scorer,
  });
  const shards=[all.slice(0,20),all.slice(20,40),all.slice(40,60),all.slice(60)].map(scoreSymbols=>replayP253PrefixShard({
    universeRecord:universe(),
    sessionBarsBySymbol:barsBySymbol(),
    scoreSymbols,
    scorePrefix:scorer,
  }));
  const recombined=recombineP253PrefixShards({universeRecord:universe(),shards});
  assert.deepEqual(recombined.commonFairCutoffs,monolithic.commonFairCutoffs);
  assert.deepEqual(recombined.ledger,monolithic.ledger);
  assert.equal(recombined.scorerCallCount,monolithic.scorerCallCount);
  assert.equal(recombined.blockedDecisionCount,0);
  assert.equal(recombined.methodology.recombinedBeforeOutcomeMaterialization,true);
});

test('recombine fails closed on overlapping or incomplete shard coverage',()=>{
  const all=targets();
  const left=replayP253PrefixShard({universeRecord:universe(),sessionBarsBySymbol:barsBySymbol(),scoreSymbols:all.slice(0,50),scorePrefix:scorer});
  const overlap=replayP253PrefixShard({universeRecord:universe(),sessionBarsBySymbol:barsBySymbol(),scoreSymbols:all.slice(49),scorePrefix:scorer});
  assert.throws(()=>recombineP253PrefixShards({universeRecord:universe(),shards:[left,overlap]}),/duplicate shard symbol/);
  assert.throws(()=>recombineP253PrefixShards({universeRecord:universe(),shards:[left]}),/coverage mismatch/);
});

test('all execution and promotion surfaces remain disabled in P25.3O',()=>{
  for(const key of [
    'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
    'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed',
    'transmitted','freshHoldoutConsumed',
  ])assert.equal(PHASE57_P25_3O_SAFETY[key],false,key);
});
