/** One-command transport boundary. Defaults to DISABLED and has no retry loop.
 * A ledger must commit IN_FLIGHT before issuing the single-use permit. Hashes
 * detect changes; they are not signatures or trading authorization. LIVE also
 * requires an explicit, session-bound local operator configuration. Tests use
 * an injected mock sink, never Excel. The ordinary read-only launcher does not
 * call this module and none of its existing locks are changed here.
 */
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {digest} from '../../../integration/no1-1-msii/runtime/locked_intent.mjs';
import {orderInstant,currentOrderInstant,validMsiiOrderId,NS_PER_MS} from '../runtime/no11_order_boundary.mjs';
import {compileCashOrderArguments,compileCancelArguments,verifyMsiiArguments,msiiFormulaText,MSII_CASH_ACCOUNTS} from '../runtime/no11_msii_argument_contract.mjs';

export const COMMAND_SCHEMA='ARK_NO11_BROKER_TRANSPORT_COMMAND_V1';
export const PERMIT_SCHEMA='ARK_NO11_BROKER_DISPATCH_PERMIT_V1';
export const CONFIG_SCHEMA='ARK_NO11_MSII_TRANSPORT_CONFIG_V1';
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const PS=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../windows/Invoke-No11MsiiOrder.ps1');
const runFile=promisify(execFile);
const need=(ok,reason)=>{if(!ok)throw Error('NO11_TRANSPORT_'+reason)};
const hash=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x);
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const stamp=(x,code)=>orderInstant(x,'NO11_TRANSPORT_'+code,{jstOnly:true});
function sameKeys(value,keys,reason){need(object(value)&&Object.keys(value).sort().join('|')===[...keys].sort().join('|'),reason)}
function verifyHash(value,field,reason){need(object(value),reason);const {[field]:given,...body}=value;need(hash(given)&&digest(body)===given,reason);return body}
function frozenCopy(value){const out=structuredClone(value);function freeze(x){if(object(x)||Array.isArray(x)){Object.values(x).forEach(freeze);Object.freeze(x)}}freeze(out);return out}
function safeCell(x){if(typeof x!=='string'||!/^\$?[A-Z]{1,3}\$?[1-9]\d{0,6}$/.test(x))return false;const m=x.replaceAll('$','').match(/^([A-Z]+)(\d+)$/);let col=0;for(const c of m[1])col=col*26+c.charCodeAt(0)-64;return col<=16384&&Number(m[2])<=1048576}
const cellKey=x=>x.replaceAll('$','');
const localWindowsPath=x=>typeof x==='string'&&/^[A-Za-z]:[\\/]/.test(x)&&!x.includes('..')&&!/[\r\n\0]/.test(x);
const worksheetName=x=>typeof x==='string'&&x.length>0&&x.length<=31&&!/[\[\]:*?/\\\r\n\0]/.test(x);

export function compileTransportCommand(input){
 need(object(input),'COMMAND_INPUT');
 const {kind}=input;
 need(kind==='ORDER'||kind==='CANCEL','KIND');
 const terms=kind==='ORDER'?input.orderTerms:null;
 if(kind==='ORDER')sameKeys(terms,['orderType','limitPrice','timeInForce','sor','accountType','accountTypeVerified'],'ORDER_TERMS');
 if(kind==='ORDER')need(terms.accountTypeVerified===true&&input.account===MSII_CASH_ACCOUNTS[terms.accountType],'ACCOUNT_NOT_VERIFIED');
 const args=kind==='ORDER'?compileCashOrderArguments({...input,...terms}):compileCancelArguments({rssOrderId:input.rssOrderId,orderNumber:input.targetOrderNumber});
 const core={schemaId:COMMAND_SCHEMA,commandId:input.commandId,kind,sessionDate:input.sessionDate,
  rssSessionKey:input.rssSessionKey,rssOrderId:input.rssOrderId,intentId:input.intentId,
  symbol:input.symbol,side:input.side,quantity:input.quantity,account:input.account,
  targetOrderNumber:kind==='CANCEL'?input.targetOrderNumber:null,createdAtJst:input.createdAtJst,
  evidenceMode:input.evidenceMode??'SYNTHETIC_OFFLINE_ONLY',orderTerms:terms,
  functionName:kind==='ORDER'?'RssStockOrder':'RssCancelOrder',arguments:[...args]};
 const command={...core,commandSha256:digest(core)};
 validateTransportCommand(command);
 return frozenCopy(command);
}

