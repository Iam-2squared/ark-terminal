import assert from 'node:assert/strict';
import test from 'node:test';
import {
  aggregateJquantsMinutesToFiveMinuteBars,
  fetchJquantsMinuteRows,
  normalizeJquantsMinuteRows,
  partitionJquantsMinuteRowsForFiveMinuteBars,
} from '../../scripts/lib/phase57-selector-jquants-minute.mjs';

const row=(Time,overrides={})=>({
  Date:'2025-01-06',Time,Code:'86970',O:100,H:101,L:99,C:100.5,Vo:1000,Va:100500,
  ...overrides,
});

test('J-Quants one-minute rows aggregate to causal sparse five-minute bars',()=>{
  const bars=aggregateJquantsMinutesToFiveMinuteBars([
    row('09:00',{O:100,H:101,L:99,C:100.5,Vo:10,Va:1000}),
    row('09:02',{O:100.5,H:103,L:100,C:102,Vo:20,Va:2040}),
    row('09:04',{O:102,H:102.5,L:101,C:101.5,Vo:30,Va:3045}),
    row('12:30',{O:104,H:105,L:103,C:104.5,Vo:40,Va:4180}),
  ],{sourceMinuteTimestampMeaning:'BAR_START_HALF_OPEN_INCLUDING_TERMINAL_AUCTION_MINUTES'});
  assert.equal(bars.length,2);
  assert.deepEqual(bars[0],{
    symbol:'8697.T',sourceCode:'86970',sessionDate:'2025-01-06',sessionSegment:'AM',
    timestamp:'2025-01-06T00:00:00.000Z',availableAt:'2025-01-06T00:05:00.000Z',
    open:100,high:103,low:99,close:101.5,volume:60,turnover:6085,
    observedMinuteCount:3,missingNoTradeMinuteCount:2,fabricatedMinuteCount:0,
  });
  assert.equal(bars[1].sessionSegment,'PM');
  assert.equal(bars[1].timestamp,'2025-01-06T03:30:00.000Z');
});

test('timestamp meaning must be verified before aggregation',()=>{
  assert.throws(()=>aggregateJquantsMinutesToFiveMinuteBars([row('09:00')]),/Tick-proven frozen contract/);
});

test('terminal auctions are classified but never mixed into regular five-minute decision bars',()=>{
  const raw=[
    row('11:29',{O:100,H:101,L:99,C:100,Vo:10,Va:1000}),
    row('11:30',{O:110,H:110,L:110,C:110,Vo:50,Va:5500}),
    row('15:30',{O:120,H:120,L:120,C:120,Vo:60,Va:7200}),
  ];
  const partition=partitionJquantsMinuteRowsForFiveMinuteBars(raw);
  assert.equal(partition.regularRows.length,1);assert.equal(partition.terminalAuctionRows.length,2);
  assert.ok(partition.terminalAuctionRows.every(item=>item.sourceMinuteKind==='TERMINAL_AUCTION_MINUTE'));
  const bars=aggregateJquantsMinutesToFiveMinuteBars(raw,{sourceMinuteTimestampMeaning:'BAR_START_HALF_OPEN_INCLUDING_TERMINAL_AUCTION_MINUTES'});
  assert.equal(bars.length,1);assert.equal(bars[0].close,100);assert.equal(bars[0].volume,10);
  assert.equal(bars[0].timestamp,'2025-01-06T02:25:00.000Z');
  assert.equal(bars[0].availableAt,'2025-01-06T02:30:00.000Z');
});

test('conflicting duplicates and out-of-session rows fail closed',()=>{
  assert.throws(()=>normalizeJquantsMinuteRows([row('09:00'),row('09:00',{C:101})]),/conflicting/);
  assert.throws(()=>normalizeJquantsMinuteRows([row('11:45')]),/outside the supported TSE source session/);
});

test('fetcher paginates without exposing or persisting credentials',async()=>{
  const requests=[];
  const pages=[
    {data:[row('09:00')],pagination_key:'NEXT'},
    {data:[row('09:01')],pagination_key:null},
  ];
  const result=await fetchJquantsMinuteRows({
    apiKey:'test-secret',date:'2025-01-06',
    fetchImpl:async(url,options)=>{
      requests.push({url:String(url),headers:options.headers});
      return {ok:true,json:async()=>pages.shift()};
    },
  });
  assert.equal(result.rows.length,2);
  assert.equal(requests.length,2);
  assert.match(requests[1].url,/pagination_key=NEXT/);
  assert.equal(requests[0].headers['x-api-key'],'test-secret');
  assert.doesNotMatch(requests[0].url,/test-secret/);
  assert.equal(result.methodology.providerEntitlementVerifiedByOperator,false);
  assert.equal(result.safety.transmitted,false);
});

test('fetcher requires credentials and a bounded query',async()=>{
  await assert.rejects(()=>fetchJquantsMinuteRows({date:'2025-01-06'}),/JQUANTS_API_KEY/);
  await assert.rejects(()=>fetchJquantsMinuteRows({apiKey:'x'}),/requires code or date/);
  await assert.rejects(()=>fetchJquantsMinuteRows({apiKey:'x',date:'2025-01-06',from:'2025-01-01'}),/from\/to minute request requires code/);
});
