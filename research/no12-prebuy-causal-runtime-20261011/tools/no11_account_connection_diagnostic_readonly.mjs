/**
 * Read the existing No11 broker-account observer file without Excel COM.
 * Shows the actual RSS cash-stock buying POWER and read-only order/position
 * connectivity. Does NOT infer cash, initialize an Ark bankroll or send orders.
 */
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {normalizeBrokerObservation} from './no11_broker_snapshot.mjs';

const fail=s=>{throw Error('NO11_ACCOUNT_DIAG_'+s)};
const need=(condition,message)=>{if(!condition)fail(message)};
function load(p){
 need(path.isAbsolute(p),'ABSOLUTE_INPUT_FILE_REQUIRED');
 const s=fs.lstatSync(p);
 need(s.isFile()&&!s.isSymbolicLink()&&s.size>0&&s.size<10_000_000,
   'PRIVATE_ACCOUNT_SOURCE_REQUIRED');
 const v=JSON.parse(fs.readFileSync(p,'utf8').replace(/^\uFEFF/,''));
 need(v.schemaId==='ARK_NO11_ACCOUNT_OBSERVATION_ENVELOPE_V1'&&
   v.status==='OBSERVED'&&v.readOnly===true&&
   v.productionReady===false&&v.orderTransmission===false,
   'ACCOUNT_SOURCE_NOT_OBSERVED_READONLY');
 return v;
}
export function inspect(envelope,session,now){
 need(envelope&&typeof envelope==='object'&&
  /^\d{4}-\d{2}-\d{2}$/.test(session)&&
  typeof now==='string'&&now.slice(0,10)===session,'SESSION_REQUIRED');
 const normalized=normalizeBrokerObservation({
  brokerObservation:envelope.brokerObservation,
  accountSnapshot:envelope.snapshot,
  sessionDate:session,throughJst:now
 });
 need(normalized.accountSnapshotCompared===true&&
  normalized.completeTables===true&&normalized.rowsTruncated===false&&
  normalized.readOnly===true&&normalized.orderTransmission===false,'CROSS_BOOK_VERIFICATION');
 need(typeof normalized.buyingPower==='number'&&
  Number.isSafeInteger(normalized.buyingPower)&&
  normalized.buyingPower>=0,'BROKER_AVAILABLE_AMOUNT_INVALID');
 return Object.freeze({
  status:'RSS_ACCOUNT_AND_ORDER_TABLES_OBSERVED_NOT_CASH_CERTIFIED',
  observationAtJst:normalized.captureCompletedAt,
  rssAvailableForCashStockJpy:String(normalized.buyingPower),
  openCashOrders:normalized.orders.filter(x=>
   !/^(?:約定|取消済|出来ず)/.test(x.status)).length,
  historicalRssOrderIds:normalized.idRows.length,
  brokerPositions:normalized.positions.length,
  accountScope:'BROKER_CASH_STOCK_BUYING_POWER_NOT_DEPOSITED_CASH',
  bankBridgeMayBeIncluded:true,
  accountCashBalanceIdentified:false,
  dynamicalBudgetSource:'BROKER_ACCOUNT_OBSERVATION_ONLY_NO_FIXED_YEN',
  cashAndBankBreakdownNeeded:true,
  originalCapitalV5Modified:false,
  readOnly:true,productionReady:false,orderTransmission:false
 });
}
function jst(){
 return new Date(Date.now()+9*3600000).toISOString().slice(0,23)+'+09:00';
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){
 try{
  const args=process.argv.slice(2);
  need(args.length===2&&args[0]==='--observer-file','USAGE');
  const sample=load(args[1]),now=jst(),date=now.slice(0,10);
  const r=inspect(sample,date,now);
  for(const [k,v] of Object.entries(r)){
   const label=k.replace(/[A-Z]/g,m=>'_'+m).toUpperCase();
   console.log('NO11_ACCOUNT_DIAG_'+label+'='+v);
  }
  console.log('NO11_ACCOUNT_DIAG_INITIAL_ALLOCATED_CASH=NOT_ASSUMED');
  console.log('ORDER_TRANSMISSION=False');
 }catch(error){
  const reason=/^NO11_(?:ACCOUNT_DIAG|BROKER)_[A-Z0-9_]+$/.test(error.message)?
   error.message:'NO11_ACCOUNT_DIAG_UNAVAILABLE_OR_STALE';
  console.log('NO11_ACCOUNT_DIAG=BLOCKED|'+reason);
  console.log('ORDER_TRANSMISSION=False');
  process.exitCode=2;
 }
}