export function validateTransportCommand(command){
 sameKeys(command,['schemaId','commandId','kind','sessionDate','rssSessionKey','rssOrderId','intentId',
  'symbol','side','quantity','account','targetOrderNumber','createdAtJst','evidenceMode','orderTerms','functionName','arguments','commandSha256'],'COMMAND_FIELDS');
 verifyHash(command,'commandSha256','COMMAND_CHANGED');
 need(command.schemaId===COMMAND_SCHEMA&&hash(command.commandId)&&hash(command.intentId),'COMMAND_IDENTITY');
 need(typeof command.rssSessionKey==='string'&&/^[A-Za-z0-9:_-]{1,128}$/.test(command.rssSessionKey)&&validMsiiOrderId(command.rssOrderId),'RSS_SESSION_OR_ID');
 const at=stamp(command.createdAtJst,'COMMAND_CLOCK');need(command.sessionDate===at.localDay,'COMMAND_SESSION');
 need(['SYNTHETIC_OFFLINE_ONLY','LIVE_OBSERVED'].includes(command.evidenceMode),'EVIDENCE_MODE');
 need(typeof command.symbol==='string'&&/^[0-9A-Z]{4}\.T$/.test(command.symbol)&&['BUY','SELL'].includes(command.side),'COMMAND_SIDE_OR_SYMBOL');
 need(Number.isSafeInteger(command.quantity)&&command.quantity>=100&&command.quantity%100===0&&MSII_CASH_ACCOUNTS.includes(command.account),'COMMAND_QUANTITY_OR_ACCOUNT');
 let expected;
 if(command.kind==='ORDER'){
  sameKeys(command.orderTerms,['orderType','limitPrice','timeInForce','sor','accountType','accountTypeVerified'],'ORDER_TERMS');
  need(command.functionName==='RssStockOrder'&&command.targetOrderNumber===null&&command.orderTerms.accountTypeVerified===true&&command.account===MSII_CASH_ACCOUNTS[command.orderTerms.accountType],'ORDER_IDENTITY');
  expected=compileCashOrderArguments({...command,...command.orderTerms});
 }else{
  need(command.kind==='CANCEL'&&command.functionName==='RssCancelOrder'&&command.orderTerms===null,'CANCEL_IDENTITY');
  expected=compileCancelArguments({rssOrderId:command.rssOrderId,orderNumber:command.targetOrderNumber});
 }
 verifyMsiiArguments(command.functionName,command.arguments);
 need(digest(expected)===digest(command.arguments),'ARGUMENTS_CHANGED');
 return frozenCopy(command);
}

export function validateDispatchPermit(permit,command,now=new Date(),maximumAgeMs=10000){
 verifyHash(permit,'permitSha256','PERMIT_CHANGED');
 need(permit.schemaId===PERMIT_SCHEMA&&permit.state==='IN_FLIGHT_COMMITTED','DURABLE_IN_FLIGHT_REQUIRED');
 for(const k of ['commandId','commandSha256','kind','sessionDate','rssSessionKey','rssOrderId','intentId','targetOrderNumber'])need(permit[k]===command[k],'PERMIT_IDENTITY_'+k.toUpperCase());
 const created=stamp(command.createdAtJst,'COMMAND_CLOCK'),prepared=stamp(permit.preparedAtJst,'PREPARED_CLOCK'),begun=stamp(permit.begunAtJst,'DISPATCH_CLOCK'),clock=currentOrderInstant(now,'NO11_TRANSPORT_NOW');
 need(prepared.localDay===command.sessionDate&&begun.localDay===command.sessionDate&&created.ns<=prepared.ns&&prepared.ns<=begun.ns&&begun.ns<=clock.ns,'PERMIT_TIME_ORDER');
 need(Number.isSafeInteger(maximumAgeMs)&&maximumAgeMs>=1&&maximumAgeMs<=30000,'PERMIT_MAX_AGE');
 need(clock.ns-begun.ns<=BigInt(maximumAgeMs)*NS_PER_MS&&clock.ns-created.ns<=30000n*NS_PER_MS,'PERMIT_STALE');
 return frozenCopy(permit);
}

