import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {publishNo12PrivateSeconds} from '../tools/no12_private_rss_seconds_publish.mjs';
import {readNo11LocalRssSecondsAsOf as read} from '../runtime/no11_rss_seconds_asof_adapter.mjs';
import {inspectFrozenNo11AsOfShadowInputs as gate,
 NO11_ASOF_GATE_SCHEMA as SCHEMA,NO11_FROZEN_ID as FROZEN
} from '../runtime/frozen_no11_asof_shadow_gate.mjs';
const at=t=>'2026-10-13T'+t+'+09:00';
function fixture(){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'no11-rss-asof-'));
 const candidatePath=path.join(root,'seconds-candidate-'+'c'.repeat(32)+'.json');
 const snapshot={
  schemaId:'ARK_NO12_MSII_RSS_MARKET_SECONDS_OBSERVATION_V1',
  sourceFunction:'RssMarket',evidenceMode:'OBSERVED_READ_ONLY',
  symbol:'7203.T',capturedAt:at('09:30:10'),
  orderPermissionEnabled:false,privateAccountDataIncluded:false,
  samples:[
   {sampledAt:at('09:30:02'),marketDate:'2026/10/13',marketClock:'09:30:01',
    lastPrice:1000,bestBid:999,bestAsk:1001},
   {sampledAt:at('09:30:04'),marketDate:'2026/10/13',marketClock:'09:30:03',
    lastPrice:1002,bestBid:1001,bestAsk:1003},
   {sampledAt:at('09:30:06'),marketDate:'2026/10/13',marketClock:'09:30:05',
    lastPrice:1003,bestBid:1002,bestAsk:1004}
  ]
 };
 fs.writeFileSync(candidatePath,JSON.stringify(snapshot));
 publishNo12PrivateSeconds({privateRoot:root,candidatePath,now:new Date(at('09:30:11'))});
 return {root,decisionAt:at('09:30:12'),now:new Date(at('09:30:11')),
  clean:()=>fs.rmSync(root,{recursive:true,force:true})};
}
const source=(kind,time,seen,known,extras={})=>({
 kind,symbol:'7203.T',sourceAsOf:at(time),receivedAt:at(seen),knownAt:at(known),
 receiptSha256:'a'.repeat(64),...extras
});
test('local RssMarket HH:MM:SS receipt feeds the No.1.1 market ASOF input, never a decision',()=>{
 const f=fixture();try{
  const r=read(f);
  assert.equal(r.status,'LOCAL_RSS_SECONDS_ASOF_MARKET_SOURCE_ONLY');
  assert.equal(r.market.lastPrice,1003);
  assert.equal(r.market.sourceAsOf,'2026-10-13T00:30:05.000Z');
  assert.equal(r.market.receivedAt,'2026-10-13T00:30:06.000Z');
  assert.equal(r.market.knownAt,'2026-10-13T00:30:11.000Z');
  assert.equal(r.marketSourceFreshnessMs,7000);
  assert.equal(r.originalFrozenH2H3H5Executed,false);
  assert.equal(r.productionReady,false);
  assert.equal(r.orderTransmission,false);
 }finally{f.clean()}
});
test('real-source-shape market envelope joins synthetic frozen inputs only as a shadow gate',()=>{
 const f=fixture();try{
  const r=read(f);
  const snapshot={
   schemaId:SCHEMA,frozenId:FROZEN,evidenceMode:'OBSERVED_READ_ONLY',
   session:'2026-10-13',symbol:'7203.T',decisionAt:f.decisionAt,
   capturedAt:f.decisionAt,productionReady:false,orderTransmission:false,
   selector:source('FROZEN_SELECTOR_EVENT','09:29:00','09:29:02','09:29:03',{
    eventId:'2026-10-13|09:29|7203',modelArtifactSha256:'b'.repeat(64)
   }),
   firstEntry:source('FROZEN_FIRST_ENTRY_INTENT','09:30:00','09:30:01','09:30:02',{
    barClosedAt:at('09:30:00'),intentAt:at('09:30:00'),score:0.8,threshold:0.7
   }),
   state9:source('FROZEN_NATIVE_STATE9_CLOSED','09:30:00','09:30:01','09:30:02',{
    barClosedAt:at('09:30:00'),primary:'RISE'
   }),
   market:r.market
  };
  const audit=gate({mode:'SYNTHETIC_OFFLINE_ONLY',snapshot,now:new Date(at('09:30:13'))});
  assert.equal(audit.status,'ASOF_SOURCE_TIMELINE_ACCEPTED_RESEARCH_ONLY');
  assert.equal(audit.originalFrozenModelsExecuted,false);
  assert.equal(audit.productionReady,false);
  assert.equal(audit.orderTransmission,false);
 }finally{f.clean()}
});
test('market snapshot altered after publisher cannot pass its pinned local receipt',()=>{
 const f=fixture();try{
  fs.appendFileSync(path.join(f.root,'market-seconds-readonly-observed.json'),' ');
  assert.throws(()=>read(f),/NO11_RSS_SECONDS_RECEIPT_IDENTITY_INVALID/);
 }finally{f.clean()}
});
test('a source that is read after decision cannot be used retroactively',()=>{
 const f=fixture();try{
  assert.throws(()=>read({...f,decisionAt:at('09:30:10')}),
   /NO11_RSS_SECONDS_DECISION_NOT_CAUSAL_OR_STALE/);
 }finally{f.clean()}
});
test('old source price cannot be passed off as fresh by a recent file capture',()=>{
 const f=fixture();try{
  const objPath=path.join(f.root,'market-seconds-readonly-observed.json');
  const recPath=path.join(f.root,'market-seconds-readonly-receipt.json');
  const obj=JSON.parse(fs.readFileSync(objPath,'utf8'));
  for(const o of obj.observations){
   o.sourceAsOf='2026-10-13T00:29:00.000Z';
   o.ageMs=Date.parse(o.sampledAt)-Date.parse(o.sourceAsOf);
  }
  obj.sourceTimeAdvanceCount=0;
  obj.status='PC_OBSERVED_SAMPLES_WITHOUT_EXCHANGE_TIME_ADVANCE';
  obj.maxSourceAgeMs=Math.max(...obj.observations.map(o=>o.ageMs));
  const bytes=Buffer.from(JSON.stringify(obj)+'\n');
  fs.writeFileSync(objPath,bytes);
  const receipt=JSON.parse(fs.readFileSync(recPath,'utf8'));
  receipt.evidenceSha256=createHash('sha256').update(bytes).digest('hex');
  receipt.sourceTimeAdvanceCount=0;
  fs.writeFileSync(recPath,JSON.stringify(receipt));
  assert.throws(()=>read(f),/NO11_RSS_SECONDS_LATEST_PRICE_TOO_OLD/);
 }finally{f.clean()}
});
test('a malformed receipt or future exchange clock cannot be promoted to source',()=>{
 const f=fixture();try{
  const p=path.join(f.root,'market-seconds-readonly-receipt.json');
  const obj=JSON.parse(fs.readFileSync(p,'utf8'));
  obj.productionReady=true;fs.writeFileSync(p,JSON.stringify(obj));
  assert.throws(()=>read(f),/NO11_RSS_SECONDS_RECEIPT_IDENTITY_INVALID/);
 }finally{f.clean()}
});
test('the bridge never writes to Excel, transmits orders or generates Frozen ML scores',()=>{
 const src=fs.readFileSync(new URL('../runtime/no11_rss_seconds_asof_adapter.mjs',import.meta.url),'utf8');
 for(const re of [/RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,
   /Excel.Application/,/\bfetch\s*\(/,/productionReady\s*:\s*true/,
   /orderTransmission\s*:\s*true/])
  assert.doesNotMatch(src,re);
});
