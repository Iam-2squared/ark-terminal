import assert from 'node:assert/strict';
import test from 'node:test';
import {
  extractP252HistoricalSessionsFromP24Snapshot,
  assertP252PinnedP24SnapshotIdentity,
  PHASE57_P25_2K_POLICY,
  PHASE57_P25_2K_SAFETY,
} from '../daytrade/phase57-p25-2k-pinned-history-bridge.js';

function yahooBody(symbol,startEpoch,count=30){
  const timestamp=Array.from({length:count},(_,i)=>startEpoch+i*300);
  const open=timestamp.map((_,i)=>100+i*.1);
  return JSON.stringify({chart:{error:null,result:[{meta:{symbol,exchangeTimezoneName:'Asia/Tokyo',dataGranularity:'5m'},timestamp,indicators:{quote:[{
    open,high:open.map(x=>x+.5),low:open.map(x=>x-.5),close:open.map(x=>x+.1),volume:open.map((_,i)=>1000+i),
  }]}}]}});
}
function syntheticSnapshot(){
  const sessionDate='2026-06-18';
  const startEpoch=Math.floor(Date.parse(`${sessionDate}T09:00:00+09:00`)/1000);
  const responses={};
  for(const symbol of PHASE57_P25_2K_POLICY.historicalUniverse){
    for(const host of [1,2]){
      const url=`https://query${host}.finance.yahoo.com/v8/finance/chart/${symbol}?period1=1&period2=2&interval=5m&includePrePost=false`;
      responses[url]={status:200,statusText:'OK',body:yahooBody(symbol,startEpoch),providerSourceUrl:url};
    }
  }
  return {
    phase:'57.p24.9-oos-byte-snapshot',
    dataEndIso:'2026-08-12T06:30:00.000Z',
    effectiveStartIso:'2026-06-17T06:30:00.000Z',
    canonicalWindowDays:56,
    symbols:[...PHASE57_P25_2K_POLICY.historicalUniverse],
    responses,
    methodology:{performanceObservedBeforeFreeze:false,canonicalWindowChosenBeforePerformance:true,freshHoldoutConsumed:false},
  };
}

test('bridge de-duplicates query1/query2 and emits one valid historical session per required symbol',()=>{
  const result=extractP252HistoricalSessionsFromP24Snapshot({snapshot:syntheticSnapshot()});
  assert.equal(result.status,'PINNED_P24_HISTORY_SESSIONS_READY');
  assert.equal(result.sessionCount,5);
  assert.deepEqual(Object.values(result.perSymbolSessionCount),[1,1,1,1,1]);
  for(const session of result.sessions){
    assert.equal(session.bars5m.length,30);
    assert.equal(session.sessionDate,'2026-06-18');
  }
  assert.equal(result.methodology.queryHostDuplicatesDeduplicated,true);
  assert.equal(result.methodology.dailyMarketSpeedRequired,false);
});

test('conflicting duplicate provider bytes fail closed instead of picking a host',()=>{
  const snapshot=syntheticSnapshot();
  const key=Object.keys(snapshot.responses).find(x=>x.includes('query2')&&x.includes('7203.T'));
  const parsed=JSON.parse(snapshot.responses[key].body);
  parsed.chart.result[0].indicators.quote[0].close[0]+=10;
  snapshot.responses[key].body=JSON.stringify(parsed);
  assert.throws(()=>extractP252HistoricalSessionsFromP24Snapshot({snapshot}),/conflicting duplicate pinned bar/);
});

test('canonical identity guard rejects any SHA mismatch before prospective use',()=>{
  assert.throws(()=>assertP252PinnedP24SnapshotIdentity({snapshot:syntheticSnapshot(),snapshotSha256:'0'.repeat(64)}),/SHA-256 mismatch/);
  assert.equal(PHASE57_P25_2K_POLICY.canonicalSnapshotSha256,'10ec0b89893823f9e2f7ba720db2d0fad8e76d642fe00f7b77d387ae6be6b12a');
  assert.equal(PHASE57_P25_2K_POLICY.canonicalSourceRunId,31785422471);
});

test('all execution surfaces and fresh holdout remain disabled',()=>{
  assert.equal(PHASE57_P25_2K_POLICY.dailyMarketSpeedRequired,false);
  assert.equal(PHASE57_P25_2K_POLICY.freshHoldoutConsumed,false);
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed'])assert.equal(PHASE57_P25_2K_SAFETY[key],false,key);
});
