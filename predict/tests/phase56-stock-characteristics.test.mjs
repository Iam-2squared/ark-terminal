import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildStockCharacteristics,
  marketCapBucket,
  priceBucket,
  tradingValueBucket,
  liquidityBucket,
  PHASE56_STOCK_CHARACTERISTICS_SAFETY,
} from '../chart/phase56-stock-characteristics.js';

function bars(n=30){
  return Array.from({length:n},(_,i)=>({
    sessionDate:`2026-01-${String(i+1).padStart(2,'0')}`,
    close:100+i,
    volume:1_000_000+i*10_000,
  }));
}

test('classifies market cap, price and liquidity buckets',()=>{
  assert.equal(marketCapBucket(9_000_000_000),'UNDER_10B');
  assert.equal(marketCapBucket(60_000_000_000),'50B_300B');
  assert.equal(priceBucket(350),'100_500');
  assert.equal(tradingValueBucket(2_000_000_000),'1B_10B');
  assert.equal(liquidityBucket(2_000_000_000),'HIGH');
});

test('builds point-in-time stock characteristics from data available at asOf',()=>{
  const xs=bars();
  const out=buildStockCharacteristics({
    bars:xs,
    asOfIndex:19,
    metadata:{
      symbol:'7203.t',sector:'Automobiles',marketSection:'Prime',marketCap:40_000_000_000_000,
      indexMembership:['Nikkei225','TOPIX'],effectiveAt:'2026-01-15',
    },
  });
  assert.equal(out.status,'STOCK_CHARACTERISTICS_READY');
  assert.equal(out.pointInTime,true);
  assert.equal(out.symbol,'7203.T');
  assert.equal(out.marketSegment,'PRIME');
  assert.equal(out.marketCapBucket,'OVER_1T');
  assert.equal(out.priceBucket,'100_500');
  assert.deepEqual(out.indexMembership,['NIKKEI225','TOPIX']);
  assert.equal(out.asOfIndex,19);
  assert.ok(out.averageTradingValue20>0);
});

test('blocks metadata that becomes effective after the as-of session',()=>{
  const out=buildStockCharacteristics({
    bars:bars(),asOfIndex:9,
    metadata:{symbol:'7203.T',marketCap:1_000_000_000_000,effectiveAt:'2026-01-20'},
  });
  assert.equal(out.status,'METADATA_FUTURE_LEAK_BLOCKED');
  assert.equal(out.pointInTime,false);
  assert.equal(out.executionAllowed,false);
});

test('never enables broker, Excel, RSS, live trading or promotion writes',()=>{
  const out=buildStockCharacteristics({bars:bars(),metadata:{symbol:'7203.T'}});
  assert.equal(PHASE56_STOCK_CHARACTERISTICS_SAFETY.executionAllowed,false);
  assert.equal(PHASE56_STOCK_CHARACTERISTICS_SAFETY.brokerWriteAllowed,false);
  assert.equal(PHASE56_STOCK_CHARACTERISTICS_SAFETY.excelOrderWriteAllowed,false);
  assert.equal(PHASE56_STOCK_CHARACTERISTICS_SAFETY.rssOrderFunctionAllowed,false);
  assert.equal(PHASE56_STOCK_CHARACTERISTICS_SAFETY.liveTradingAllowed,false);
  assert.equal(PHASE56_STOCK_CHARACTERISTICS_SAFETY.automaticPromotionAllowed,false);
  assert.equal(PHASE56_STOCK_CHARACTERISTICS_SAFETY.productionUpdateAllowed,false);
  assert.equal(out.executionAllowed,false);
  assert.equal(out.brokerWriteAllowed,false);
  assert.equal(out.excelOrderWriteAllowed,false);
  assert.equal(out.rssOrderFunctionAllowed,false);
  assert.equal(out.liveTradingAllowed,false);
  assert.equal(out.automaticPromotionAllowed,false);
  assert.equal(out.productionUpdateAllowed,false);
  assert.equal(out.transmitted,false);
});
