import test from 'node:test';
import assert from 'node:assert/strict';
import { buildHistoricalIntradayRows, PHASE57_HISTORICAL_BASELINE_SAFETY } from './phase57-historical-intraday-baseline.js';

const bars = Array.from({length:40},(_,i)=>{
  const base=100+i*0.08;
  return { timestamp:new Date(Date.UTC(2026,0,5,0,i,0)).toISOString(), open:base, high:base+0.35, low:base-0.10, close:base+0.15, volume:1000+i*10 };
});

test('historical intraday rows keep future data out of features and use future only for labels',()=>{
  const rows=buildHistoricalIntradayRows({symbol:'7203.T',sessionDate:'2026-01-05',bars,horizonBars:5,barrierBps:20});
  assert.ok(rows.length>0);
  for(const row of rows){
    assert.equal(row.sourceMode,'historical_intraday_ohlcv');
    assert.ok(row.featureCutoff < row.outcomeAt);
    assert.equal(row.pointInTimeValid,true);
    assert.equal(row.features.bookImbalance,0);
    assert.equal(row.features.aggressiveBuyRatio,0.5);
  }
});

test('historical baseline safety remains READ ONLY',()=>{
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed']) assert.equal(PHASE57_HISTORICAL_BASELINE_SAFETY[key],false);
});
