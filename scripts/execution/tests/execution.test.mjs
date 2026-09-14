import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {ExecutionRuntime,TransmissionLockedAdapter,MockExecutionAdapter,recoverStoppedWriter} from '../runtime.mjs';
import {FREEZE,VERSIONS,SAFETY,orderIntent,fingerprint,LIMIT_KEYS} from '../contract.mjs';
const AT='2026-08-07T01:00:00.000Z',H='a'.repeat(64);
export const limits={maxSingleOrderJpy:500000,maxSymbolExposureJpy:900000,maxGrossExposureJpy:1500000,maxNetExposureJpy:1500000,maxOpenPositions:10,maxOrdersPerDecision:1,maxOrdersPerDay:100,maxDailyLossJpy:100000,maxDailyLossPct:10,maxPositionQuantity:10000,maxPendingExposureJpy:1000000,maxAccountAgeMs:30000,maxFeedAgeMs:30000,maxDecisionAgeMs:30000};
export const config=(changes={})=>({mode:'SYNTHETIC_FIXTURE',freezeSha256:FREEZE,repoHead:'61cb50b7eea670c8473811a4198f919e7065671b',fixtureHash:H,sessionDate:'2026-08-07',startedAt:AT,symbols:['7203.T','6758.T'],initialCashJpy:1000000,limits,...changes});
const decision=(changes={})=>({decisionId:'d1',sessionDate:'2026-08-07',decisionAt:AT,createdAt:AT,symbol:'7203.T',direction:'LONG',action:'ENTER',quantity:300,referencePrice:100,orderType:'LIMIT',limitPrice:100,timeInForce:'DAY',...VERSIONS,sourceEvidenceHash:H,decisionEvidenceHash:H,...changes});
const results=[];
function scenario(name,fn){test(name,()=>{fn();results.push({name,status:'PASS'});});}
function harness(changes={}){
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'ark-execution-'));const cfg=config(changes);let rt=new ExecutionRuntime(dir,cfg),seq=0;
  const h={dir,cfg,get rt(){return rt;},send(kind,fields={}){return rt.process({eventId:`e${++seq}`,kind,at:AT,...fields});},
    context(changes={}){const s=rt.snapshot();const account={...s.portfolio,openOrders:Object.values(s.orders).filter(o=>['SUBMITTED','ACCEPTED','PARTIALLY_FILLED','CANCEL_REQUESTED','UNKNOWN','RECONCILIATION_REQUIRED','SUBMISSION_REQUESTED'].includes(o.status)).map(o=>({orderIntentId:o.intent.orderIntentId,remainingQuantity:o.intent.quantity-o.filledQuantity})).sort((a,b)=>a.orderIntentId.localeCompare(b.orderIntentId))};
      return h.send('CONTEXT',{evidenceHash:H,context:{msiiConnected:true,excelConnected:true,networkConnected:true,engineReady:true,finalizationPassed:true,adapterAvailable:true,feedAt:AT,accountAt:AT,account,...changes}});},
    ready(d={}){h.context();h.send('MODE',{operator:'fixture',mode:'SHADOW'});const {orderIntentId}=h.send('CREATE',{decision:decision(d)});h.send('VALIDATE',{orderIntentId});return orderIntentId;},
    accepted(d={}){const id=h.ready(d);assert.equal(h.send('REQUEST',{orderIntentId:id}).status,'SUBMISSION_REQUESTED');h.send('ADAPTER_RESPONSE',{orderIntentId:id,status:'SUBMITTED'});h.send('ACCEPT',{orderIntentId:id});return id;},
    restart(){rt.close();rt=new ExecutionRuntime(dir,cfg);},
    close(){rt.close();fs.rmSync(dir,{recursive:true,force:true});}};return h;
}
function withH(fn,changes={}){const h=harness(changes);try{fn(h);}finally{h.close();}}
scenario('intent BUY/SELL and LONG/SHORT close mapping',()=>{
  for(const direction of ['LONG','SHORT'])for(const action of ['ENTER','EXIT']){
    const i=orderIntent(decision({direction,action}),{symbols:['7203.T'],position:{symbol:'7203.T',direction,quantity:300}});
    assert.equal(i.side,(direction==='LONG')!==(action==='EXIT')?'BUY':'SELL');assert.equal(i.positionEffect,action==='ENTER'?'OPEN':'CLOSE');
  }
});
scenario('invalid intent identity/evidence/quantity/time is rejected',()=>{
  for(const patch of [{quantity:0},{quantity:99},{symbol:'UNKNOWN'},{direction:'BUY'},{sourceEvidenceHash:''},{decisionAt:'2026-08-07T01:01:00Z'},{entryVersion:'changed'},{orderType:'UNKNOWN'},{timeInForce:'IOC'},{limitPrice:NaN},{action:'EXIT'}])assert.throws(()=>orderIntent(decision(patch),{symbols:['7203.T']}));
});
scenario('idempotency canonical across object key order and restart',()=>withH(h=>{
  const d=decision();const id=h.send('CREATE',{decision:d}).orderIntentId;h.restart();
  const again=h.send('CREATE',{decision:Object.fromEntries(Object.entries(d).reverse())});assert.equal(again.orderIntentId,id);assert.equal(again.duplicate,true);
  assert.equal(Object.keys(h.rt.snapshot().orders).length,1);
  assert.throws(()=>h.send('CREATE',{decision:decision({quantity:400})}),/CONFLICTING_DECISION/);
}));
scenario('three partial fills conserve cash, quantity and average; duplicates rejected',()=>withH(h=>{
  const id=h.accepted();for(const [n,price]of [99,98,100].entries())h.send('FILL',{orderIntentId:id,fillId:`f${n}`,quantity:100,price,feeJpy:1});
  const s=h.rt.snapshot(),o=s.orders[id];assert.equal(o.status,'FILLED');assert.equal(o.averageFillPrice,99);assert.equal(s.positions['7203.T'].quantity,300);assert.equal(s.cashJpy,970297);assert.equal(s.realizedPnl,-3);
  h.restart();assert.throws(()=>h.send('FILL',{orderIntentId:id,fillId:'f0',quantity:100,price:99,feeJpy:1}));assert.equal(h.rt.snapshot().positions['7203.T'].quantity,300);
  assert.throws(()=>h.send('ADAPTER_RESPONSE',{orderIntentId:id,status:'SUBMITTED'}));
}));
scenario('duplicate fill with distinct callback ID and overfill are atomic rejects',()=>withH(h=>{
  const id=h.accepted();h.send('FILL',{orderIntentId:id,fillId:'f',quantity:100,price:100,feeJpy:0});const before=h.rt.snapshot();
  assert.throws(()=>h.send('FILL',{orderIntentId:id,fillId:'f',quantity:100,price:100,feeJpy:0}),/DUPLICATE_FILL/);
  assert.throws(()=>h.send('FILL',{orderIntentId:id,fillId:'f2',quantity:300,price:100,feeJpy:0}),/OVERFILL/);assert.deepEqual(h.rt.snapshot().positions,before.positions);assert.equal(h.rt.snapshot().cashJpy,before.cashJpy);assert.equal(h.rt.snapshot().mode,'DISARMED');
}));
for(const direction of ['LONG','SHORT'])scenario(`${direction} open/close cash collateral and realized PnL`,()=>withH(h=>{
  const open=h.accepted({direction});h.send('FILL',{orderIntentId:open,fillId:'open',quantity:300,price:100,feeJpy:3});
  assert.equal(h.rt.snapshot().cashJpy,969997); // Short proceeds are not reusable.
  const close=h.accepted({decisionId:'exit',direction,action:'EXIT',referencePrice:110,limitPrice:110});
  h.send('FILL',{orderIntentId:close,fillId:'close',quantity:300,price:110,feeJpy:3});
  const s=h.rt.snapshot();assert.equal(Object.keys(s.positions).length,0);assert.equal(s.cashJpy,1000000+(direction==='LONG'?3000:-3000)-6);assert.equal(s.realizedPnl,s.cashJpy-1000000);
}));
scenario('rejection and cancellation do not fabricate fills',()=>withH(h=>{
  const id=h.ready();h.send('REQUEST',{orderIntentId:id});h.send('ADAPTER_RESPONSE',{orderIntentId:id,status:'REJECTED'});assert.equal(h.rt.snapshot().cashJpy,1000000);
  const id2=h.accepted({decisionId:'d2'});h.send('CANCEL_REQUEST',{orderIntentId:id2});h.send('CANCELLED',{orderIntentId:id2});assert.equal(h.rt.snapshot().orders[id2].status,'CANCELLED');assert.throws(()=>h.send('ACCEPT',{orderIntentId:id2}));
}));
for(const key of ['msiiConnected','excelConnected','networkConnected','engineReady','finalizationPassed','adapterAvailable'])scenario(`preflight fails ${key}`,()=>withH(h=>{
  h.context({[key]:false});h.send('MODE',{operator:'test',mode:'ARM_REQUESTED'});const r=h.send('MODE',{operator:'test',mode:'ARMED'});assert.ok(r.reasons.length);assert.equal(h.rt.snapshot().mode,'DISARMED');
}));
scenario('stale feed/account and future context fail closed',()=>withH(h=>{
  for(const field of ['feedAt','accountAt']){h.context({[field]:'2026-08-07T00:00:00Z'});h.send('MODE',{operator:'test',mode:'ARM_REQUESTED'});assert.ok(h.send('MODE',{operator:'test',mode:'ARMED'}).reasons.length);}
  assert.throws(()=>h.context({feedAt:'2026-08-07T02:00:00Z'}),/NONCAUSAL/);
}));
scenario('unknown/mismatched external position and buying power cannot arm or close',()=>withH(h=>{
  for(const change of [{positions:null},{positions:[{symbol:'7203.T',direction:'LONG',quantity:100}]},{buyingPower:null},{cashJpy:900000}]){
    const account={...h.rt.snapshot().portfolio,openOrders:[],...change};assert.equal(h.context({account}).status,'MISMATCH');h.send('MODE',{operator:'test',mode:'ARM_REQUESTED'});assert.ok(h.send('MODE',{operator:'test',mode:'ARMED'}).reasons.length);
  }
}));
for(const [key,value,reason]of [['maxSingleOrderJpy',1,'SINGLE_ORDER_LIMIT'],['maxSymbolExposureJpy',1,'SYMBOL_EXPOSURE_LIMIT'],['maxGrossExposureJpy',1,'GROSS_EXPOSURE_LIMIT'],['maxNetExposureJpy',1,'NET_EXPOSURE_LIMIT'],['maxPositionQuantity',100,'POSITION_QUANTITY_LIMIT'],['maxPendingExposureJpy',1,'PENDING_EXPOSURE_LIMIT']])scenario(`hard gate ${key}`,()=>withH(h=>{const id=h.ready();assert.ok(h.rt.snapshot().orders[id].blockReasons.includes(reason));},{limits:{...limits,[key]:value}}));
scenario('missing/invalid limits never default permissively',()=>{for(const key of LIMIT_KEYS){const cfg=config({limits:{...limits,[key]:null}});const dir=fs.mkdtempSync(path.join(os.tmpdir(),'ark-bad-'));try{assert.throws(()=>new ExecutionRuntime(dir,cfg));}finally{fs.rmSync(dir,{recursive:true,force:true});}}});
scenario('pending orders reserve buying power and cannot net away exposure',()=>withH(h=>{
  const first=h.ready({quantity:5000});assert.equal(h.rt.snapshot().orders[first].status,'READY');
  const second=h.ready({decisionId:'d2',symbol:'6758.T',quantity:6000,direction:'SHORT'});assert.ok(h.rt.snapshot().orders[second].blockReasons.includes('INSUFFICIENT_BUYING_POWER'));
},{limits:{...limits,maxSingleOrderJpy:1000000}}));
scenario('max position count includes pending symbols',()=>withH(h=>{h.ready();const id=h.ready({decisionId:'other',symbol:'6758.T'});assert.ok(h.rt.snapshot().orders[id].blockReasons.includes('POSITION_COUNT_LIMIT'));},{limits:{...limits,maxOpenPositions:1}}));
scenario('daily order count includes submitted orders',()=>withH(h=>{h.accepted();const id=h.ready({decisionId:'other',symbol:'6758.T'});assert.ok(h.rt.snapshot().orders[id].blockReasons.includes('DAILY_ORDER_LIMIT'));},{limits:{...limits,maxOrdersPerDay:1}}));
scenario('external cash flow never changes trading PnL; withdrawal invalidates readiness',()=>withH(h=>{
  const id=h.ready({quantity:5000});h.send('CASH_FLOW',{cashFlowId:'w',flow:{type:'WITHDRAWAL',amountJpy:600000}});
  let s=h.rt.snapshot();assert.equal(s.cashJpy,400000);assert.equal(s.realizedPnl,0);assert.equal(s.portfolio.equityJpy,400000);h.context();assert.ok(h.send('REQUEST',{orderIntentId:id}).reasons.includes('INSUFFICIENT_BUYING_POWER'));
  h.send('CASH_FLOW',{cashFlowId:'d',flow:{type:'DEPOSIT',amountJpy:300000}});h.send('CASH_FLOW',{cashFlowId:'m',flow:{type:'MANUAL_ADJUSTMENT',amountJpy:-100,reason:'synthetic correction'}});s=h.rt.snapshot();assert.equal(s.cashJpy,699900);assert.equal(s.realizedPnl,0);assert.throws(()=>h.send('CASH_FLOW',{cashFlowId:'w',flow:{type:'WITHDRAWAL',amountJpy:1}}));
}));
scenario('daily marked loss blocks ARM and new entry',()=>withH(h=>{const id=h.accepted();h.send('FILL',{orderIntentId:id,fillId:'x',quantity:300,price:100,feeJpy:0});h.send('MARK',{symbol:'7203.T',price:50});const other=h.ready({decisionId:'other',symbol:'6758.T'});assert.ok(h.rt.snapshot().orders[other].blockReasons.includes('DAILY_LOSS_LIMIT'));},{limits:{...limits,maxDailyLossJpy:1000}}));
scenario('EXIT_ONLY admits known risk-reducing close and reserves close quantity',()=>withH(h=>{
  h.context();h.send('MODE',{operator:'test',mode:'EXIT_ONLY'});
  const entry=h.send('CREATE',{decision:decision()}).orderIntentId;assert.ok(h.send('VALIDATE',{orderIntentId:entry}).reasons.includes('EXIT_ONLY'));
  const d=decision({decisionId:'close',action:'EXIT'}),id=h.send('CREATE',{decision:d}).orderIntentId;assert.equal(h.send('VALIDATE',{orderIntentId:id}).status,'READY');
  const id2=h.send('CREATE',{decision:{...d,decisionId:'close2'}}).orderIntentId;assert.ok(h.send('VALIDATE',{orderIntentId:id2}).reasons.includes('CLOSE_POSITION_UNKNOWN_OR_RESERVED'));
},{positions:[{symbol:'7203.T',direction:'LONG',quantity:300,averagePrice:100}]}));
scenario('emergency stop persists and no submission/cancel/automatic clear occurs',()=>withH(h=>{
  const id=h.ready();h.send('EMERGENCY_STOP');h.restart();assert.equal(h.rt.snapshot().mode,'EMERGENCY_STOP');assert.equal(h.rt.snapshot().orders[id].status,'BLOCKED');assert.throws(()=>h.send('MODE',{operator:'test',mode:'SHADOW'}));
  assert.throws(()=>h.send('CLEAR_EMERGENCY',{operator:'test',evidenceHash:H,confirm:false}));h.send('CLEAR_EMERGENCY',{operator:'test',evidenceHash:H,confirm:true});assert.equal(h.rt.snapshot().mode,'DISARMED');assert.equal(h.rt.snapshot().reconciliation,'UNKNOWN');
}));
for(const stage of ['CREATED','READY','SUBMISSION_REQUESTED','SUBMITTED','PARTIALLY_FILLED','FILLED','RECONCILIATION_REQUIRED'])scenario(`restart at ${stage} never resubmits or duplicates fills`,()=>withH(h=>{
  let id;
  if(stage==='CREATED')id=h.send('CREATE',{decision:decision()}).orderIntentId;
  else id=h.ready();
  if(['SUBMISSION_REQUESTED','SUBMITTED','PARTIALLY_FILLED','FILLED','RECONCILIATION_REQUIRED'].includes(stage))h.send('REQUEST',{orderIntentId:id});
  if(['SUBMITTED','PARTIALLY_FILLED','FILLED','RECONCILIATION_REQUIRED'].includes(stage))h.send('ADAPTER_RESPONSE',{orderIntentId:id,status:'SUBMITTED'});
  if(['PARTIALLY_FILLED','FILLED'].includes(stage)){h.send('ACCEPT',{orderIntentId:id});h.send('FILL',{orderIntentId:id,fillId:'f',quantity:stage==='FILLED'?300:100,price:100,feeJpy:0});}
  if(stage==='RECONCILIATION_REQUIRED'){h.send('UNKNOWN',{orderIntentId:id});h.send('RECONCILIATION_REQUIRED',{orderIntentId:id});}
  const before=h.rt.snapshot();h.restart();const after=h.rt.snapshot();assert.equal(after.cashJpy,before.cashJpy);assert.deepEqual(after.positions,before.positions);assert.equal(after.orders[id].submissionCount,before.orders[id].submissionCount);assert.equal(after.mode,'DISARMED');assert.equal(after.reconciliation,'UNKNOWN');
  if(!['CREATED','READY','FILLED','RECONCILIATION_REQUIRED'].includes(stage))assert.equal(after.orders[id].status,'UNKNOWN');
}));
scenario('unknown outcome requires explicit evidence/account reconciliation, never retries',()=>withH(h=>{
  const id=h.ready();h.send('REQUEST',{orderIntentId:id});h.send('ADAPTER_RESPONSE',{orderIntentId:id,status:'UNKNOWN'});assert.throws(()=>h.send('REQUEST',{orderIntentId:id}));h.send('RECONCILIATION_REQUIRED',{orderIntentId:id});
  assert.throws(()=>h.send('RESOLVE_ORDER',{orderIntentId:id,operator:'test',evidenceHash:H,status:'ACCEPTED',filledQuantity:0}));h.context();h.send('RESOLVE_ORDER',{orderIntentId:id,operator:'test',evidenceHash:H,status:'ACCEPTED',filledQuantity:0});assert.equal(h.rt.snapshot().orders[id].submissionCount,1);
}));
scenario('same event callback replay is no-op; changed event and backwards time reject',()=>withH(h=>{
  const e={eventId:'same',kind:'CREATE',at:AT,decision:decision()};const a=h.rt.process(e);assert.equal(h.rt.process(e).duplicate,true);assert.equal(Object.keys(h.rt.snapshot().orders).length,1);assert.throws(()=>h.rt.process({...e,decision:decision({quantity:100})}),/CONFLICTING_EVENT/);assert.throws(()=>h.send('DISCONNECT',{at:'2026-08-07T00:59:00Z'}),/NONMONOTONIC/);assert.ok(a.orderIntentId);
}));
scenario('tampered journal and torn tail fail closed preserving bytes',()=>{
  for(const torn of [false,true]){const h=harness();h.ready();h.rt.close();const file=path.join(h.dir,'execution.jsonl');let bytes=fs.readFileSync(file,'utf8');bytes=torn?bytes+'{"partial":':bytes.replace('"cashJpy":','"badCash":');if(!torn)bytes=bytes.replace('"initialCashJpy":1000000','"initialCashJpy":1');fs.writeFileSync(file,bytes);assert.throws(()=>new ExecutionRuntime(h.dir,h.cfg));assert.equal(fs.readFileSync(file,'utf8'),bytes);fs.rmSync(h.dir,{recursive:true,force:true});}
});
scenario('single writer lock refuses concurrent process',()=>withH(h=>{assert.throws(()=>new ExecutionRuntime(h.dir,h.cfg),/EEXIST/);}));
scenario('production boundary cannot transmit even with spoofed flags or fixture adapter',()=>withH(h=>{
  const adapter=new TransmissionLockedAdapter();for(const flags of [{},{executionAllowed:true,transmitted:true},new MockExecutionAdapter()]){assert.equal(adapter.submitOrder(flags).reason,'TRANSMISSION_LOCKED');assert.equal(adapter.cancelOrder(flags).transmitted,false);assert.equal(h.rt.submitOrder(flags).blocked,true);}
  h.context();h.send('MODE',{operator:'test',mode:'ARM_REQUESTED'});assert.ok(h.send('MODE',{operator:'test',mode:'ARMED'}).reasons.includes('TRANSMISSION_LOCKED'));
  const id=h.ready();assert.ok(h.send('REQUEST',{orderIntentId:id}).reasons.includes('TRANSMISSION_LOCKED'));assert.throws(()=>h.send('ADAPTER_RESPONSE',{orderIntentId:id,status:'SUBMITTED'}));assert.deepEqual(h.rt.snapshot().safety,SAFETY);
},{mode:'TRANSMISSION_LOCKED'}));
scenario('close fill releases cash before same-timestamp entry; no double cost',()=>withH(h=>{
  const id=h.accepted({decisionId:'close',action:'EXIT'});h.send('FILL',{orderIntentId:id,fillId:'close',quantity:300,price:100,feeJpy:1});
  const next=h.ready({decisionId:'new',symbol:'6758.T'});assert.equal(h.rt.snapshot().orders[next].status,'READY');assert.equal(h.rt.snapshot().cashJpy,30999);
},{initialCashJpy:1000,positions:[{symbol:'7203.T',direction:'LONG',quantity:300,averagePrice:100}]}));
scenario('strong process exit retains lock; explicit verified recovery preserves journal',()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'ark-process-crash-')),cfg=config();
  try{
    const program=`import {ExecutionRuntime} from './scripts/execution/runtime.mjs';const r=new ExecutionRuntime(${JSON.stringify(dir)},${JSON.stringify(cfg)});r.process(${JSON.stringify({eventId:'crash-create',kind:'CREATE',at:AT,decision:decision()})});process.exit(0);`;
    const run=spawnSync(process.execPath,['--input-type=module','-e',program],{encoding:'utf8'});assert.equal(run.status,0,run.stderr);
    assert.throws(()=>new ExecutionRuntime(dir,cfg),/EEXIST/);
    const file=path.join(dir,'execution.jsonl'),bytes=fs.readFileSync(file),sha=createHash('sha256').update(bytes).digest('hex');
    assert.throws(()=>recoverStoppedWriter(dir,cfg,{operator:'test',confirmAllWritersStopped:false,expectedJournalSha256:sha}));
    assert.throws(()=>recoverStoppedWriter(dir,cfg,{operator:'test',confirmAllWritersStopped:true,expectedJournalSha256:H}));
    const recovery=recoverStoppedWriter(dir,cfg,{operator:'test',confirmAllWritersStopped:true,expectedJournalSha256:sha});assert.ok(fs.existsSync(recovery.archive));assert.deepEqual(fs.readFileSync(file),bytes);
    const rt=new ExecutionRuntime(dir,cfg);assert.equal(Object.keys(rt.snapshot().orders).length,1);assert.equal(rt.snapshot().mode,'DISARMED');rt.close();
  }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
