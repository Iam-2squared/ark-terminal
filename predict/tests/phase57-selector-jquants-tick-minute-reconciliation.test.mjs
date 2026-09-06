import assert from 'node:assert/strict';
import test from 'node:test';
import {gzipSync} from 'node:zlib';
import {
  parseTickTime,reconcileTickMinute,runTickMinuteReconciliation,
  RECONCILIATION_DATES,RECONCILIATION_CODES,
} from '../../scripts/reconcile_phase57_selector_jquants_tick_minute.mjs';

const safetyKeys=['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted'];
const tick=(Date,Code,Time,Price,TradingVolume,TransactionId,SessionDistinction)=>(
  {Date,Code,Time,SessionDistinction,Price:String(Price),TradingVolume:String(TradingVolume),TransactionId});
const minute=(Date,Code,Time,price,volume)=>(
  {Date,Code,Time,O:price,H:price,L:price,C:price,Vo:volume,Va:price*volume});

function queryFixture(date='2025-01-14',code='72030'){
  const rows=[
    ['09:00','09:00:00.100000',100,2,'01'],
    ['11:30','11:30:00.100000',101,3,'01'],
    ['12:30','12:30:00.100000',102,4,'02'],
    ['15:30','15:30:00.100000',103,5,'02'],
  ];
  return {
    ticks:rows.map(([label,time,price,volume,session],index)=>tick(date,code,time,price,volume,String(index+1),session)),
    minutes:rows.map(([label,time,price,volume])=>minute(date,code,label,price,volume)),
  };
}

test('tick timestamps preserve microseconds for competing interval assignments',()=>{
  assert.deepEqual(parseTickTime('09:00:00.000000'),{hour:9,minute:0,second:0,micro:0,totalMinute:540,microsWithinMinute:0});
  assert.throws(()=>parseTickTime('09:00:00'),/INVALID_TICK_TIME/);
});

test('all boundaries and all minute rows uniquely establish start-labelled half-open bins',()=>{
  const fixture=queryFixture();
  const result=reconcileTickMinute({ticks:fixture.ticks,minuteRows:fixture.minutes,queries:[{date:'2025-01-14',code:'72030'}]});
  assert.equal(result.contractConfirmed,true);
  assert.equal(result.contract,'BAR_START_HALF_OPEN_INCLUDING_TERMINAL_AUCTION_MINUTES');
  assert.equal(result.comparisons.START_HALF_OPEN.exactMatchCount,4);
  assert.equal(result.comparisons.START_HALF_OPEN.orphanTickBinCount,0);
  assert.ok(result.boundaries.every(row=>row.minuteRowPresent&&row.matches.START_HALF_OPEN));
  assert.ok(result.boundaries.every(row=>!row.matches.END_HALF_OPEN));
});

test('volume or turnover mismatch fails closed',()=>{
  const fixture=queryFixture();fixture.minutes[1]={...fixture.minutes[1],Va:999};
  const result=reconcileTickMinute({ticks:fixture.ticks,minuteRows:fixture.minutes,queries:[{date:'2025-01-14',code:'72030'}]});
  assert.equal(result.contractConfirmed,false);
  assert.equal(result.contract,'TIMESTAMP_CONTRACT_STILL_UNRESOLVED');
});

test('live transport downloads one bounded gzip, never reports prices, secret or signed URL',async()=>{
  const ticks=[],minutes=new Map();
  for(const date of RECONCILIATION_DATES){for(const code of RECONCILIATION_CODES){
    const fixture=queryFixture(date,code);ticks.push(...fixture.ticks);minutes.set(`${date}|${code}`,fixture.minutes);
  }}
  const header='Date,Code,Time,SessionDistinction,Price,TradingVolume,TransactionId';
  const csv=[header,...ticks.map(row=>[row.Date,row.Code,row.Time,row.SessionDistinction,row.Price,row.TradingVolume,row.TransactionId].join(','))].join('\n')+'\n';
  const compressed=gzipSync(csv),secret='secret-must-not-escape',signed='https://download.invalid/file.csv.gz?token=private';
  let signedDownloads=0;
  const report=await runTickMinuteReconciliation({apiKey:secret,pace:async()=>{},fetchImpl:async(url,options)=>{
    const parsed=new URL(url);
    if(parsed.hostname==='download.invalid'){signedDownloads+=1;assert.equal(options.headers['x-api-key'],undefined);return new Response(compressed,{status:200});}
    assert.equal(options.headers['x-api-key'],secret);assert.equal(String(url).includes(secret),false);
    if(parsed.pathname==='/v2/bulk/list')return new Response(JSON.stringify({data:[{Key:'equities/trades/test.csv.gz',Size:compressed.length,LastModified:'2025-01-16T00:00:00Z'}]}),{status:200});
    if(parsed.pathname==='/v2/bulk/get')return new Response(JSON.stringify({url:signed}),{status:200});
    if(parsed.pathname==='/v2/equities/bars/minute')return new Response(JSON.stringify({data:minutes.get(`${parsed.searchParams.get('date')}|${parsed.searchParams.get('code')}`)}),{status:200});
    throw new Error('unexpected fixture URL');
  }});
  assert.equal(signedDownloads,1);assert.equal(report.status,'TIMESTAMP_CONTRACT_CONFIRMED');
  assert.equal(report.reconciliation.contractConfirmed,true);assert.equal(report.sourceValidationPass,false);
  assert.equal(report.adapterChanged,false);assert.equal(report.fiveMinuteAggregationPerformed,false);
  const encoded=JSON.stringify(report);assert.equal(encoded.includes(secret),false);assert.equal(encoded.includes(signed),false);
  assert.equal(encoded.includes('"Price"'),false);assert.ok(safetyKeys.every(key=>report.safety[key]===false));
  assert.equal(report.untouchedOosReleased,false);
});

test('oversize tick file stops before signed URL acquisition',async()=>{
  let calls=0;
  const report=await runTickMinuteReconciliation({apiKey:'s',pace:async()=>{},fetchImpl:async(url)=>{
    calls+=1;const parsed=new URL(url);assert.equal(parsed.pathname,'/v2/bulk/list');
    return new Response(JSON.stringify({data:[{Key:'large.gz',Size:2_000_000_001,LastModified:'2025-01-16T00:00:00Z'}]}),{status:200});
  }});
  assert.equal(calls,2);assert.equal(report.status,'TICK_BULK_DOWNLOAD_BUDGET_EXCEEDED');
  assert.equal(report.downloadCount,0);assert.equal(report.reconciliation,null);
});

test('missing key and entitlement errors stay sanitized and sealed',async()=>{
  const missing=await runTickMinuteReconciliation({fetchImpl:async()=>{throw new Error('not called');}});
  assert.equal(missing.status,'AUTH_REQUIRED');assert.equal(missing.apiRequestCount,0);
  const denied=await runTickMinuteReconciliation({apiKey:'x',fetchImpl:async()=>new Response('private error',{status:403})});
  assert.equal(denied.status,'BLOCKED_ENTITLEMENT');assert.equal(JSON.stringify(denied).includes('private error'),false);
  assert.equal(denied.developmentReleased,false);assert.equal(denied.validationReleased,false);assert.equal(denied.untouchedOosReleased,false);
});
