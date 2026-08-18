import assert from 'node:assert/strict';
import test from 'node:test';
import {
  buildP252Yahoo5mUrls,
  parseP252Yahoo5mSessionPayload,
  fetchP252Yahoo5mSession,
  collectP252Routine5mSession,
  PHASE57_P25_2J_POLICY,
  PHASE57_P25_2J_SAFETY,
} from '../daytrade/phase57-p25-2j-routine-nonrss-5m-source.js';

const FIXED5=['7203.T','6758.T','9984.T','8306.T','8035.T'];
const OLD30=Array.from({length:30},(_,i)=>`${2001+i}.T`);
const D50=Array.from({length:50},(_,i)=>`${1001+i}.T`);
function universe(sessionDate='2026-08-19'){
  return {ready:true,sessionDate,variants:{FIXED_5:FIXED5,OLD_FIXED_30:OLD30,DYNAMIC_30:D50.slice(0,30),DYNAMIC_40:D50.slice(0,40),DYNAMIC_50:D50}};
}
function payload(sessionDate='2026-08-19',count=30){
  const first=Math.floor(Date.parse(`${sessionDate}T09:00:00+09:00`)/1000);
  const timestamp=Array.from({length:count},(_,i)=>first+i*300);
  const open=timestamp.map((_,i)=>100+i*.1);
  return {chart:{error:null,result:[{meta:{exchangeTimezoneName:'Asia/Tokyo',dataGranularity:'5m'},timestamp,indicators:{quote:[{
    open,
    high:open.map(x=>x+.5),
    low:open.map(x=>x-.5),
    close:open.map(x=>x+.1),
    volume:open.map((_,i)=>1000+i),
  }]}}]}};
}

test('Yahoo 5m parser produces canonical same-session OHLCV with interval-start provenance',()=>{
  const result=parseP252Yahoo5mSessionPayload({payload:payload(),symbol:'7203.T',sessionDate:'2026-08-19'});
  assert.equal(result.provider,'YAHOO_FINANCE_CHART_5M');
  assert.equal(result.interval,'5m');
  assert.equal(result.bars.length,30);
  assert.equal(result.bars[0].timestamp,'2026-08-19T00:00:00.000Z');
  assert.equal(result.sourceQuality.dataGranularity,'5m');
  assert.equal(result.methodology.yahooTimestampRepresentsFiveMinuteIntervalStart,true);
  assert.equal(result.methodology.brokerGroundTruth,false);
});

test('Yahoo request is pinned to the requested JST session and 5m regular data mode',()=>{
  const urls=buildP252Yahoo5mUrls({symbol:'7203.T',sessionDate:'2026-08-19'});
  assert.equal(urls.length,2);
  for(const url of urls){
    assert.match(url,/interval=5m/);
    assert.match(url,/includePrePost=false/);
    assert.match(url,/7203.T/);
  }
});

test('Yahoo fetcher fails over from query1 to query2 and fingerprints provider payload',async()=>{
  let calls=0;
  const fetchImpl=async url=>{
    calls+=1;
    if(calls===1)return {ok:false,status:503,json:async()=>({})};
    return {ok:true,status:200,json:async()=>payload()};
  };
  const result=await fetchP252Yahoo5mSession({symbol:'7203.T',sessionDate:'2026-08-19',fetchImpl});
  assert.equal(calls,2);
  assert.equal(result.requestHost,'query2.finance.yahoo.com');
  assert.match(result.sourcePayloadSha256,/^[a-f0-9]{64}$/);
});

test('routine collector requires every frozen target-union symbol but never requires MarketSpeed or board/tick',async()=>{
  const record=universe();
  const fetchSession=async({symbol,sessionDate})=>({
    symbol,sessionDate,provider:'TEST_5M',requestHost:'test',sourcePayloadSha256:'a'.repeat(64),bars:parseP252Yahoo5mSessionPayload({payload:payload(sessionDate),symbol,sessionDate}).bars,
  });
  const result=await collectP252Routine5mSession({universeRecord:record,fetchSession});
  const expectedUnion=new Set(Object.values(record.variants).flat()).size;
  assert.equal(result.ready,true);
  assert.equal(result.targetSymbolCount,expectedUnion);
  assert.equal(result.collectedSymbolCount,expectedUnion);
  assert.equal(result.failedSymbolCount,0);
  assert.equal(result.sourceProvenance.dailyMarketSpeedRequired,false);
  assert.equal(result.methodology.boardOrTickUsed,false);
  assert.equal(PHASE57_P25_2J_POLICY.microstructureUsed,false);
});

test('one failed symbol blocks the whole routine session instead of silently shrinking the universe',async()=>{
  const record=universe();
  const fetchSession=async({symbol,sessionDate})=>{
    if(symbol==='1001.T')throw new Error('test outage');
    return {symbol,sessionDate,provider:'TEST_5M',bars:parseP252Yahoo5mSessionPayload({payload:payload(sessionDate),symbol,sessionDate}).bars};
  };
  const result=await collectP252Routine5mSession({universeRecord:record,fetchSession});
  assert.equal(result.ready,false);
  assert.equal(result.status,'BLOCKED_ROUTINE_NONRSS_5M_SESSION');
  assert.equal(result.failedSymbolCount,1);
  assert.equal(result.failures[0].symbol,'1001.T');
});

test('all execution surfaces remain disabled',()=>{
  assert.equal(PHASE57_P25_2J_POLICY.dailyMarketSpeedRequired,false);
  assert.equal(PHASE57_P25_2J_POLICY.marketSpeedVerificationSeparate,true);
  assert.equal(PHASE57_P25_2J_POLICY.boardOrTickRequired,false);
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed'])assert.equal(PHASE57_P25_2J_SAFETY[key],false,key);
});
