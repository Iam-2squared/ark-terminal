import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {digest} from '../../../integration/no1-1-msii/runtime/locked_intent.mjs';
import {compileCashOrderArguments,compileCancelArguments,verifyMsiiArguments,MSII_CASH_ACCOUNTS} from '../runtime/no11_msii_argument_contract.mjs';
import {buildNo12SyntheticMsiiOrderText,NO12_ORDER_INTENT_SCHEMA} from '../runtime/synthetic_msii_draft.mjs';
import {compileTransportCommand,validateTransportCommand,validateDispatchPermit,validateTransportPacket,dispatchPreparedCommand,PERMIT_SCHEMA,CONFIG_SCHEMA} from '../tools/no11_msii_transport.mjs';

const day='2026-10-26',created=day+'T09:30:10+09:00',now=day+'T09:30:11+09:00';
const script=fileURLToPath(new URL('../tools/no11_msii_transport.mjs',import.meta.url));
const ps=fileURLToPath(new URL('../windows/Invoke-No11MsiiOrder.ps1',import.meta.url));
function seal(x,field){const {[field]:old,...body}=x;return {...body,[field]:digest(body)}}
function fixture(kind='ORDER',side='BUY'){
 const command=compileTransportCommand({commandId:'a'.repeat(64),kind,sessionDate:day,rssSessionKey:'test-excel-session-1',
  rssOrderId:81,intentId:'b'.repeat(64),symbol:'7203.T',side,quantity:200,account:'特定',
  targetOrderNumber:kind==='CANCEL'?'12345':null,createdAtJst:created,evidenceMode:'LIVE_OBSERVED',
  orderTerms:kind==='ORDER'?{orderType:'LIMIT',limitPrice:100.1,timeInForce:'DAY',sor:false,accountType:0,accountTypeVerified:true}:null});
 const permit=seal({schemaId:PERMIT_SCHEMA,commandId:command.commandId,commandSha256:command.commandSha256,
  kind,sessionDate:day,rssSessionKey:command.rssSessionKey,rssOrderId:command.rssOrderId,intentId:command.intentId,
  targetOrderNumber:command.targetOrderNumber,preparedAtJst:created,begunAtJst:day+'T09:30:10.5+09:00',state:'IN_FLIGHT_COMMITTED'},'permitSha256');
 const config={schemaId:CONFIG_SCHEMA,mode:'LIVE',orderTransmission:true,operatorEnabled:true,approvedForSession:true,
  sessionDate:day,rssSessionKey:command.rssSessionKey,expiresAtJst:day+'T15:30:00+09:00',
  workbookPath:'C:\\ArkPrivate\\Transport.xlsx',worksheetName:'Transport',formulaCell:'A1',triggerCell:'B1',guardCell:'C1',sessionCell:'D1',
  guardValue:'ARK_NO11_SEND_ONCE',expectedExcelPid:123,expectedExcelHwnd:456,expectedExcelStartedAt:day+'T00:00:00Z',
  expectedAddInPaths:['C:\\Fixture\\MarketSpeed2_RSS_64bit.xll','C:\\Fixture\\MarketSpeed2_RSS_VBA.xlam'],expectedOpenWorkbooks:['C:\\ArkPrivate\\Transport.xlsx'],
  dispatchDirectory:'C:\\ArkPrivate\\dispatch',permitMaximumAgeMs:10000,responseTimeoutMs:1000};
 return {command,permit,config};
}
function mockSink(reply={}){const calls=[];return {kind:'SYNTHETIC_TEST',calls,async dispatch(packet){
 calls.push(packet);return {commandId:packet.command.commandId,commandSha256:packet.command.commandSha256,rssOrderId:packet.command.rssOrderId,
  status:'SENT_AWAITING_RECONCILIATION',reason:'MOCK_ONLY',dispatchAttempted:true,...reply};
}}}

