import assert from 'node:assert/strict';
import test from 'node:test';
import {buildP253PCheckpointPlan,validateP253PCheckpointCoverage,PHASE57_P25_3P_SAFETY} from '../daytrade/phase57-p25-3p-checkpoint-plan.js';

const FROZEN5=['7203.T','6758.T','9984.T','8306.T','8035.T'];
const OLD30=Array.from({length:30},(_,i)=>`${2001+i}.T`);
const D50=Array.from({length:50},(_,i)=>`${1001+i}.T`);
const D40=D50.slice(0,40),D30=D50.slice(0,30);
const universe={ready:true,sessionDate:'2026-08-19',variants:{FIXED_5:FROZEN5,OLD_FIXED_30:OLD30,DYNAMIC_30:D30,DYNAMIC_40:D40,DYNAMIC_50:D50}};

test('checkpoint plan partitions the frozen full union deterministically without overlap',()=>{
  const plan=buildP253PCheckpointPlan({universeRecord:universe,batchSize:5});
  const expected=[...new Set([...FROZEN5,...OLD30,...D50])].sort();
  assert.equal(plan.targetSymbolCount,expected.length);
  assert.equal(plan.batchCount,Math.ceil(expected.length/5));
  assert.deepEqual(plan.targetSymbols,expected);
  assert.deepEqual(plan.batches.flatMap(x=>x.shardSymbols),expected);
  assert.equal(new Set(plan.batches.flatMap(x=>x.shardSymbols)).size,expected.length);
  assert.equal(plan.methodology.currentOuterOosUsedForPartitioning,false);
});

test('checkpoint coverage requires every precommitted batch exactly once',()=>{
  const plan=buildP253PCheckpointPlan({universeRecord:universe,batchSize:7});
  const checkpoints=plan.batches.map(batch=>({phase:'57.p25.3p.checkpoint',status:'P25_3P_CHECKPOINT_COMPLETE',batchId:batch.batchId,shardSymbols:[...batch.shardSymbols]}));
  assert.deepEqual(validateP253PCheckpointCoverage({plan,checkpoints}),{complete:true,batchCount:plan.batchCount,targetSymbolCount:plan.targetSymbolCount});
  assert.throws(()=>validateP253PCheckpointCoverage({plan,checkpoints:checkpoints.slice(1)}),/missing checkpoints/);
  assert.throws(()=>validateP253PCheckpointCoverage({plan,checkpoints:[...checkpoints,checkpoints[0]]}),/duplicate checkpoint/);
});

test('safety remains fail-closed',()=>{
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed'])assert.equal(PHASE57_P25_3P_SAFETY[key],false,key);
});
