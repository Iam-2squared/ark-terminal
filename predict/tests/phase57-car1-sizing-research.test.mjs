import assert from 'node:assert/strict';
import test from 'node:test';
import {
  buildCausalRiskSnapshot,
  normalizeSizingWeights,
  PHASE57_CAR1_POLICY,
  PHASE57_CAR1_PROFILES,
  PHASE57_CAR1_SAFETY,
} from '../portfolio/phase57-car1-sizing-research.js';

const t=i=>`2026-09-01T00:${String(i).padStart(2,'0')}:00.000Z`;
const bar=(i,close,range=2)=>({timestamp:t(i),open:close,high:close+range,low:close-range,close});
const history=(scale=1)=>Array.from({length:15},(_,i)=>bar(i,100+i*scale,2*scale));

test('CAR-1 remains research-only and cannot promote or transmit',()=>{
  for(const key of [
    'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
    'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','winnerSelectionAllowed',
  ])assert.equal(PHASE57_CAR1_SAFETY[key],false,key);
  assert.equal(PHASE57_CAR1_POLICY.entrySet,'FROZEN_UNCHANGED');
  assert.equal(PHASE57_CAR1_POLICY.exitSet,'FROZEN_UNCHANGED');
  assert.equal(PHASE57_CAR1_POLICY.parameterSearchAllowed,false);
  assert.deepEqual(PHASE57_CAR1_PROFILES.map(row=>row.id),['EQUAL_NOTIONAL','INVERSE_ATR','INVERSE_REALIZED_VOL']);
});

test('risk snapshot fails closed if a future bar is supplied',()=>{
  assert.throws(()=>buildCausalRiskSnapshot({bars:[...history(),bar(16,120)],entryTimestamp:t(14)}),/future bar supplied/);
});

test('future bars cannot silently change the causal snapshot because they are rejected',()=>{
  const left=buildCausalRiskSnapshot({bars:history(),entryTimestamp:t(14)});
  assert.equal(left.futureBarUsed,false);
  assert.equal(left.futureOutcomeUsed,false);
  assert.throws(()=>buildCausalRiskSnapshot({bars:[...history(),bar(15,500,100)],entryTimestamp:t(14)}),/future bar supplied/);
});

test('inverse ATR allocates less weight to the higher ATR candidate',()=>{
  const low=buildCausalRiskSnapshot({bars:history(0.5),entryTimestamp:t(14)});
  const high=buildCausalRiskSnapshot({bars:history(2),entryTimestamp:t(14)});
  const weights=normalizeSizingWeights({profileId:'INVERSE_ATR',candidates:[{key:'LOW',riskSnapshot:low},{key:'HIGH',riskSnapshot:high}]});
  assert.ok(weights.find(row=>row.key==='LOW').weight>weights.find(row=>row.key==='HIGH').weight);
  assert.ok(Math.abs(weights.reduce((sum,row)=>sum+row.weight,0)-1)<1e-12);
});

test('inverse realized volatility allocates less weight to the higher-vol candidate',()=>{
  const lowBars=Array.from({length:15},(_,i)=>bar(i,100+(i%2?0.2:-0.2),1));
  const highBars=Array.from({length:15},(_,i)=>bar(i,100+(i%2?5:-5),6));
  const low=buildCausalRiskSnapshot({bars:lowBars,entryTimestamp:t(14)});
  const high=buildCausalRiskSnapshot({bars:highBars,entryTimestamp:t(14)});
  const weights=normalizeSizingWeights({profileId:'INVERSE_REALIZED_VOL',candidates:[{key:'LOW',riskSnapshot:low},{key:'HIGH',riskSnapshot:high}]});
  assert.ok(weights.find(row=>row.key==='LOW').weight>weights.find(row=>row.key==='HIGH').weight);
});

test('equal notional is exactly equal and does not inspect risk estimates',()=>{
  const weights=normalizeSizingWeights({profileId:'EQUAL_NOTIONAL',candidates:[{key:'A'},{key:'B'},{key:'C'}]});
  assert.deepEqual(weights.map(row=>row.weight),[1/3,1/3,1/3]);
});

test('insufficient causal history fails closed instead of backfilling',()=>{
  assert.throws(()=>buildCausalRiskSnapshot({bars:history().slice(0,10),entryTimestamp:t(9)}),/insufficient causal history/);
});
