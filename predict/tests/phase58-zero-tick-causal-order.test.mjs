import test from 'node:test';
import assert from 'node:assert/strict';
import {buildZeroTickFlow,classifyTicksWithZeroContinuation} from '../scalping/phase58-zero-tick-classifier.js';

const descTicks=[
  {time:'09:00:03.000',price:102,volume:10},
  {time:'09:00:02.000',price:101,volume:10},
  {time:'09:00:01.000',price:100,volume:10},
];

test('normalizes MARKETSPEED II newest-to-oldest tick rows before causal zero-tick classification',()=>{
  const out=buildZeroTickFlow(descTicks,{inputOrder:'DESC'});
  assert.equal(out.integrity.tickInputOrder,'DESC');
  assert.equal(out.integrity.causalProcessingOrder,'OLDEST_TO_NEWEST');
  assert.equal(out.integrity.causalOrderNormalized,true);
  assert.equal(out.integrity.futureLeakageDetected,false);
  assert.deepEqual(out.classified.map(x=>x.price),[100,101,102]);
  assert.deepEqual(out.classified.map(x=>x.side),[0,1,1]);
});

test('keeps already oldest-to-newest input in causal order',()=>{
  const asc=[...descTicks].reverse();
  const rows=classifyTicksWithZeroContinuation(asc,{inputOrder:'ASC'});
  assert.deepEqual(rows.map(x=>x.price),[100,101,102]);
  assert.deepEqual(rows.map(x=>x.side),[0,1,1]);
});

test('equal-price ticks inherit only a previously observed non-zero direction after order normalization',()=>{
  const desc=[
    {time:'09:00:04.000',price:101,volume:10},
    {time:'09:00:03.000',price:101,volume:10},
    {time:'09:00:02.000',price:101,volume:10},
    {time:'09:00:01.000',price:100,volume:10},
  ];
  const out=buildZeroTickFlow(desc,{inputOrder:'DESC'});
  assert.deepEqual(out.classified.map(x=>x.side),[0,1,1,1]);
  assert.equal(out.features.continuationCount,2);
});

test('rejects unknown tick input order rather than silently inventing chronology',()=>{
  assert.throws(()=>buildZeroTickFlow(descTicks,{inputOrder:'UNKNOWN'}),/inputOrder must be ASC or DESC/);
});

test('all trading and write flags remain false',()=>{
  const out=buildZeroTickFlow(descTicks,{inputOrder:'DESC'});
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed']){
    assert.equal(out.safety[key],false,key);
  }
});
