import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {inspectSavedNo11MarketShadow as inspect,readSavedNo11MarketShadow as read} from '../runtime/no11_saved_market_shadow_bridge.mjs';
const time=s=>'2026-10-13T'+s+'+09:00';
const fixture=()=>({
 schemaId:'ARK_NO11_LOCAL_MARKET_SHADOW_V2',symbol:'7203.T',
 source:'MarketSpeedII_RssMarket',price:2968,marketClock:'12:30:05',
 marketDaySource:'PC_JST_INFERRED_NOT_BROKER_CERTIFIED',
 sourceAsOf:time('12:30:05'),observedAt:time('12:30:06'),
 sourceAgeSeconds:1,marketFresh:true,status:'LOCAL_MARKET_OBSERVED_FRESH',
 nonAtomicExcelCellRead:true,brokerArrivalCertified:false,
 originalNo11DecisionEngineConnected:false,productionReady:false,orderTransmission:false
});
test('fresh local RSS snapshot maps to market ONLY; no model or order permission',()=>{
 const r=inspect({snapshot:fixture(),now:new Date(time('12:30:07'))});
 assert.equal(r.market.lastPrice,2968);
 assert.equal(r.market.receivedAt,'2026-10-13T03:30:06.000Z');
 assert.equal(r.market.knownAt,'2026-10-13T03:30:07.000Z');
 assert.equal(r.originalFrozenAsOfGatePassed,false);
 assert.equal(r.originalFrozenH2H3H5Executed,false);
 assert.equal(r.productionReady,false);
 assert.equal(r.orderTransmission,false);
});
test('11:30 market clock observed at 11:39 fails closed, as actually seen on PC',()=>{
 const x=fixture();x.marketClock='11:30:00';x.sourceAsOf=time('11:30:00');
 x.observedAt=time('11:39:44');x.sourceAgeSeconds=584;x.marketFresh=false;
 x.status='LOCAL_MARKET_OBSERVED_STALE';
 assert.throws(()=>inspect({snapshot:x,now:new Date(time('11:39:45'))}),/NO11_MARKET_SHADOW_SOURCE_STALE/);
});
test('old JSON, future timestamp, tampered freshness and producer BLOCKED fail closed',()=>{
 const now=new Date(time('12:30:30'));
 assert.throws(()=>inspect({snapshot:fixture(),now}),/NO11_MARKET_SHADOW_OBSERVATION_STALE/);
 const a=fixture();a.sourceAsOf=time('12:31:00');
 assert.throws(()=>inspect({snapshot:a,now:new Date(time('12:30:07'))}),/NO11_MARKET_SHADOW_CLOCK_INCONSISTENT/);
 const b=fixture();b.marketFresh=false;
 assert.throws(()=>inspect({snapshot:b,now:new Date(time('12:30:07'))}),/NO11_MARKET_SHADOW_STATUS_INCONSISTENT/);
 const c=fixture();c.status='BLOCKED';
 assert.throws(()=>inspect({snapshot:c,now:new Date(time('12:30:07'))}),/NO11_MARKET_SHADOW_PRODUCER_BLOCKED/);
});
test('saved local market JSON can be read with hash but not broker-certified',()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'ark-no11-market-'));
 try{
  const file=path.join(root,'market_shadow_v2.json');
  fs.writeFileSync(file,JSON.stringify(fixture()));
  const r=read({file,now:new Date(time('12:30:07'))});
  assert.match(r.localSnapshotSha256,/^[a-f0-9]{64}$/);
  assert.equal(r.sourceHashCertifiedByBroker,false);
  assert.equal(r.originalFrozenSelectorConnected,false);
 }finally{fs.rmSync(root,{recursive:true,force:true})}
});
test('no false production promotion, orders or model fitting',()=>{
 const s=fs.readFileSync(new URL('../runtime/no11_saved_market_shadow_bridge.mjs',import.meta.url),'utf8');
 for(const pattern of [/RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,
  /Excel.Application/,/\bfetch\s*\(/,/productionReady\s*:\s*true/,
  /orderTransmission\s*:\s*true/])assert.doesNotMatch(s,pattern);
});
