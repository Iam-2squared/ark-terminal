import test from 'node:test';
import assert from 'node:assert/strict';
import { buildIntradayReadonlyFeatures } from '../daytrade/phase57-intraday-readonly.js';

const bars=[
  {timestamp:'2026-08-09T00:00:00Z',open:100,high:102,low:99,close:101,volume:1000},
  {timestamp:'2026-08-09T00:05:00Z',open:101,high:103,low:100,close:102,volume:1200},
  {timestamp:'2026-08-09T00:10:00Z',open:102,high:104,low:101,close:103,volume:1600},
  {timestamp:'2026-08-09T00:15:00Z',open:103,high:105,low:102,close:104,volume:2200},
];

const snapshot={bestBid:103.9,bestAsk:104.1,bidSize:5000,askSize:3000,bidDepth:16000,askDepth:11000};
const ticks=[
  {price:103.8,size:100,direction:'BUY'},
  {price:103.9,size:200,direction:'BUY'},
  {price:104.0,size:100,direction:'SELL'},
];

test('P57.1 builds intraday VWAP, range, momentum and microstructure features',()=>{
  const r=buildIntradayReadonlyFeatures({bars,snapshot,ticks});
  assert.equal(r.status,'INTRADAY_FEATURES_READY');
  assert.equal(r.features.lastPrice,104);
  assert.ok(r.features.vwap>100);
  assert.ok(r.features.vwapDistance>0);
  assert.ok(r.features.retFromOpen>0);
  assert.ok(r.features.bookImbalance>0);
  assert.equal(r.interactions.vwapFlowAlignment,'ABOVE_VWAP_BUY_FLOW');
  assert.equal(r.source.rssOrderFunctionsUsed,false);
});

test('P57.1 handles partial intraday data without inventing signals',()=>{
  const r=buildIntradayReadonlyFeatures({bars:[bars[0]]});
  assert.equal(r.status,'PARTIAL_INTRADAY_FEATURES');
  assert.equal(r.features.momentum3,null);
  assert.equal(r.interactions.vwapFlowAlignment,'UNKNOWN');
});

test('P57.1 cannot write, trade, promote or update production',()=>{
  const r=buildIntradayReadonlyFeatures({bars,snapshot,ticks});
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed']) assert.equal(r[key],false,key);
  assert.equal(r.paperTradingAllowed,false);
  assert.equal(r.transmitted,false);
  assert.equal(r.humanApprovalRequired,true);
  assert.equal(r.safety.executionAllowed,false);
});