export function validateTransportConfiguration(config,command,now=new Date()){
 const mode=config?.mode??'DISABLED';
 need(['DISABLED','OBSERVE_ONLY','LIVE'].includes(mode),'CONFIG_MODE');
 if(mode!=='LIVE'){
  need(config?.orderTransmission!==true,'DISABLED_CONFIG_CANNOT_TRANSMIT');
  return frozenCopy({...config,mode,orderTransmission:false});
 }
 need(config.schemaId===CONFIG_SCHEMA&&config.orderTransmission===true&&config.operatorEnabled===true&&config.approvedForSession===true,'EXPLICIT_OPERATOR_CONFIGURATION_REQUIRED');
 need(config.sessionDate===command.sessionDate&&config.rssSessionKey===command.rssSessionKey&&command.evidenceMode==='LIVE_OBSERVED','LIVE_SESSION_OR_SOURCE');
 const expires=stamp(config.expiresAtJst,'CONFIG_EXPIRY'),clock=currentOrderInstant(now,'NO11_TRANSPORT_NOW');
 need(expires.localDay===command.sessionDate&&clock.ns<=expires.ns,'CONFIG_EXPIRED');
 need(localWindowsPath(config.workbookPath)&&/\.xlsx$/i.test(config.workbookPath)&&localWindowsPath(config.dispatchDirectory),'LOCAL_PINNED_PATHS');
 need(worksheetName(config.worksheetName),'WORKSHEET_NAME');
 need([config.formulaCell,config.triggerCell,config.guardCell,config.sessionCell].every(safeCell),'CELL_ADDRESS');
 need(new Set([config.formulaCell,config.triggerCell,config.guardCell,config.sessionCell].map(cellKey)).size===4,'CELL_COLLISION');
 need(config.guardValue==='ARK_NO11_SEND_ONCE'&&Number.isSafeInteger(config.expectedExcelPid)&&config.expectedExcelPid>0&&Number.isSafeInteger(config.expectedExcelHwnd)&&config.expectedExcelHwnd>0,'EXCEL_SESSION_PIN');
 const started=currentOrderInstant(config.expectedExcelStartedAt,'NO11_TRANSPORT_EXCEL_START');need(started.ns<=clock.ns,'EXCEL_START_FROM_FUTURE');
 need(Array.isArray(config.expectedAddInPaths)&&config.expectedAddInPaths.length===2&&config.expectedAddInPaths.every(localWindowsPath),'ADDIN_PIN');
 const addons=config.expectedAddInPaths.map(x=>path.win32.basename(x));
 need(addons.filter(x=>/^MarketSpeed2_RSS_(?:32|64)bit\.xll$/i.test(x)).length===1&&addons.filter(x=>/^MarketSpeed2_RSS_VBA\.xlam$/i.test(x)).length===1,'ADDIN_PIN');
 need(Array.isArray(config.expectedOpenWorkbooks)&&config.expectedOpenWorkbooks.length>=1&&config.expectedOpenWorkbooks.length<=8&&config.expectedOpenWorkbooks.every(localWindowsPath),'OPEN_WORKBOOK_PIN');
 const books=config.expectedOpenWorkbooks.map(x=>x.replaceAll('/','\\').toLowerCase());
 need(new Set(books).size===books.length&&books.includes(config.workbookPath.replaceAll('/','\\').toLowerCase()),'WORKBOOK_LIST');
 const temporary=config.expectedTemporaryWorkbooks??[];
 need(Array.isArray(temporary)&&temporary.length<=1,'TEMPORARY_WORKBOOK_LIST');
 for(const descriptor of temporary){
  sameKeys(descriptor,['name','worksheetNames','identitySheet','identityCell','identityValue'],'TEMPORARY_WORKBOOK_FIELDS');
  need(typeof descriptor.name==='string'&&descriptor.name.trim()===descriptor.name&&descriptor.name.length>0&&descriptor.name.length<=128&&!/[\\/:\r\n\0]/.test(descriptor.name),'TEMPORARY_WORKBOOK_NAME');
  need(Array.isArray(descriptor.worksheetNames)&&descriptor.worksheetNames.length>=2&&descriptor.worksheetNames.length<=64&&descriptor.worksheetNames.every(worksheetName),'TEMPORARY_WORKSHEETS');
  const sheets=descriptor.worksheetNames.map(x=>x.toLowerCase());
  need(new Set(sheets).size===sheets.length&&descriptor.worksheetNames.includes('ARK_NO11_CUMULATIVE'),'TEMPORARY_WORKSHEETS');
  need(descriptor.identitySheet==='ARK_NO11_CUMULATIVE'&&descriptor.identityCell==='G1'&&typeof descriptor.identityValue==='string'&&/^ARK_NO11_C50_TEMP_[a-f0-9]{32}$/.test(descriptor.identityValue),'TEMPORARY_WORKBOOK_IDENTITY');
 }
 need(Number.isSafeInteger(config.permitMaximumAgeMs)&&config.permitMaximumAgeMs>=1&&config.permitMaximumAgeMs<=30000,'PERMIT_MAX_AGE');
 need(Number.isSafeInteger(config.responseTimeoutMs)&&config.responseTimeoutMs>=100&&config.responseTimeoutMs<=10000,'RESPONSE_TIMEOUT');
 return frozenCopy({...config,expectedTemporaryWorkbooks:temporary});
}

