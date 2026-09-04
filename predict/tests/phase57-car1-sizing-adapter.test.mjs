import assert from 'node:assert/strict';
import test from 'node:test';
import {
  buildCausalSizingGroup,
  targetBudgetsFromGroup,
} from '../portfolio/phase57-car1-sizing-adapter.js';

const DATE='2026-09-01';
const at=minute=>`${DATE}T00:${String(minute).padStart(2,'0')}:00.000Z`;

function bars({base=100,range=2,step=0.2,count=20}={}){
  return Array.from({length:count},(_,index)=>{
    const close=base+index*step;
    return {timestamp:at(index),open:close,high:close+range/2,low:close-range/2,close};
  });
}

function entry(symbol,minute=15){
  return {sessionDate:DATE,symbol,entryTimestamp:at(minute)};
}

test('Equal Notional preserves the legacy per-slot budget for simultaneous candidates',()=>{
  const group=buildCausalSizingGroup({
    profileId:'EQUAL_NOTIONAL',
    entries:[entry('1002.T'),entry('1001.T')],
    barsBySymbol:{},
  });
  assert.deepEqual(group.candidates.map(row=>row.symbol),['1001.T','1002.T']);
  const budgets=targetBudgetsFromGroup({group,equityBeforeEntry:1_000_000,maxPositions:4});
  assert.equal(budgets.length,2);
  assert.equal(budgets[0].targetBudgetJpy,250_000);
  assert.equal(budgets[1].targetBudgetJpy,250_000);
  assert.equal(budgets.reduce((sum,row)=>sum+row.targetBudgetJpy,0),500_000);
  assert.equal(group.audit.rankingChanged,false);
  assert.equal(group.audit.entryChanged,false);
  assert.equal(group.audit.exitChanged,false);
  assert.equal(group.audit.winnerSelectionAllowed,false);
});

test('Inverse ATR reallocates only within the same simultaneous slot-budget total',()=>{
  const group=buildCausalSizingGroup({
    profileId:'INVERSE_ATR',
    entries:[entry('LOW.T'),entry('HIGH.T')],
    barsBySymbol:{
      'LOW.T':bars({range:1,step:0.1,count:20}),
      'HIGH.T':bars({range:6,step:0.1,count:20}),
    },
  });
  const budgets=targetBudgetsFromGroup({group,equityBeforeEntry:1_000_000,maxPositions:4});
  const low=budgets.find(row=>row.key.endsWith('|LOW.T'));
  const high=budgets.find(row=>row.key.endsWith('|HIGH.T'));
  assert.ok(low.targetBudgetJpy>high.targetBudgetJpy);
  assert.ok(Math.abs(budgets.reduce((sum,row)=>sum+row.targetBudgetJpy,0)-500_000)<1e-8);
  assert.equal(group.audit.futureBarUsed,false);
  assert.equal(group.audit.futureOutcomeUsed,false);
});

test('future bars in the full session source are excluded before risk calculation',()=>{
  const allBars=bars({range:2,count:20});
  allBars.push({timestamp:at(19).replace('00:19','00:59'),open:999,high:1000,low:998,close:999});
  const group=buildCausalSizingGroup({
    profileId:'INVERSE_REALIZED_VOL',
    entries:[entry('1001.T')],
    barsBySymbol:{'1001.T':allBars},
  });
  assert.equal(group.candidates[0].riskSnapshot.asOfTimestamp,at(15));
  assert.equal(group.candidates[0].riskSnapshot.futureBarUsed,false);
  assert.equal(group.candidates[0].riskSnapshot.futureOutcomeUsed,false);
});

test('mixed Entry timestamps are rejected rather than silently changing priority semantics',()=>{
  assert.throws(()=>buildCausalSizingGroup({
    profileId:'EQUAL_NOTIONAL',
    entries:[entry('1001.T',15),entry('1002.T',16)],
    barsBySymbol:{},
  }),/one simultaneous Entry timestamp/);
});
