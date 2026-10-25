/** Existing read-only RSS snapshot -> account observation, never order authority. */
import fs from 'node:fs';
import path from 'node:path';
import {createHash,randomUUID} from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {inspectReadOnlySnapshot} from '../../../integration/no1-1-msii/runtime/account_gate.mjs';
import {cashSide,observedCashOrder} from './no11_broker_order_state.mjs';
export const ENVELOPE='ARK_NO11_ACCOUNT_OBSERVATION_ENVELOPE_V1';
const STATE='ARK_NO11_ACCOUNT_OBSERVATION_STATE_V1';
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const sha=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
const need=(x,c)=>{if(!x)throw Error('NO11_ACCOUNT_'+c)};
const clock=x=>typeof x==='string'&&/^20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,7})?\+09:00$/.test(x)?Date.parse(x):NaN;
const int=(x,min=0)=>Number.isSafeInteger(x)&&x>=min;
function symbol(x){need(typeof x==='string'&&/^[0-9A-Z]{4}(?:\.T)?$/.test(x),'SYMBOL_INVALID');return x.endsWith('.T')?x:x+'.T'}
function restore(previous,session){
 if(previous===null)return {schemaId:STATE,sessionDate:session,sourceAt:null,sourceSha:null,runId:null,sequence:0,orders:{},excludedSymbols:[],latchedBlockers:[],productionReady:false,orderTransmission:false};
 const {stateSha256,...body}=previous;
 need(body.schemaId===STATE&&body.sessionDate===session&&sha(body)===stateSha256&&body.productionReady===false&&body.orderTransmission===false,'STATE_CHANGED');
 return structuredClone(body);
}
export function observe({envelope,sessionDate,throughJst,previous=null}){
 const state=restore(previous,sessionDate),now=clock(throughJst);
 need(Number.isFinite(now)&&throughJst.slice(0,10)===sessionDate,'CLOCK_INVALID');
 need(envelope?.schemaId===ENVELOPE&&envelope.readOnly===true&&envelope.productionReady===false&&envelope.orderTransmission===false,'SOURCE_NOT_READONLY');
 need(envelope.status==='OBSERVED','SOURCE_UNAVAILABLE');
 need(/^[a-f0-9]{32}$/.test(envelope.runId)&&int(envelope.sequence,1),'SOURCE_ID_INVALID');
 const {snapshot,health}=envelope,start=clock(snapshot?.capturedAt),end=clock(snapshot?.captureCompletedAt);
 need(Number.isFinite(start)&&Number.isFinite(end)&&end>=start&&end-start<25000&&end<=now&&now-end<=30000&&snapshot.capturedAt.slice(0,10)===sessionDate&&snapshot.captureCompletedAt.slice(0,10)===sessionDate,'STALE_OR_FUTURE_SOURCE');
 need(health?.actualFeedTimestampCertified===false&&clock(health.healthCapturedAt)>=start&&clock(health.healthCapturedAt)<=end&&['capacity','orders','executions','positions'].every(k=>clock(health.feeds?.[k]?.observedAt)>=start&&clock(health.feeds[k].observedAt)<=end),'STATUS_CLOCK_INVALID');
 const original=inspectReadOnlySnapshot({snapshot,health,now:new Date(now)});
 need(original.status==='RSS_STATUS_OBSERVED_READ_ONLY','ORIGINAL_SOURCE_INSPECTION_BLOCKED');
 need(snapshot.positions.length<=198&&snapshot.orders.length<=298&&snapshot.executions.length<=298,'ROW_LIMIT');
 const sourceSha=sha(envelope);
 if(state.sourceAt!==null){
  need(end>=clock(state.sourceAt),'SOURCE_TIME_REVERSED');
  if(end===clock(state.sourceAt))need(sourceSha===state.sourceSha,'SAME_TIME_CHANGED');
  if(envelope.runId===state.runId){need(envelope.sequence>=state.sequence,'SEQUENCE_REVERSED');if(envelope.sequence===state.sequence)need(sourceSha===state.sourceSha,'SAME_SEQUENCE_CHANGED');}
 }
 const excluded=new Set(state.excludedSymbols),positions=new Set(),orders={},anomalies=[];
 let pending=0,increased=0,disappeared=0;
 for(const p of snapshot.positions){
  const code=symbol(p.symbol);need(int(p.quantity,1)&&typeof p.account==='string'&&p.account.length>0,'POSITION_INVALID');
  const key=code+'|'+p.account;need(!positions.has(key),'DUPLICATE_POSITION');positions.add(key);excluded.add(code);
 }
 for(const r of snapshot.orders){
  need(!Object.hasOwn(orders,r.orderNumber),'ORDER_ID_INVALID');
  const row=observedCashOrder(r);
  if(!row.terminal)pending++;excluded.add(row.symbol);
  const old=state.orders[r.orderNumber];
  if(old){
   // The first observer used short Japanese sides. Normalize only this exact
   // representation during read; all other identity changes remain blocking.
   const oldSide=['BUY','SELL'].includes(old.side)?old.side:cashSide(old.side);
   if(['symbol','account','quantity'].some(k=>old[k]!==row[k])||oldSide!==row.side)anomalies.push('ORDER_IDENTITY_CHANGED');
   if(row.filledQty<old.filledQty)anomalies.push('CUMULATIVE_FILL_REVERSED');
   if(old.terminal&&!row.terminal)anomalies.push('TERMINAL_ORDER_REOPENED');
   if(row.filledQty>old.filledQty)increased++;
  }
  orders[r.orderNumber]=row;
 }
 for(const [id,old] of Object.entries(state.orders))if(!Object.hasOwn(orders,id)){
  if(!old.terminal){anomalies.push('ORDER_DISAPPEARED_UNRESOLVED');disappeared++;}
  orders[id]=old;
 }
 for(const x of snapshot.executions){
  excluded.add(symbol(x.symbol));cashSide(x.side);
  need(int(x.quantity,1)&&typeof x.price==='number'&&Number.isFinite(x.price)&&x.price>0&&typeof x.account==='string'&&x.account.length>0,'EXECUTION_INVALID');
 }
 need(Object.keys(orders).length<=5000,'HISTORY_LIMIT');
 state.latchedBlockers=[...new Set([...state.latchedBlockers,...anomalies])];
 state.excludedSymbols=[...excluded].sort();state.orders=orders;
 Object.assign(state,{sourceAt:snapshot.captureCompletedAt,sourceSha,runId:envelope.runId,sequence:envelope.sequence});
 const blockers=[...state.latchedBlockers,...(pending?['PENDING_OR_UNKNOWN_REAL_ORDER']:[])];
 return {state:{...state,stateSha256:sha(state)},report:{schemaId:'ARK_NO11_ACCOUNT_OBSERVATION_REPORT_V1',sessionDate,
  status:blockers.length?'OBSERVED_ENTRY_BLOCKED':'OBSERVED_READONLY',sourceSha256:sourceSha,sourceAt:state.sourceAt,
  blockers,newShadowEntriesAllowed:blockers.length===0,excludedSymbols:state.excludedSymbols,
  observedBuyingPowerJpy:snapshot.buyingPower,positionRows:snapshot.positions.length,orderRows:snapshot.orders.length,
  executionRows:snapshot.executions.length,pendingOrders:pending,fillIncreasedOrders:increased,disappearedOrders:disappeared,
  actualFeedTimestampCertified:false,realCashUsedForFunding:false,realFillsAppliedToShadow:false,
  arkOrderAttributionAvailable:false,productionReady:false,orderTransmission:false}};
}
function privatePath(value,exists=true){
 need(typeof value==='string'&&path.isAbsolute(value),'PRIVATE_ABSOLUTE_PATH_REQUIRED');const p=path.resolve(value);
 need(p!==ROOT&&!p.startsWith(ROOT+path.sep),'PRIVATE_PATH_IN_REPO');
 for(let c=p;;){if(fs.existsSync(c))need(!fs.lstatSync(c).isSymbolicLink(),'SYMLINK_FORBIDDEN');const parent=path.dirname(c);if(parent===c)break;c=parent;}
 need(fs.statSync(path.dirname(p)).isDirectory(),'PRIVATE_PARENT_REQUIRED');if(exists)need(fs.statSync(p).isFile(),'PRIVATE_FILE_REQUIRED');return p;
}
function read(file,limit){const p=privatePath(file);need(fs.statSync(p).size>0&&fs.statSync(p).size<=limit,'FILE_SIZE');return JSON.parse(fs.readFileSync(p,'utf8').replace(/^\uFEFF/,''));}
function save(file,value){privatePath(file,false);const temp=file+'.'+randomUUID()+'.tmp';const fd=fs.openSync(temp,'wx',0o600);
 try{fs.writeFileSync(fd,JSON.stringify(value));fs.fsyncSync(fd);}finally{fs.closeSync(fd);}
 try{fs.renameSync(temp,file);}finally{if(fs.existsSync(temp))fs.unlinkSync(temp);}
}
export function main(args=process.argv.slice(2)){
 need(args.length===6&&args[0]==='--source'&&args[2]==='--state'&&args[4]==='--session','CLI_ARGUMENTS');
 const source=privatePath(args[1]),dest=privatePath(args[3],false);need(source!==dest,'PATH_COLLISION');
 const throughJst=new Date(Date.now()+32400000).toISOString().replace('Z','+09:00');
 const result=observe({envelope:read(source,5000000),sessionDate:args[5],throughJst,previous:fs.existsSync(dest)?read(dest,2000000):null});
 save(dest,result.state);console.log(JSON.stringify(result.report));
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){try{main();}catch(e){
 console.log(JSON.stringify({schemaId:'ARK_NO11_ACCOUNT_OBSERVATION_REPORT_V1',status:'BLOCKED',blockers:[/^NO11_ACCOUNT_[A-Z0-9_]+$/.test(e.message)?e.message:'NO11_ACCOUNT_SOURCE_UNAVAILABLE'],newShadowEntriesAllowed:false,excludedSymbols:[],productionReady:false,orderTransmission:false}));process.exitCode=2;}}
