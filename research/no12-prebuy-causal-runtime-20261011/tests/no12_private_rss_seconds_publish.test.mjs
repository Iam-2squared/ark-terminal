import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {inspectNo12SecondsSnapshot as inspect,publishNo12PrivateSeconds as publish}
 from '../tools/no12_private_rss_seconds_publish.mjs';
const at=t=>'2026-10-13T'+t+'+09:00';
const sample=(pc,source,price=1000)=>({
 sampledAt:at(pc),marketDate:'2026/10/13',marketClock:source,
 lastPrice:price,bestBid:price-1,bestAsk:price+1
});
const snapshot=()=>({
 schemaId:'ARK_NO12_MSII_RSS_MARKET_SECONDS_OBSERVATION_V1',
 sourceFunction:'RssMarket',evidenceMode:'OBSERVED_READ_ONLY',
 symbol:'7203.T',capturedAt:at('09:30:10'),
 orderPermissionEnabled:false,privateAccountDataIncluded:false,
 samples:[sample('09:30:02','09:30:01'),sample('09:30:04','09:30:03'),
  sample('09:30:06','09:30:05')]
});
const now=new Date(at('09:30:11'));
test('seconds source timestamp advances are observed at PC sample times, not certified broker arrival',()=>{
 const r=inspect({snapshot:snapshot(),now});
 assert.equal(r.sampleCount,3);
 assert.equal(r.sourceTimeAdvanceCount,2);
 assert.equal(r.maxSourceAgeMs,1000);
 assert.equal(r.status,'PC_OBSERVED_EXCHANGE_SECONDS_ADVANCE_NOT_BROKER_CERTIFIED');
 assert.equal(r.actualBrokerArrivalCertified,false);
 assert.equal(r.productionReady,false);
 assert.equal(r.orderTransmission,false);
});
test('no trade-time change is not misreported as a fresh advancing feed',()=>{
 const s=snapshot();
 s.samples[1].marketClock='09:30:01';s.samples[2].marketClock='09:30:01';
 const r=inspect({snapshot:s,now});
 assert.equal(r.sourceTimeAdvanceCount,0);
 assert.equal(r.status,'PC_OBSERVED_SAMPLES_WITHOUT_EXCHANGE_TIME_ADVANCE');
});
test('future exchange time, clock regression and future PC capture fail closed',()=>{
 const a=snapshot();a.samples[0].marketClock='09:30:10';
 assert.throws(()=>inspect({snapshot:a,now}),/NO12_SECONDS_FUTURE_EXCHANGE_TICK/);
 const b=snapshot();b.samples[1].marketClock='09:30:00';
 assert.throws(()=>inspect({snapshot:b,now}),/NO12_SECONDS_SOURCE_CLOCK_REGRESSION/);
 const c=snapshot();c.capturedAt=at('09:32:00');
 assert.throws(()=>inspect({snapshot:c,now}),/NO12_SECONDS_SOURCE_STALE_OR_FUTURE/);
});
test('quote invalidity and crossed bid/ask are not accepted as market truth',()=>{
 const a=snapshot();a.samples[0].lastPrice=NaN;
 assert.throws(()=>inspect({snapshot:a,now}),/NO12_SECONDS_PRICE_INVALID/);
 const b=snapshot();b.samples[1].bestBid=1010;
 assert.throws(()=>inspect({snapshot:b,now}),/NO12_SECONDS_CROSSED_BID_ASK_UNVERIFIED/);
});
test('source is persisted to local private receipt only; extra account fields are discarded',()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'no12-seconds-private-'));
 try{
  const file=path.join(root,'seconds-candidate-'+'d'.repeat(32)+'.json');
  const s=snapshot();s.accountSecret='NOT_FOR_RECEIPT';
  fs.writeFileSync(file,JSON.stringify(s));
  const r=publish({privateRoot:root,candidatePath:file,now});
  assert.equal(r.sampleCount,3);
  const saved=fs.readFileSync(path.join(root,'market-seconds-readonly-observed.json'),'utf8');
  assert(!saved.includes('accountSecret'));
  assert(!saved.includes('NOT_FOR_RECEIPT'));
  assert.equal(JSON.parse(saved).actualBrokerArrivalCertified,false);
  assert(fs.existsSync(path.join(root,'market-seconds-readonly-receipt.json')));
 }finally{fs.rmSync(root,{recursive:true,force:true})}
});
test('no orders, Excel writes, external network or live flags in seconds publisher',()=>{
 const src=fs.readFileSync(new URL('../tools/no12_private_rss_seconds_publish.mjs',import.meta.url),'utf8');
 for(const re of [/RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,/\bfetch\s*\(/,
   /Excel.Application/,/productionReady\s*:\s*true/,/orderTransmission\s*:\s*true/])
  assert.doesNotMatch(src,re);
});
