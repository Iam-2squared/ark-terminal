import assert from 'node:assert/strict';
import test from 'node:test';
import {buildPhase57SelectorNativeTargets} from '../daytrade/phase57-selector-v3-targets.js';

const START=Date.parse('2026-09-04T01:00:00.000Z');
const iso=value=>new Date(value).toISOString();

function futureBar(index,{high=100.1,low=99.9}={}){
  return {
    availableAt:iso(START+(index+1)*5*60_000),
    sessionDate:'2026-09-04',
    high,low,
  };
}

test('selector-native excursions are Entry-independent and cost adjusted',()=>{
  const result=buildPhase57SelectorNativeTargets({
    featureCutoff:iso(START),
    anchorPrice:100,
    sessionDate:'2026-09-04',
    futureBars:Array.from({length:12},(_,index)=>futureBar(index,{
      high:100.1+(index+1)*0.1,
      low:99.9-(index+1)*0.05,
    })),
  });
  const primary=result.horizons[6];
  assert.equal(primary.status,'TARGET_READY');
  assert.equal(primary.upExcursion,0.007);
  assert.equal(primary.downExcursion,0.004);
  assert.equal(primary.twoSidedOpportunity,0.007);
  assert.equal(primary.costAdjustedTwoSidedUtility,0.006);
  assert.equal(result.methodology.entryIndependent,true);
});

test('same OHLC bar touching both barriers is explicitly ambiguous',()=>{
  const result=buildPhase57SelectorNativeTargets({
    featureCutoff:iso(START),
    anchorPrice:100,
    sessionDate:'2026-09-04',
    futureBars:Array.from({length:12},(_,index)=>futureBar(index,index===0?{high:100.7,low:99.3}:{})),
  });
  assert.equal(result.horizons[1].barriers['20'].status,'AMBIGUOUS_SAME_BAR');
  assert.equal(result.horizons[1].barriers['20'].upArm,'AMBIGUOUS_SAME_BAR');
  assert.equal(result.horizons[1].barriers['20'].downArm,'AMBIGUOUS_SAME_BAR');
  assert.equal(result.methodology.ambiguousSameBarOrderInferred,false);
});

test('missing future bars remain missing instead of being fabricated',()=>{
  const result=buildPhase57SelectorNativeTargets({
    featureCutoff:iso(START),
    anchorPrice:100,
    sessionDate:'2026-09-04',
    futureBars:[futureBar(0),futureBar(1)],
  });
  assert.equal(result.horizons[2].status,'TARGET_READY');
  assert.equal(result.horizons[3].status,'INSUFFICIENT_FUTURE_BARS');
  assert.equal(result.horizons[3].twoSidedOpportunity,null);
});

test('overnight bars never satisfy an intraday horizon',()=>{
  const result=buildPhase57SelectorNativeTargets({
    featureCutoff:iso(START),
    anchorPrice:100,
    sessionDate:'2026-09-04',
    futureBars:Array.from({length:12},(_,index)=>({...futureBar(index),sessionDate:'2026-09-05'})),
  });
  assert.equal(result.futureBarCount,0);
  assert.equal(result.horizons[1].status,'INSUFFICIENT_FUTURE_BARS');
});

test('conflicting duplicate future bars fail closed',()=>{
  const left=futureBar(0);
  assert.throws(()=>buildPhase57SelectorNativeTargets({
    featureCutoff:iso(START),anchorPrice:100,sessionDate:'2026-09-04',
    futureBars:[left,{...left,high:left.high+1}],
  }),/conflicting future bar/);
});