export function validateTransportPacket(packet,{now=new Date()}={}){
 need(object(packet),'PACKET');
 const command=validateTransportCommand(packet.command);
 const config=validateTransportConfiguration(packet.config,command,now);
 const permit=config.mode==='LIVE'?validateDispatchPermit(packet.permit,command,now,config.permitMaximumAgeMs):null;
 return frozenCopy({command,config,permit});
}
function result(command,status,reason,attempted=false,actual=false){
 return {schemaId:'ARK_NO11_MSII_TRANSPORT_RESULT_V1',commandId:command?.commandId??null,commandSha256:command?.commandSha256??null,
  rssOrderId:command?.rssOrderId??null,kind:command?.kind??null,status,reason,
  dispatchAttempted:attempted,brokerTransmissionAttempted:actual&&attempted,
  brokerAcknowledged:false,executionConfirmed:false,cancellationAcknowledged:false,
  cashReserveReleased:false,orderCanBeResent:false,productionReady:false,orderTransmission:actual&&attempted};
}

/** The injected sink is the single physical boundary; one call, never retry. */
export async function dispatchPreparedCommand(packet,{sink,now=()=>new Date()}={}){
 let checked;
 try{checked=validateTransportPacket(packet,{now:now()})}
 catch(error){return result(packet?.command,'NOT_SENT',String(error.message))}
 const {command,config}=checked;
 if(config.mode!=='LIVE')return {...result(command,'NOT_SENT',config.mode),formulaText:msiiFormulaText(command.functionName,command.arguments)};
 need(sink&&typeof sink.dispatch==='function'&&['MSII_POWERSHELL','SYNTHETIC_TEST'].includes(sink.kind),'SINK_REQUIRED');
 // Recheck immediately before crossing the sink boundary, including elapsed
 // preparation time. The immutable permit was already committed by the ledger.
 try{validateTransportPacket(checked,{now:now()})}catch(error){return result(command,'NOT_SENT',String(error.message))}
 try{
  const response=await sink.dispatch(checked);
  need(object(response)&&response.commandId===command.commandId&&response.commandSha256===command.commandSha256&&response.rssOrderId===command.rssOrderId,'SINK_RESPONSE_IDENTITY');
  need(['NOT_SENT','SENT_AWAITING_RECONCILIATION','UNKNOWN'].includes(response.status)&&typeof response.dispatchAttempted==='boolean','SINK_RESPONSE_STATUS');
  need(response.status!=='NOT_SENT'||response.dispatchAttempted===false,'SINK_FALSE_NOT_SENT');
  need(response.status!=='SENT_AWAITING_RECONCILIATION'||response.dispatchAttempted===true,'SINK_FALSE_SENT');
  const out=result(command,response.status,String(response.reason??''),response.dispatchAttempted,sink.kind==='MSII_POWERSHELL');
  out.simulatedSink=sink.kind==='SYNTHETIC_TEST';
  if(typeof response.statusText==='string')out.statusText=response.statusText.slice(0,512);
  if(typeof response.triggerRestoredToZero==='boolean')out.triggerRestoredToZero=response.triggerRestoredToZero;
  return out;
 }catch(error){
  // A process timeout or lost reply cannot prove whether the trigger changed.
  return {...result(command,'UNKNOWN','SINK_REPLY_UNAVAILABLE',true,sink.kind==='MSII_POWERSHELL'),simulatedSink:sink.kind==='SYNTHETIC_TEST'};
 }
}

