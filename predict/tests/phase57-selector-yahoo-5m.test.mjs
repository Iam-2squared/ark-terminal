import assert from 'node:assert/strict';
import test from 'node:test';
import {fetchYahooChart5m,parseYahooChart5mPayload} from '../../scripts/lib/phase57-selector-yahoo-5m.mjs';

const seconds=value=>Math.floor(Date.parse(value)/1000);

function payload(){
  const times=[
    '2026-09-04T00:00:00.000Z',
    '2026-09-04T02:25:00.000Z',
    '2026-09-04T02:30:00.000Z',
    '2026-09-04T03:30:00.000Z',
    '2026-09-04T06:25:00.000Z',
    '2026-09-04T06:30:00.000Z',
  ];
  return {
    chart:{result:[{
      meta:{exchangeName:'JPX',exchangeTimezoneName:'Asia/Tokyo',currency:'JPY',instrumentType:'EQUITY',dataGranularity:'5m'},
      timestamp:times.map(seconds),
      indicators:{quote:[{
        open:times.map((_,index)=>100+index),
        high:times.map((_,index)=>101+index),
        low:times.map((_,index)=>99+index),
        close:times.map((_,index)=>100.5+index),
        volume:times.map((_,index)=>1000+index),
      }]},
    }],error:null},
  };
}

test('Yahoo parser keeps only JPX regular-session BAR_OPEN observations',()=>{
  const result=parseYahooChart5mPayload({symbol:'7203.T',sector:'輸送用機器',market:'プライム',payload:payload()});
  assert.equal(result.bars.length,4);
  assert.deepEqual(result.bars.map(bar=>bar.timestamp),[
    '2026-09-04T00:00:00.000Z','2026-09-04T02:25:00.000Z',
    '2026-09-04T03:30:00.000Z','2026-09-04T06:25:00.000Z',
  ]);
  assert.equal(result.bars.every(bar=>bar.sessionDate==='2026-09-04'),true);
});

test('Yahoo fetch retries retryable failure without changing provenance',async()=>{
  let calls=0;
  const fetchImpl=async()=>{
    calls+=1;
    if(calls===1)return {ok:false,status:429,text:async()=> 'rate limited'};
    return {ok:true,status:200,json:async()=>payload()};
  };
  const result=await fetchYahooChart5m({symbol:'7203.T',attempts:2,baseDelayMs:0,fetchImpl});
  assert.equal(calls,2);
  assert.equal(result.symbol,'7203.T');
  assert.equal(result.providerMeta.dataGranularity,'5m');
});

test('Yahoo parser fails closed when no valid bars exist',()=>{
  assert.throws(()=>parseYahooChart5mPayload({
    symbol:'7203.T',payload:{chart:{result:[{timestamp:[],indicators:{quote:[{}]}}]}},
  }),/no valid regular-session/);
});

