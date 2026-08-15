import test from 'node:test';
import assert from 'node:assert/strict';
import {buildPhase58MicrostructureFrame,assertPhase58ReadOnly,PHASE58_P1_CONTRACT} from '../scalping/phase58-microstructure-foundation.js';

const quotes=[
  {timestamp:'2026-08-15T00:00:00.000Z',bestBid:100,bestAsk:100.1,bidSize:900,askSize:700,bidPrice1:100,bidSize1:900,askPrice1:100.1,askSize1:700},
  {timestamp:'2026-08-15T00:00:02.000Z',bestBid:100.1,bestAsk:100.2,bidSize:1000,askSize:650,bidPrice1:100.1,bidSize1:1000,askPrice1:100.2,askSize1:650},
];
const ticks=[
  {timestamp:'2026-08-15T00:00:01.000Z',price:100.1,volume:100},
  {timestamp:'2026-08-15T00:00:02.500Z',price:100.2,volume:200},
];

test('P58.1 builds a causal read-only microstructure frame',()=>{
  const frame=buildPhase58MicrostructureFrame({snapshot:quotes.at(-1),quoteSnapshots:quotes,ticks,asOf:'2026-08-15T00:00:03.000Z'});
  assert.equal(frame.status,'MICROSTRUCTURE_FRAME_READY');
  assert.equal(frame.dataQuality.futureQuoteAssignments,0);
  assert.ok(Number.isFinite(frame.features.spreadBps));
  assert.ok(Number.isFinite(frame.features.topBookImbalance));
  assert.equal(frame.contract.nativeAggressorSideAvailable,false);
  assertPhase58ReadOnly(frame);
});

test('P58.1 fails quality when quote is crossed',()=>{
  const frame=buildPhase58MicrostructureFrame({snapshot:{timestamp:'2026-08-15T00:00:02.000Z',bestBid:101,bestAsk:100,bidSize:10,askSize:10},quoteSnapshots:quotes,ticks:[],asOf:'2026-08-15T00:00:03.000Z'});
  assert.equal(frame.quality.checks.topOfBookValid,false);
  assert.equal(frame.status,'MICROSTRUCTURE_FRAME_DEGRADED');
});

test('P58.1 contract is limited to read-only RSS sources',()=>{
  assert.deepEqual(PHASE58_P1_CONTRACT.allowedFunctions,['RssMarket','RssTickList']);
  assert.equal(PHASE58_P1_CONTRACT.forbiddenOrderFunctions,true);
  assert.equal(PHASE58_P1_CONTRACT.maxRssTickRows,300);
});
