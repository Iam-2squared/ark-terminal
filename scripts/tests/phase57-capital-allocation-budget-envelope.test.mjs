import test from 'node:test';
import assert from 'node:assert/strict';
import {simulatePhaseB} from '../lib/phase57-capital-allocation-v3-phase-b.mjs';

const opportunity=({eventId='x',symbol='1001.T',timestamp='2026-09-01T00:00:00.000Z',entryPrice=100})=>({
  eventId,symbol,sessionDate:'2026-09-01',decisionTimestamp:timestamp,direction:1,
  entryPrice,mshScore:.8,recentRealizedVolatility:.01,outcomeUsed:false,exitUsed:false,
});
const trade=({eventId='x',symbol='1001.T',exitPrice=101,exitTimestamp='2026-09-01T00:10:00.000Z'})=>({
  eventId,symbol,direction:1,causalEligible:true,
  v4:{exitTimestamp,exitPrice,exitReason:'V4_NATIVE',barsHeld:2,netReturnPct:.95},
});
const mark=(symbol,timestamp,close)=>({symbol,timestamp,sessionDate:'2026-09-01',close});

function run({budgetDivisor=10,fractionalShares=false,entryPrice=100,exitPrice=101,initialCapital=300000}={}){
  const entryTimestamp='2026-09-01T00:00:00.000Z',exitTimestamp='2026-09-01T00:10:00.000Z';
  return simulatePhaseB({
    opportunities:[opportunity({entryPrice,timestamp:entryTimestamp})],trades:[trade({exitPrice,exitTimestamp})],
    allocationId:'V3_B_RISK',exitId:'FROZEN_EXIT_V4',initialCapital,maxPositions:10,budgetDivisor,fractionalShares,
    marks:[mark('1001.T',entryTimestamp,entryPrice),mark('1001.T',exitTimestamp,exitPrice)],
  });
}

test('budget denominator is independent of the fixed ten-position limit',()=>{
  const max10=run({budgetDivisor:10}),max5=run({budgetDivisor:5});
  assert.equal(max10.budgetDivisor,10);assert.equal(max5.budgetDivisor,5);
  assert.equal(max10.closedTrades[0].quantity,300);assert.equal(max5.closedTrades[0].quantity,600);
  assert.equal(max10.capital.maximumConcurrentPositions,1);assert.equal(max5.capital.maximumConcurrentPositions,1);
});

test('fractional diagnostic accepts a target below one 100-share lot without changing cash accounting',()=>{
  const lot=run({budgetDivisor:10,entryPrice:1500,exitPrice:1515,initialCapital:200000});
  const fractional=run({budgetDivisor:10,fractionalShares:true,entryPrice:1500,exitPrice:1515,initialCapital:200000});
  assert.equal(lot.trade.accepted,0);assert.equal(lot.trade.rejectionCounts.TARGET_BUDGET_BELOW_100_SHARES,1);
  assert.equal(fractional.trade.accepted,1);assert.ok(Math.abs(fractional.closedTrades[0].quantity-40/3)<1e-8);
  assert.equal(fractional.fractionalShares,true);assert.equal(fractional.accounting.costDoubleCounted,false);
  assert.ok(Math.abs(fractional.finalEquityJpy-(200000+190))<1e-6);
});

test('explicit MAX_10 budget produces the same result as the legacy default argument',()=>{
  const explicit=run({budgetDivisor:10});
  const entryTimestamp='2026-09-01T00:00:00.000Z',exitTimestamp='2026-09-01T00:10:00.000Z';
  const legacy=simulatePhaseB({
    opportunities:[opportunity({timestamp:entryTimestamp})],trades:[trade({exitTimestamp})],
    allocationId:'V3_B_RISK',exitId:'FROZEN_EXIT_V4',initialCapital:300000,maxPositions:10,
    marks:[mark('1001.T',entryTimestamp,100),mark('1001.T',exitTimestamp,101)],
  });
  assert.equal(explicit.finalEquityJpy,legacy.finalEquityJpy);
  assert.deepEqual(explicit.closedTrades,legacy.closedTrades);
});
