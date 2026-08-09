import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizeIntradayFrame} from '../daytrade/phase57-intraday-capture-replay.js';
import {buildIntradayDataset,replayDataset,serializeDatasetJsonl} from '../daytrade/phase57-intraday-local-dataset.js';

const frame=(symbol,ts,price)=>normalizeIntradayFrame({symbol,capturedAt:ts,bar:{timestamp:ts,open:price,high:price+1,low:price-1,close:price,volume:1000},market:{price,bid:price-.5,ask:price+.5},ticks:[]});

test('P3 partitions frames deterministically by session and symbol',()=>{
  const a=frame('7203.T','2026-08-07T00:01:00Z',100);
  const b=frame('7203.T','2026-08-07T00:02:00Z',101);
  const c=frame('8306.T','2026-08-07T00:01:30Z',200);
  const ds=buildIntradayDataset([b,c,a]);
  assert.equal(ds.status,'INTRADAY_DATASET_READY');
  assert.equal(ds.rowCount,3);
  assert.equal(ds.partitionCount,2);
  assert.equal(ds.partitions[0].rows[0].capturedAt,'2026-08-07T00:01:00.000Z');
  assert.equal(ds.partitioning,'sessionDate/symbol');
});

test('P3 replay filters symbol/session and preserves chronological order',()=>{
  const ds=buildIntradayDataset([frame('7203.T','2026-08-07T00:02:00Z',101),frame('7203.T','2026-08-07T00:01:00Z',100),frame('8306.T','2026-08-07T00:01:30Z',200)]);
  const rows=replayDataset(ds,{symbol:'7203.T',sessionDate:'2026-08-07'});
  assert.equal(rows.length,2);
  assert.ok(rows[0].capturedAt<rows[1].capturedAt);
});

test('P3 JSONL serialization is stable and contains partition keys',()=>{
  const ds=buildIntradayDataset([frame('7203.T','2026-08-07T00:01:00Z',100)]);
  const text=serializeDatasetJsonl(ds);
  const parsed=JSON.parse(text);
  assert.equal(parsed.partition,'2026-08-07/7203.T');
  assert.equal(parsed.symbol,'7203.T');
});

test('P3 cannot trade or write broker/order channels',()=>{
  const ds=buildIntradayDataset([]);
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed']) assert.equal(ds[key],false,key);
  assert.equal(ds.paperTradingAllowed,false);
  assert.equal(ds.safety.humanApprovalRequired,true);
});
