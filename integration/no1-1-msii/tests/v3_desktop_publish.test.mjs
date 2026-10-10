import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {publishNo11V3ReadOnly} from '../tools/no11_v3_desktop_publish.mjs';
import {LOCKED_FLAGS,digest} from '../runtime/locked_intent.mjs';
function fixture() {
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'ark-v3-desktop-'));
 const id='a'.repeat(32),dir=path.join(root,'capture-v3-candidate',id);
 fs.mkdirSync(dir,{recursive:true});
 const now=new Date().toISOString();
 const snap={schemaId:'ARK_ACCOUNT_READONLY_SNAPSHOT_V2',
   capturedAt:now,captureCompletedAt:now,source:'MARKETSPEED_II_RSS',
   mode:'READ_ONLY',captureMethod:'ISOLATED_BULK_CANDIDATE_NOT_PRODUCTION',
   positions:[{symbol:'408A',quantity:180,marketValue:300000}],
   orders:[],executions:[],buyingPower:700000,safety:{...LOCKED_FLAGS}};
 const health={schemaId:'ARK_MSII_RSS_SOURCE_HEALTH_V1',source:'MARKETSPEED_II_RSS',
   readOnly:true,addinLoaded:true,workbookPersisted:true,rssErrors:0,
   healthCapturedAt:now,actualFeedTimestampCertified:false,
   observationBasis:'FINAL_STATUS_RE_READ_NOT_MARKET_SOURCE_TIMESTAMP',
   feeds:Object.fromEntries(Object.entries({capacity:'完了',orders:'配信中',
     executions:'配信中',positions:'配信中'}).map(([key,state])=>[key,{state,observedAt:now}]))};
 const core={schemaId:'ARK_CASH_OWNERSHIP_BASELINE_V1',frozen:true,capturedAt:now,
   source:'MARKETSPEED_II_RSS_EXPLICIT_OWNER_CONFIRMED',
   externalPositions:[{symbol:'408A.T',quantity:180}],arkManagedPositions:[]};
 const owner={...core,baselineSha256:digest(core)};
 const write=(p,x)=>fs.writeFileSync(p,JSON.stringify(x));
 write(path.join(dir,'snapshot.json'),snap);
 write(path.join(dir,'source-health.json'),health);
 write(path.join(root,'ownership-baseline.json'),owner);
 const files=()=>['snapshot.json','source-health.json','desktop-capital-readonly.json',
   'desktop-v3-readonly-receipt.json'].map(x=>path.join(root,x));
 return {root,id,dir,now,snap,health,owner,write,files,
   cleanup(){fs.rmSync(root,{recursive:true,force:true});}};
}
test('fresh V3 exports READ ONLY account pair and private funding preview only',()=>{
 const x=fixture();
 try {
   const p=publishNo11V3ReadOnly({privateRoot:x.root,runId:x.id,now:new Date(x.now)});
   assert.equal(p.status,'READ_ONLY_CAPITAL_PREVIEW');
   assert.equal(p.productionReady,false);
   assert.equal(p.orderTransmission,false);
   assert(x.files().every(fs.existsSync));
   const funding=JSON.parse(fs.readFileSync(path.join(x.root,'desktop-capital-readonly.json'),'utf8'));
   assert.equal(funding.status,'READ_ONLY_CAPITAL_PREVIEW');
   assert.equal(funding.productionReady,false);
   assert.equal(funding.orderTransmission,false);
   assert.equal(funding.personalStockDoubleDeducted,false);
   assert.deepEqual(funding.arkCapitalInputs,{cash:700000,equity:700000,exposure:0});
   assert.equal(JSON.parse(fs.readFileSync(path.join(x.root,'snapshot.json'))).captureMethod,'ISOLATED_BULK_CANDIDATE_NOT_PRODUCTION');
   assert.equal(JSON.parse(fs.readFileSync(path.join(x.root,'source-health.json'))).actualFeedTimestampCertified,false);
   assert(fs.existsSync(path.join(x.root,'ownership-baseline.json')));
   assert(fs.existsSync(path.join(x.dir,'snapshot.json')));
 }finally{x.cleanup();}
});
test('changed broker holdings and baseline hash never get a published official snapshot',()=>{
 for(const tamper of [
   x=>{x.snap.positions[0].quantity=100;x.write(path.join(x.dir,'snapshot.json'),x.snap);},
   x=>{x.owner.baselineSha256='0'.repeat(64);x.write(path.join(x.root,'ownership-baseline.json'),x.owner);},
   x=>{x.snap.orders.push({orderNumber:'123'});x.write(path.join(x.dir,'snapshot.json'),x.snap);}
 ]) {
  const x=fixture();
  try {
   tamper(x);
   assert.throws(()=>publishNo11V3ReadOnly({privateRoot:x.root,runId:x.id}),/V3_CAPITAL_OR_OWNERSHIP_GATE_BLOCKED/);
   assert(!x.files().some(fs.existsSync));
  }finally{x.cleanup();}
 }
});
test('wrong/late feed state, fake broker timestamps, over-25s capture fail closed',()=>{
 const cases=[
   x=>{x.health.feeds.capacity.state='#NAME?';x.write(path.join(x.dir,'source-health.json'),x.health);},
   x=>{x.health.actualFeedTimestampCertified=true;x.write(path.join(x.dir,'source-health.json'),x.health);},
   x=>{x.health.observationBasis='BROKER_PROOF';x.write(path.join(x.dir,'source-health.json'),x.health);},
   x=>{x.snap.capturedAt=new Date(Date.parse(x.now)-26000).toISOString();x.write(path.join(x.dir,'snapshot.json'),x.snap);}
 ];
 for(const tamper of cases) {
   const x=fixture();
   try {
      tamper(x);
      assert.throws(()=>publishNo11V3ReadOnly({privateRoot:x.root,runId:x.id}));
      assert(!x.files().some(fs.existsSync));
   }finally{x.cleanup();}
 }
});
test('cannot select another run directory or follow a private data symlink',()=>{
 const x=fixture();
 try {
   assert.throws(()=>publishNo11V3ReadOnly({privateRoot:x.root,runId:'../not-safe'}),/V3_RUN_ID_INVALID/);
   const link=path.join(x.dir,'source-health.json');
   fs.renameSync(link,link+'.orig');
   fs.symlinkSync(link+'.orig',link);
   assert.throws(()=>publishNo11V3ReadOnly({privateRoot:x.root,runId:x.id}),/V3_HEALTH_UNSAFE/);
 }finally{x.cleanup();}
});
test('no trading interface, order writer or safety-reset entrypoint in publisher',()=>{
 const content=fs.readFileSync(new URL('../tools/no11_v3_desktop_publish.mjs',import.meta.url),'utf8');
 for(const disallowed of [/RssStockOrder\s*\(/i,/RssCancelOrder\s*\(/i,/explicitSafetyReset\s*\(/,/RssMargin/i,/executionAllowed\s*:\s*true/i]) assert.doesNotMatch(content,disallowed);
 assert.match(content,/no11_desktop_cash_preview\.mjs/);
 assert.match(content,/V3_SNAPSHOT_EXPIRED_BEFORE_PUBLISH/);
});

test('previous candidate cannot be replayed or used to claim new account freshness',()=>{
 const x=fixture();
 try {
   publishNo11V3ReadOnly({privateRoot:x.root,runId:x.id});
   const source=fs.readFileSync(path.join(x.root,'snapshot.json'),'utf8');
   assert.throws(()=>publishNo11V3ReadOnly({privateRoot:x.root,runId:x.id}),/V3_CANDIDATE_REPLAY_BLOCKED/);
   assert.equal(fs.readFileSync(path.join(x.root,'snapshot.json'),'utf8'),source);
 }finally{x.cleanup();}
});
test('distinct fresh candidate atomically replaces prior read-only private outputs',()=>{
 const x=fixture();
 try {
   publishNo11V3ReadOnly({privateRoot:x.root,runId:x.id});
   const second='b'.repeat(32);
   const next=path.join(x.root,'capture-v3-candidate',second);
   fs.mkdirSync(next);
   x.write(path.join(next,'snapshot.json'),x.snap);
   x.write(path.join(next,'source-health.json'),x.health);
   const y=publishNo11V3ReadOnly({privateRoot:x.root,runId:second});
   assert.equal(y.runId,second);
   const receipt=JSON.parse(fs.readFileSync(path.join(x.root,'desktop-v3-readonly-receipt.json'),'utf8'));
   assert.equal(receipt.captureRunId,second);
   assert.equal(receipt.productionReady,false);
 }finally{x.cleanup();}
});
