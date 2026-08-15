import test from 'node:test';
import assert from 'node:assert/strict';
import {buildPhase58P2P3,buildOrderBookIntelligence} from '../scalping/phase58-orderbook-tickflow.js';

const q=(t,bid,ask,bs,as)=>({timestamp:t,bestBid:bid,bestAsk:ask,bidSize:bs,askSize:as,bidPrice1:bid,askPrice1:ask,bidSize1:bs,askSize1:as,bidPrice2:bid-1,askPrice2:ask+1,bidSize2:bs*.7,askSize2:as*.7,underSize:bs,overSize:as});
const ticks=(base,p0)=>[
  {timestamp:new Date(Date.parse(base)+500).toISOString(),price:p0,volume:100},
  {timestamp:new Date(Date.parse(base)+1000).toISOString(),price:p0+1,volume:120},
  {timestamp:new Date(Date.parse(base)+1500).toISOString(),price:p0+1,volume:80},
];
const input=(t,bid,ask,bs,as)=>({snapshot:q(t,bid,ask,bs,as),quoteSnapshots:[q(new Date(Date.parse(t)-1000).toISOString(),bid,ask,bs,as),q(t,bid,ask,bs,as)],ticks:ticks(new Date(Date.parse(t)-1000).toISOString(),ask),asOf:new Date(Date.parse(t)+1000).toISOString()});

test('P58.2/3 builds causal research intelligence and keeps all writes disabled',()=>{
  const r=buildPhase58P2P3([
    input('2026-08-15T00:00:01.000Z',100,101,1000,900),
    input('2026-08-15T00:00:03.000Z',100,102,1400,700),
    input('2026-08-15T00:00:05.000Z',101,103,1600,600),
  ]);
  assert.equal(r.orderBook.status,'ORDER_BOOK_INTELLIGENCE_READY');
  assert.equal(r.tickFlow.status,'TICK_FLOW_INTELLIGENCE_READY');
  assert.equal(r.safety.executionAllowed,false);
  assert.equal(r.safety.rssOrderFunctionAllowed,false);
  assert.ok(r.orderBook.sampleCount>=2);
  assert.ok(Number.isFinite(r.orderBook.features.pressureConsensus));
});

test('P58.2 refuses to claim readiness from one frame',()=>{
  const r=buildPhase58P2P3([input('2026-08-15T00:00:01.000Z',100,101,1000,900)]);
  assert.equal(r.orderBook.status,'INSUFFICIENT_HISTORY');
});

test('P58.2 filters degraded frames rather than using invalid book history',()=>{
  const r=buildPhase58P2P3([
    input('2026-08-15T00:00:01.000Z',100,101,1000,900),
    input('2026-08-15T00:00:03.000Z',101,100,1000,900),
  ]);
  assert.equal(r.frames[1].status,'MICROSTRUCTURE_FRAME_DEGRADED');
  assert.equal(r.orderBook.status,'INSUFFICIENT_HISTORY');
});