scenario('journal append failure leaves memory unchanged and blocks further commands',()=>withH(h=>{
  const before=h.rt.snapshot(),write=fs.writeFileSync;
  try{fs.writeFileSync=()=>{throw Error('synthetic disk failure');};assert.throws(()=>h.send('CREATE',{decision:decision()}),/synthetic disk failure/);}finally{fs.writeFileSync=write;}
  const after=h.rt.snapshot();assert.deepEqual(after.orders,before.orders);assert.equal(after.journalHealthy,false);assert.throws(()=>h.send('DISCONNECT'),/JOURNAL_FAILED/);
}));
scenario('prototype identities and cross-session events cannot corrupt state',()=>withH(h=>{
  assert.throws(()=>h.send('CASH_FLOW',{cashFlowId:'__proto__',flow:{type:'DEPOSIT',amountJpy:1}}));assert.throws(()=>h.send('DISCONNECT',{at:'2026-08-08T01:00:00Z'}),/SESSION_BOUNDARY/);
}));
scenario('invalid context revokes older readiness and remains revoked after replay',()=>withH(h=>{
  const id=h.ready();assert.throws(()=>h.context({accountAt:'bad'}));assert.equal(h.rt.snapshot().mode,'DISARMED');assert.equal(h.rt.snapshot().reconciliation,'UNKNOWN');h.restart();assert.equal(h.rt.snapshot().reconciliation,'UNKNOWN');assert.ok(h.send('REQUEST',{orderIntentId:id}).reasons.length);
}));
// Evidence exports are derived from assertions; never overwrite an earlier run.
process.on('exit',()=>{if(process.env.ARK_EXECUTION_EVIDENCE_DIR){const dir=process.env.ARK_EXECUTION_EVIDENCE_DIR;fs.mkdirSync(dir,{recursive:false});for(const name of ['execution-contract','idempotency','state-machine','reconciliation','risk-gate','restart-recovery','transmission-lock'])fs.writeFileSync(path.join(dir,name+'-evidence.json'),JSON.stringify({schemaId:'ARK_EXECUTION_TEST_EVIDENCE_V1',suite:name,source:'SYNTHETIC_ASSERTIONS_ONLY',allAssertionsPassed:process.exitCode===undefined||process.exitCode===0,assertedScenarios:results.filter(x=>({ 'execution-contract':/intent|prototype|same-timestamp/,idempotency:/duplic|idempot|same event/, 'state-machine':/fill|rejection|cancel|UNKNOWN|unknown outcome/, reconciliation:/reconcil|unknown|external|close/, 'risk-gate':/gate|limit|pending|loss|preflight|stale|EXIT_ONLY/, 'restart-recovery':/restart|journal|process|writer|replay/, 'transmission-lock':/production|emergency|preflight/ }[name]).test(x.name)),totalScenarioCount:results.length,safety:SAFETY,freezeSha256:FREEZE},null,2)+'\n',{flag:'wx'});}});
