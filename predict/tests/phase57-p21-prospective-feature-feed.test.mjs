import test from 'node:test';
import assert from 'node:assert/strict';
import { buildProspectiveP21FeatureFeed } from '../daytrade/phase57-p21-prospective-feature-feed.js';
import { enrichHistoricalIntradayBars } from '../daytrade/phase57-intraday-multifactor.js';

function bars(){
  const start=Date.parse('2026-08-17T00:00:00.000Z'); // 09:00 JST
  return Array.from({length:8},(_,i)=>({
    timestamp:new Date(start+i*5*60_000).toISOString(),
    open:100+i*0.1,
    high:101+i*0.1,
    low:99+i*0.1,
    close:100.2+i*0.1,
    volume:1000+i*100,
  }));
}

const forbidden=['outcomeAt','outcome','outcomes','label','actualReturnPct','futureBars','realizedReturn','grossReturnPct','netReturnPct','mfePct','maePct','exitTimestamp','exitReason','hit','target'];

test('builds outcome-free current rows for all frozen P21 horizons from a completed same-session 5m prefix',()=>{
  const source=bars();
  const out=buildProspectiveP21FeatureFeed({symbol:'7203.T',sessionDate:'2026-08-17',bars5m:source,latestBarClosed:true});
  assert.equal(out.complete,true);
  assert.equal(out.status,'PROSPECTIVE_P21_FEATURE_FEED_READY');
  assert.deepEqual(out.horizonsBars,[1,3,6,12,24]);
  assert.equal(out.featureCutoff,source.at(-1).timestamp);
  for(const h of out.horizonsBars){
    const row=out.currentRowsByHorizon[h];
    assert.equal(row.horizonBars,h);
    assert.equal(row.featureCutoff,source.at(-1).timestamp);
    assert.equal(row.pointInTimeValid,true);
    assert.equal(row.sourceMode,'prospective_completed_5m_ohlcv_prefix');
    for(const key of forbidden) assert.equal(Object.prototype.hasOwnProperty.call(row,key),false,key);
  }
});

test('matches the P24 current-bar feature definitions and Phase57 multifactor enrichment',()=>{
  const source=bars();
  const out=buildProspectiveP21FeatureFeed({symbol:'7203.T',sessionDate:'2026-08-17',bars5m:source,latestBarClosed:true});
  const features=out.currentRowsByHorizon[1].features;
  const current=source.at(-1);
  const previous=source.at(-2);
  const previous5=source.slice(-6,-1).map(x=>x.volume);
  const avgPrevious5=previous5.reduce((a,b)=>a+b,0)/previous5.length;
  assert.ok(Math.abs(features.returnFromOpen-((current.close/source[0].open-1)*100))<1e-12);
  assert.ok(Math.abs(features.rangePosition-((current.close-current.low)/(current.high-current.low)))<1e-12);
  assert.ok(Math.abs(features.shortMomentum-((current.close/previous.close-1)*100))<1e-12);
  assert.ok(Math.abs(features.relativeVolume-(current.volume/avgPrevious5))<1e-12);
  const expectedMulti=enrichHistoricalIntradayBars(source).at(-1).multiFactor;
  for(const [key,value] of Object.entries(expectedMulti)) assert.ok(Math.abs(Number(features[key])-Number(value))<1e-12,key);
});

test('fails closed unless the latest 5m bar is explicitly marked completed',()=>{
  const out=buildProspectiveP21FeatureFeed({symbol:'7203.T',sessionDate:'2026-08-17',bars5m:bars()});
  assert.equal(out.complete,false);
  assert.ok(out.blockers.includes('LATEST_5M_BAR_NOT_EXPLICITLY_CLOSED'));
});

test('fails closed on mixed JST sessions',()=>{
  const source=bars();
  source[0]={...source[0],timestamp:'2026-08-16T00:00:00.000Z'};
  const out=buildProspectiveP21FeatureFeed({symbol:'7203.T',sessionDate:'2026-08-17',bars5m:source,latestBarClosed:true});
  assert.equal(out.complete,false);
  assert.ok(out.blockers.includes('CROSS_SESSION_5M_PREFIX'));
});

test('all write/trading/promotion flags remain false',()=>{
  const out=buildProspectiveP21FeatureFeed({symbol:'7203.T',sessionDate:'2026-08-17',bars5m:bars(),latestBarClosed:true});
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed']){
    assert.equal(out.safety[key],false,key);
  }
});
