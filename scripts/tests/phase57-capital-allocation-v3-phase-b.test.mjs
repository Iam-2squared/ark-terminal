import test from 'node:test';
import assert from 'node:assert/strict';
import {runBar5Adapter,simulatePhaseB,PHASE_B_POLICY} from '../lib/phase57-capital-allocation-v3-phase-b.mjs';

const decisions=values=>values.map((currentReturnPct,i)=>({timestamp:`2026-09-01T00:${String((i+1)*5).padStart(2,'0')}:00.000Z`,currentReturnPct,baseScore:{state:{elapsedBars:i+1}}}));
const trade=({direction='LONG',values=[-1,-.5,-.2,-.1,-.25,-.3],v4Bars=8}={})=>({eventId:'x',symbol:'1111.T',direction,entryPrice:100,causalEligible:true,firstBarDirectionalCloseReturnBps:values[0]*100,v4:{exitTimestamp:'2026-09-01T01:00:00.000Z',exitPrice:direction==='LONG'?102:98,exitReason:'V4_NATIVE',barsHeld:v4Bars,netReturnPct:1.95},management:{v4:decisions(values)}});
const closeAt=(symbol,t)=>({
  '2026-09-01T00:25:00.000Z':99.75,
}[t]);

test('bar5 adapter is directionally symmetric and charges exactly one round trip cost',()=>{
  const l=runBar5Adapter(trade({direction:'LONG'}),{barCloseAt:closeAt});
  const s=runBar5Adapter(trade({direction:'SHORT'}),{barCloseAt:(symbol,t)=>t.endsWith('25:00.000Z')?100.25:null});
  assert.equal(l.classification,'DEFENSIVE_EXIT_BAR_5');assert.equal(s.classification,'DEFENSIVE_EXIT_BAR_5');
  assert.ok(Math.abs(l.grossReturnPct+0.25)<1e-12);assert.ok(Math.abs(s.grossReturnPct+0.25)<1e-12);
  assert.ok(Math.abs(l.netReturnPct-(l.grossReturnPct-PHASE_B_POLICY.roundTripCostPct))<1e-12);
});

test('reclaim is directional completed close return >= 0, including exactly bar5',()=>{
  const x=runBar5Adapter(trade({values:[-1,-.5,-.2,-.1,0,-2]}),{barCloseAt:closeAt});
  assert.equal(x.classification,'RECOVERED_TO_V4');assert.equal(x.exitReason,'V4_NATIVE');
});

test('bar6 and later cannot rescue a negative bar5',()=>{
  const x=runBar5Adapter(trade({values:[-1,-.5,-.2,-.1,-.25,3]}),{barCloseAt:closeAt});
  assert.equal(x.classification,'DEFENSIVE_EXIT_BAR_5');assert.equal(x.barsHeld,5);assert.equal(x.exitTimestamp,'2026-09-01T00:25:00.000Z');
});

test('native v4 early EXIT and missing horizon fail closed to v4',()=>{
  const x=runBar5Adapter(trade({values:[-1,-.5,-.2],v4Bars:3}),{barCloseAt:closeAt});
  assert.equal(x.classification,'HORIZON_FALLBACK_V4');assert.equal(x.exitReason,'V4_NATIVE');
});

const opportunity=({eventId,symbol,timestamp,direction=1,entryPrice=100})=>({
  eventId,symbol,sessionDate:'2026-09-01',decisionTimestamp:timestamp,direction,
  entryPrice,mshScore:.8,recentRealizedVolatility:.01,outcomeUsed:false,exitUsed:false,
});
const frozenTrade=({eventId,symbol,direction=1,exitTimestamp,exitPrice})=>({
  eventId,symbol,direction,causalEligible:true,v4:{exitTimestamp,exitPrice,exitReason:'V4_NATIVE',barsHeld:2,netReturnPct:direction*(exitPrice/100-1)*100-PHASE_B_POLICY.roundTripCostPct},
});
const mark=(symbol,timestamp,close)=>({symbol,timestamp,sessionDate:'2026-09-01',close});

test('cash ledger charges one split round-trip cost and reconciles final cash',()=>{
  const entryTimestamp='2026-09-01T00:00:00.000Z',exitTimestamp='2026-09-01T00:10:00.000Z';
  const result=simulatePhaseB({
    opportunities:[opportunity({eventId:'long',symbol:'1001.T',timestamp:entryTimestamp})],
    trades:[frozenTrade({eventId:'long',symbol:'1001.T',exitTimestamp,exitPrice:101})],
    allocationId:'V3_0_EQUAL',exitId:'FROZEN_EXIT_V4',initialCapital:200000,maxPositions:2,
    marks:[mark('1001.T',entryTimestamp,100),mark('1001.T',exitTimestamp,101)],
  });
  assert.equal(result.trade.accepted,1);assert.equal(result.closedTrades[0].quantity,1000);
  assert.equal(result.trade.transactionCostsJpy,50);assert.equal(result.netPnlJpy,950);
  assert.equal(result.finalEquityJpy,200950);assert.equal(result.realizedPnlJpy,950);
});

test('SHORT is fully cash collateralized and sale proceeds never become buying power',()=>{
  const entryTimestamp='2026-09-01T00:00:00.000Z',exitTimestamp='2026-09-01T00:10:00.000Z';
  const result=simulatePhaseB({
    opportunities:[opportunity({eventId:'short',symbol:'1002.T',timestamp:entryTimestamp,direction:-1})],
    trades:[frozenTrade({eventId:'short',symbol:'1002.T',direction:-1,exitTimestamp,exitPrice:98})],
    allocationId:'V3_0_EQUAL',exitId:'FROZEN_EXIT_V4',initialCapital:200000,maxPositions:2,
    marks:[mark('1002.T',entryTimestamp,100),mark('1002.T',exitTimestamp,98)],
  });
  const afterEntry=result.curve.find(x=>x.timestamp===entryTimestamp);
  assert.equal(afterEntry.cashJpy,99975);assert.equal(afterEntry.shortExposureJpy,100000);
  assert.equal(result.finalEquityJpy,201950);assert.equal(result.accounting.shortSaleProceedsReusable,false);
});

test('same-timestamp EXIT releases cash before ENTRY under the shared ordering',()=>{
  const t0='2026-09-01T00:00:00.000Z',t1='2026-09-01T00:10:00.000Z',t2='2026-09-01T00:20:00.000Z';
  const result=simulatePhaseB({
    opportunities:[
      opportunity({eventId:'first',symbol:'1003.T',timestamp:t0}),
      opportunity({eventId:'second',symbol:'1004.T',timestamp:t1}),
    ],
    trades:[
      frozenTrade({eventId:'first',symbol:'1003.T',exitTimestamp:t1,exitPrice:101}),
      frozenTrade({eventId:'second',symbol:'1004.T',exitTimestamp:t2,exitPrice:102}),
    ],
    allocationId:'V3_0_EQUAL',exitId:'FROZEN_EXIT_V4',initialCapital:100000,maxPositions:1,
    marks:[mark('1003.T',t0,100),mark('1003.T',t1,101),mark('1004.T',t1,100),mark('1004.T',t2,102)],
  });
  assert.deepEqual(result.decisions.map(x=>[x.eventId,x.status]),[['first','ACCEPTED'],['second','ACCEPTED']]);
  assert.equal(result.trade.accepted,2);assert.equal(result.capital.maximumConcurrentPositions,1);
});