function privateFile(value,{exists=true}={}){
 need(typeof value==='string'&&path.isAbsolute(value),'ABSOLUTE_PRIVATE_PATH');
 const p=path.resolve(value);need(p!==ROOT&&!p.startsWith(ROOT+path.sep),'PRIVATE_PATH_IN_REPOSITORY');
 for(let cur=p;;){if(fs.existsSync(cur))need(!fs.lstatSync(cur).isSymbolicLink(),'PRIVATE_SYMLINK');const parent=path.dirname(cur);if(parent===cur)break;cur=parent}
 need(fs.statSync(path.dirname(p)).isDirectory(),'PRIVATE_PARENT');
 if(exists)need(fs.statSync(p).isFile()&&fs.statSync(p).size>0&&fs.statSync(p).size<=262144,'REQUEST_SIZE');
 return p;
}
function readRequest(filename){return JSON.parse(fs.readFileSync(privateFile(filename),'utf8').replace(/^\uFEFF/,''))}
function writeExclusive(filename,value){privateFile(filename,{exists:false});const fd=fs.openSync(filename,'wx',0o600);try{fs.writeFileSync(fd,JSON.stringify(value));fs.fsyncSync(fd)}finally{fs.closeSync(fd)}}

export function powerShellSink(){
 return {kind:'MSII_POWERSHELL',async dispatch(packet){
  need(process.platform==='win32','WINDOWS_REQUIRED');
  const directory=path.resolve(packet.config.dispatchDirectory);
  const packetFile=path.join(directory,packet.command.commandId+'.transport.json');
  // A saved packet is a second process-level duplicate guard. It is never
  // overwritten or removed, including when a reply is lost.
  writeExclusive(packetFile,packet);
  const raw=fs.readFileSync(packetFile);const {createHash}=await import('node:crypto');
  const bytesSha=createHash('sha256').update(raw).digest('hex');
  const {stdout}=await runFile('powershell.exe',['-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',PS,
   '-RequestPath',packetFile,'-ExpectedRequestSha256',bytesSha,'-NodeExecutable',process.execPath],
   {windowsHide:true,timeout:Math.max(15000,packet.config.responseTimeoutMs+12000),maxBuffer:1048576,encoding:'utf8'});
  const lines=stdout.trim().split(/\r?\n/).filter(Boolean);need(lines.length===1,'POWERSHELL_RESULT_FORMAT');return JSON.parse(lines[0]);
 }};
}

let cliDispatchMayHaveOccurred=false;
export async function main(args=process.argv.slice(2)){
 if(args.length===2&&args[0]==='--validate-packet'){
  const checked=validateTransportPacket(readRequest(args[1]));
  process.stdout.write(JSON.stringify({...checked,formulaText:msiiFormulaText(checked.command.functionName,checked.command.arguments)})+'\n');return;
 }
 need(args.length===4&&args[0]==='--request'&&args[2]==='--result','CLI_ARGUMENTS');
 const source=privateFile(args[1]),dest=privateFile(args[3],{exists:false});need(source!==dest&&!fs.existsSync(dest),'RESULT_ALREADY_EXISTS');
 const packet=readRequest(source);
 cliDispatchMayHaveOccurred=packet?.config?.mode==='LIVE';
 const output=await dispatchPreparedCommand(packet,{sink:powerShellSink()});
 writeExclusive(dest,output);process.stdout.write(JSON.stringify(output)+'\n');
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){
 main().catch(error=>{process.stdout.write(JSON.stringify({schemaId:'ARK_NO11_MSII_TRANSPORT_RESULT_V1',status:cliDispatchMayHaveOccurred?'UNKNOWN':'NOT_SENT',reason:String(error.message),dispatchAttempted:cliDispatchMayHaveOccurred,orderCanBeResent:false,orderTransmission:false,productionReady:false})+'\n');process.exitCode=2});
}