test('pure argument extraction preserves the established synthetic 20-argument preview across cash order settings',()=>{
 for(const side of ['BUY','SELL'])for(const accountType of [0,1,2,3])for(const sor of [false,true])for(const orderType of ['MARKET','LIMIT']){
  const core={schemaId:NO12_ORDER_INTENT_SCHEMA,evidenceMode:'SYNTHETIC_OFFLINE_ONLY',symbol:'7203.T',side,
   positionEffect:side==='BUY'?'OPEN':'CLOSE',quantity:200,cashOnly:true,marginAllowed:false,shortSellingAllowed:false,
   syntheticCashAndSlotReserved:side==='BUY',syntheticArkOwnedPosition:side==='SELL',timeInForce:'DAY',sor,orderType,
   limitPrice:orderType==='LIMIT'?100.1:null,accountType,accountTypeVerified:true,transmitted:false,productionReady:false};
  const intent={...core,intentSha256:digest(core)};
  const preview=buildNo12SyntheticMsiiOrderText({intent,orderIdentity:{schemaId:'ARK_NO12_SYNTHETIC_ORDER_ID_OBSERVATION_V1',
   evidenceMode:'SYNTHETIC_OFFLINE_ONLY',observedAt:created,reservedOrderId:81,usedOrderIds:[],sourceIntentSha256:intent.intentSha256,syntheticUniquenessChecked:true},now});
  assert.deepEqual(preview.arguments,compileCashOrderArguments({...core,rssOrderId:81}));
  const expected=['81','0','7203.T',side==='BUY'?'3':'1','0',sor?'1':'0','200',orderType==='MARKET'?'0':'1',orderType==='MARKET'?'':'100.1','1','',String(accountType),'','','','','0','','',''];
  assert.deepEqual(preview.arguments,expected);
  assert.equal(preview.orderTransmission,false);assert.equal(preview.formulaCellType,'TEXT');
 }
});
test('the common cancel compiler enforces exactly three canonical arguments',()=>{
 assert.deepEqual(compileCancelArguments({rssOrderId:2147483647,orderNumber:'12345'}),['2147483647','0','12345']);
 for(const orderNumber of ['0','001','123);BAD','9007199254740992'])assert.throws(()=>compileCancelArguments({rssOrderId:81,orderNumber}));
});
test('every fixed slot and trigger in a 20-argument command is checked rather than trusting its hash',()=>{
 const f=fixture();
 for(let i=0;i<20;i++){
  const c=structuredClone(f.command);c.arguments[i]=i===1?'1':'bad';
  assert.throws(()=>validateTransportCommand(seal(c,'commandSha256')),'argument '+i);
 }
});
test('unsupported function names, hidden extra fields and malformed argument types cannot reach a sink',()=>{
 for(const patch of [{functionName:'RssMarginOpenOrder'},{arguments:['81',0,'12345']},{ignored:'anything'}]){
  const c=seal({...fixture('CANCEL').command,...patch},'commandSha256');assert.throws(()=>validateTransportCommand(c));
 }
 assert.throws(()=>verifyMsiiArguments('RssCancelOrder',['81','0','12345','']));
});
test('compile supports BUY, SELL and CANCEL without inventing live evidence',()=>{
 for(const [kind,side] of [['ORDER','BUY'],['ORDER','SELL'],['CANCEL','BUY'],['CANCEL','SELL']]){
  const f=fixture(kind,side);assert.equal(validateTransportCommand(f.command).kind,kind);
  const input=structuredClone(f.command);delete input.evidenceMode;
  assert.equal(compileTransportCommand(input).evidenceMode,'SYNTHETIC_OFFLINE_ONLY');
 }
});
test('the default DISABLED mode does not request or instantiate a physical sink',async()=>{
 const f=fixture();delete f.config;delete f.permit;
 const r=await dispatchPreparedCommand(f,{now:()=>now});assert.equal(r.status,'NOT_SENT');assert.equal(r.reason,'DISABLED');assert.equal(r.orderTransmission,false);
});
test('OBSERVE_ONLY provides an inert preview and never consumes a permit or calls the sink',async()=>{
 const f=fixture();f.config={mode:'OBSERVE_ONLY',orderTransmission:false};f.permit=null;const sink=mockSink();
 const r=await dispatchPreparedCommand(f,{sink,now:()=>now});assert.equal(r.reason,'OBSERVE_ONLY');assert.equal(sink.calls.length,0);assert.match(r.formulaText,/^=RssStockOrder\(81,0,/);
});
test('a LIVE configuration cannot promote a synthetic source or omit explicit local approval',async()=>{
 for(const patch of [{operatorEnabled:false},{approvedForSession:false},{orderTransmission:false}]){
  const f=fixture();Object.assign(f.config,patch);const sink=mockSink();const r=await dispatchPreparedCommand(f,{sink,now:()=>now});assert.equal(r.status,'NOT_SENT');assert.equal(sink.calls.length,0);
 }
 const f=fixture();f.command=seal({...f.command,evidenceMode:'SYNTHETIC_OFFLINE_ONLY'},'commandSha256');
 assert.throws(()=>validateTransportPacket(f,{now}),/LIVE_SESSION_OR_SOURCE/);
});
test('a permit must be a committed IN_FLIGHT record for every command identity field',()=>{
 const f=fixture();
 for(const key of ['commandId','commandSha256','kind','sessionDate','rssSessionKey','rssOrderId','intentId','targetOrderNumber','state']){
  const p=seal({...f.permit,[key]:key==='rssOrderId'?82:'changed'},'permitSha256');
  assert.throws(()=>validateDispatchPermit(p,f.command,now),key);
 }
 assert.throws(()=>validateDispatchPermit(null,f.command,now));
});
test('100ns future permit, impossible date, stale permit and a stale original command are rejected',()=>{
 const f=fixture();
 for(const begunAtJst of [day+'T09:30:11.0000001+09:00',day+'T09:30:09+09:00','2026-02-30T09:30:10+09:00']){
  assert.throws(()=>validateDispatchPermit(seal({...f.permit,begunAtJst},'permitSha256'),f.command,now));
 }
 assert.throws(()=>validateDispatchPermit(f.permit,f.command,day+'T09:30:20.5000001+09:00'));
 assert.throws(()=>validateDispatchPermit(f.permit,f.command,day+'T09:30:40.0000001+09:00',30000));
 assert.throws(()=>validateDispatchPermit(f.permit,f.command,new Date(NaN)));
});
test('stale permits are rechecked after preparation immediately before the sink call',async()=>{
 const f=fixture(),sink=mockSink();let tick=0;
 const r=await dispatchPreparedCommand(f,{sink,now:()=>tick++===0?now:day+'T09:30:30+09:00'});
 assert.equal(r.status,'NOT_SENT');assert.equal(sink.calls.length,0);
});
test('local fixed workbook, cells, process, session, add-in and expiry are mandatory',()=>{
 for(const patch of [{workbookPath:'\\\\server\\share.xlsx'},{formulaCell:'A1:B9'},{triggerCell:'A1'},
  {formulaCell:'XFE1'},{formulaCell:'A1048577'},{worksheetName:'Sheet/Bad'},{expectedExcelPid:0},
  {expectedExcelHwnd:0},{expectedOpenWorkbooks:[]},{expectedAddInPaths:[]},{expiresAtJst:created},
  {rssSessionKey:'another-session'},{permitMaximumAgeMs:30001},{responseTimeoutMs:10001}]){
  const f=fixture();Object.assign(f.config,patch);assert.throws(()=>validateTransportPacket(f,{now}),JSON.stringify(patch));
 }
});
test('the unsaved C50 workbook needs its exact name, worksheet set and literal ready-receipt identity',()=>{
 const descriptor={name:'Book1',worksheetNames:['ARK_NO11_CUMULATIVE','Q01'],identitySheet:'ARK_NO11_CUMULATIVE',identityCell:'G1',identityValue:'ARK_NO11_C50_TEMP_'+'a'.repeat(32)};
 const f=fixture();assert.deepEqual(validateTransportPacket(f,{now}).config.expectedTemporaryWorkbooks,[]);
 f.config.expectedTemporaryWorkbooks=[descriptor];
 assert.deepEqual(validateTransportPacket(f,{now}).config.expectedTemporaryWorkbooks,[descriptor]);
 for(const patch of [{name:'C:\\Book1'},{name:''},{worksheetNames:['Q01']},
  {worksheetNames:['ARK_NO11_CUMULATIVE','Q01','q01']},{identitySheet:'Other'},
  {identityCell:'G2'},{identityValue:'ARK_NO11_C50_TEMP_wrong'},{extra:'unchecked'}]){
  f.config.expectedTemporaryWorkbooks=[{...descriptor,...patch}];
  assert.throws(()=>validateTransportPacket(f,{now}),JSON.stringify(patch));
 }
 f.config.expectedTemporaryWorkbooks=[descriptor,descriptor];assert.throws(()=>validateTransportPacket(f,{now}));
});
test('the mock one-shot boundary returns a submission observation without ACK, execution, cancellation or cash-release claims',async()=>{
 for(const kind of ['ORDER','CANCEL']){
  const f=fixture(kind),before=structuredClone(f),sink=mockSink();
  const r=await dispatchPreparedCommand(f,{sink,now:()=>now});assert.equal(r.status,'SENT_AWAITING_RECONCILIATION');assert.equal(sink.calls.length,1);
  for(const key of ['brokerTransmissionAttempted','brokerAcknowledged','executionConfirmed','cancellationAcknowledged','cashReserveReleased','orderCanBeResent','productionReady','orderTransmission'])assert.equal(r[key],false,key);
  assert.equal(r.simulatedSink,true);assert.deepEqual(f,before);assert.equal(Object.isFrozen(sink.calls[0].command.arguments),true);
 }
});
test('a lost sink response yields UNKNOWN and is never automatically retried',async()=>{
 let calls=0;const sink={kind:'SYNTHETIC_TEST',async dispatch(){calls++;throw Error('simulated process timeout')}};
 const r=await dispatchPreparedCommand(fixture(),{sink,now:()=>now});assert.equal(r.status,'UNKNOWN');assert.equal(r.dispatchAttempted,true);assert.equal(calls,1);assert.equal(r.orderCanBeResent,false);
});
test('an ACK claim, wrong command identity or inconsistent NOT_SENT reply is treated as UNKNOWN',async()=>{
 for(const reply of [{status:'ACKNOWLEDGED'},{rssOrderId:82},{commandSha256:'c'.repeat(64)},
  {status:'NOT_SENT',dispatchAttempted:true},{status:'SENT_AWAITING_RECONCILIATION',dispatchAttempted:false}]){
  const sink=mockSink(reply);const r=await dispatchPreparedCommand(fixture(),{sink,now:()=>now});assert.equal(r.status,'UNKNOWN');assert.equal(sink.calls.length,1);
 }
});
test('a provably pre-trigger refusal is NOT_SENT and still does not authorize replay or reserve release',async()=>{
 const sink=mockSink({status:'NOT_SENT',dispatchAttempted:false,reason:'GUARD_BLOCKED'});
 const r=await dispatchPreparedCommand(fixture(),{sink,now:()=>now});assert.equal(r.status,'NOT_SENT');assert.equal(r.dispatchAttempted,false);assert.equal(r.orderCanBeResent,false);assert.equal(r.cashReserveReleased,false);
});
test('CLI default path is fully non-transmitting and writes a separate durable result',()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'no11-transport-off-'));
 try{
  const f=fixture();f.config={mode:'DISABLED',orderTransmission:false};delete f.permit;
  const src=path.join(dir,'request.json'),dest=path.join(dir,'result.json');fs.writeFileSync(src,JSON.stringify(f));
  const r=spawnSync(process.execPath,[script,'--request',src,'--result',dest],{encoding:'utf8'});assert.equal(r.status,0,r.stderr+r.stdout);
  const report=JSON.parse(fs.readFileSync(dest,'utf8'));assert.equal(report.status,'NOT_SENT');assert.equal(report.orderTransmission,false);
  const again=spawnSync(process.execPath,[script,'--request',src,'--result',dest],{encoding:'utf8'});assert.equal(again.status,2);assert.equal(JSON.parse(fs.readFileSync(dest,'utf8')).status,'NOT_SENT');
 }finally{fs.rmSync(dir,{recursive:true,force:true})}
});
test('PowerShell staged algorithm uses mocks for prepare, readback, one-shot commit, lost response and restart cases',{skip:process.platform!=='win32'},()=>{
 const r=spawnSync('powershell.exe',['-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',ps,'-OfflineSelfTest'],{encoding:'utf8',timeout:15000});
 assert.equal(r.status,0,r.stdout+r.stderr);const report=JSON.parse(r.stdout.trim());assert.equal(report.status,'PASS_OFFLINE_MOCK_ONLY');assert.equal(report.tests,28);assert.equal(report.excelAttached,false);assert.equal(report.brokerTransmissions,0);
});
test('default PowerShell invocation is disabled before any COM attachment',{skip:process.platform!=='win32'},()=>{
 const r=spawnSync('powershell.exe',['-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',ps],{encoding:'utf8',timeout:15000});
 assert.equal(r.status,0,r.stdout+r.stderr);const report=JSON.parse(r.stdout.trim());assert.equal(report.status,'NOT_SENT');assert.equal(report.reason,'NO11_TRANSPORT_DISABLED');assert.equal(report.dispatchAttempted,false);
});
