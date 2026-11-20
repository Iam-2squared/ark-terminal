/** Normalize observed MSII cash tables. No Excel, order, cash or position mutation.
 * A double read only establishes unchanged observed values, not an atomic broker
 * snapshot or fresh buying power. RSS IDs reset when Excel exits (official help
 * ohm_002_05); their namespace therefore includes the observed Excel session.
 */
import {createHash} from 'node:crypto';
import {orderInstant,validMsiiOrderId,NS_PER_MS} from '../runtime/no11_order_boundary.mjs';
import {observedCashOrder,cashSide} from './no11_broker_order_state.mjs';
import {LOCKED_FLAGS} from '../../../integration/no1-1-msii/runtime/locked_intent.mjs';

export const BROKER_OBSERVATION_SCHEMA='ARK_NO11_BROKER_OBSERVATION_V1';
export const BROKER_SNAPSHOT_SCHEMA='ARK_NO11_BROKER_SNAPSHOT_V1';
export const ORDER_ID_HEADERS=Object.freeze(['発注ID','関数名','発注日','発注時刻','注文番号','発注結果']);
export const ORDER_HEADERS=Object.freeze(['注文番号','受付No','通常注文状況','逆指値注文状況','アルゴ注文状況','銘柄コード','銘柄名称','口座区分','市場名称','信用区分','弁済期限','発注/受注日時','売買','取引','執行条件','注文期限','注文数量','約定数量','注文単価','注文区分','逆指値条件','セット注文','セット注文条件','税区分','注文失効日時','注文失効理由','入力経路','アルゴ注文条件','SOR判定時刻','SOR判定時主市場情報/対象外理由']);
export const EXECUTION_HEADERS=Object.freeze(['約定日','受渡日','銘柄コード','銘柄名称','口座区分','市場名称','信用区分','弁済期限','取引','売買','約定数量','約定単価','約定代金','税区分','特別空売り料(円)']);
export const BROKER_LAYOUT=Object.freeze({sheetName:'ARK_ORDER_IDS_READONLY',idFormula:'=RssOrderIDList(A2:F2)',orderFormula:'=RssOrderList(H2:AK2,0,1)',executionFormula:'=RssExecutionList(AM2:BA2,1)',maximumRows:5000});
const need=(ok,code)=>{if(!ok)throw Error('NO11_BROKER_'+code)};
const hash=s=>createHash('sha256').update(s).digest('hex');
const digest=o=>hash(JSON.stringify(o));
const hex=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x);
const text=(x,code,max=4096)=>{need(typeof x==='string'&&x.length>0&&x.length<=max&&x===x.trim()&&!/[\u0000-\u001f]/.test(x),code);return x};
const integer=(x,min=0)=>Number.isSafeInteger(x)&&x>=min&&x<=1000000000;
const stamp=(x,code)=>orderInstant(x,'NO11_BROKER_'+code,{jstOnly:true});
const symbol=x=>{need(typeof x==='string'&&/^[0-9A-Z]{4}(?:\.T)?$/.test(x),'SYMBOL');return x.endsWith('.T')?x:x+'.T'};
function date(value,code){
 need(typeof value==='string','DATE');
 const m=/^(20\d{2})[-/](\d{1,2})[-/](\d{1,2})$/.exec(value)||/^(20\d{2})(\d{2})(\d{2})$/.exec(value);
 need(m!==null,code);const d=`${m[1]}-${m[2].padStart(2,'0')}-${m[3].padStart(2,'0')}`;
 stamp(d+'T00:00:00+09:00',code);return d;
}
export function normalizeRssDateTime(value){
 need(typeof value==='string','DATETIME');
 const m=/^(20\d{2})[-/](\d{1,2})[-/](\d{1,2})[ T](\d{2}):(\d{2}):(\d{2})(?:\+09:00)?$/.exec(value);
 need(m!==null,'DATETIME');const d=date(`${m[1]}-${m[2]}-${m[3]}`,'DATETIME');
 const s=`${d}T${m[4]}:${m[5]}:${m[6]}+09:00`;stamp(s,'DATETIME');return s;
}
export function brokerExcelSessionKey(value){
 need(value&&integer(value.processId,1)&&typeof value.startedAtUtc==='string'&&value.startedAtUtc.endsWith('Z'),'EXCEL_SESSION');
 orderInstant(value.startedAtUtc,'NO11_BROKER_EXCEL_START');
 need(hex(value.accountWorkbookIdentity)&&hex(value.orderIdWorkbookIdentity),'WORKBOOK_IDENTITY');
 return hash([String(value.processId),value.startedAtUtc,value.accountWorkbookIdentity,value.orderIdWorkbookIdentity].join('\n'));
}
function normalizeId(row,sessionDate,end){
 need(row&&validMsiiOrderId(row.rssOrderId),'RSS_ID');text(row.functionName,'FUNCTION',80);
 need(/^Rss[A-Za-z0-9_]+$/.test(row.functionName),'FUNCTION');
 // IDs persist across trading days until Excel exits; retain old IDs so they
 // cannot accidentally be reused. The order binder separately requires today.
 const day=date(row.orderDate,'ORDER_DATE');need(day<=sessionDate,'ID_SESSION');
 need(typeof row.orderTime==='string'&&/^\d{2}:\d{2}:\d{2}$/.test(row.orderTime),'ORDER_TIME');
 need(stamp(day+'T'+row.orderTime+'+09:00','ORDER_TIME').ns<=end.ns,'ID_FUTURE');
 need(row.orderNumber===null||(typeof row.orderNumber==='string'&&/^[1-9]\d{0,31}$/.test(row.orderNumber)),'ORDER_NUMBER');
 text(row.result,'ID_RESULT');
 return {...row,orderDate:day};
}
function normalizeOrder(row,sessionDate,end){
 observedCashOrder(row);need(/^[1-9]\d{0,31}$/.test(row.orderNumber),'ORDER_NUMBER');text(row.market,'ORDER_MARKET',80);text(row.inputRoute,'INPUT_ROUTE',128);
 const orderReceivedAt=normalizeRssDateTime(row.orderReceivedAt);
 need(orderReceivedAt.slice(0,10)===sessionDate&&stamp(orderReceivedAt,'ORDER_TIME').ns<=end.ns,'ORDER_SESSION');
 text(row.executionCondition,'EXECUTION_CONDITION',80);text(row.orderType,'ORDER_TYPE',80);
 return {...row,orderReceivedAt};
}
function normalizeExecution(row,sessionDate,end){
 symbol(row.symbol);cashSide(row.side);text(row.account,'ACCOUNT',64);text(row.market,'EXECUTION_MARKET',80);
 need(row.trade==='現物','EXECUTION_TRADE');need(integer(row.quantity,1),'EXECUTION_QUANTITY');
 need(typeof row.price==='number'&&Number.isFinite(row.price)&&row.price>0&&/^\d+(?:\.\d{1,6})?$/.test(String(row.price)),'EXECUTION_PRICE');
 const executionDate=normalizeRssDateTime(row.executionDate);
 need(executionDate.slice(0,10)===sessionDate&&stamp(executionDate,'EXECUTION_TIME').ns<=end.ns,'EXECUTION_SESSION');
 return {...row,executionDate};
}
function comparableOrders(rows){return rows.map(r=>[r.orderNumber,symbol(r.symbol),r.account,cashSide(r.side),r.trade,r.executionCondition,r.quantity,r.filledQty,r.status.replaceAll('(','（').replaceAll(')','）')]).sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b)))}
function comparableExecutions(rows){return rows.map(r=>[normalizeRssDateTime(r.executionDate),symbol(r.symbol),r.account,cashSide(r.side),r.trade,r.market,r.quantity,r.price]).sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b)))}
function comparablePositions(rows){return rows.map(r=>[symbol(r.symbol),r.account,r.quantity]).sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b)))}
function verifyPrevious(previous){
 if(previous===null)return;
 need(previous&&previous.schemaId===BROKER_SNAPSHOT_SCHEMA,'PREVIOUS_SCHEMA');
 const {snapshotSha256,...body}=previous;need(hex(snapshotSha256)&&snapshotSha256===digest(body),'PREVIOUS_HASH');
 need(previous.orderTransmission===false&&previous.productionReady===false,'PREVIOUS_UNSAFE');
}
export function normalizeBrokerObservation({brokerObservation:o,sessionDate,throughJst,previous=null,accountSnapshot=null}){
 const now=stamp(throughJst,'NOW');need(now.localDay===sessionDate,'SESSION');
 need(o?.schemaId===BROKER_OBSERVATION_SCHEMA&&o.readOnly===true&&o.productionReady===false&&o.orderTransmission===false,'SOURCE');
 need(o.status==='OBSERVED','SOURCE_UNAVAILABLE');
 const start=stamp(o.capturedAt,'CAPTURE_START'),end=stamp(o.captureCompletedAt,'CAPTURE_END');
 need(start.localDay===sessionDate&&end.localDay===sessionDate&&start.ns<=end.ns&&end.ns<=now.ns&&end.ns-start.ns<25000n*NS_PER_MS&&now.ns-end.ns<=30000n*NS_PER_MS,'CAPTURE_CLOCK');
 need(o.sameSnapshotVerified===true&&o.verificationBasis==='DOUBLE_READ_EQUAL_NOT_ATOMIC_FEED'&&o.actualFeedTimestampCertified===false&&o.buyingPowerFreshnessCertified===false,'SOURCE_VERIFICATION');
 need(o.cashScope==='ALL_CHANNELS_ALL_STATUSES_CASH_ONLY'&&o.completeTables===true&&o.rowsTruncated===false,'TABLE_COMPLETENESS');
 need(o.excelSession?.sessionKey===brokerExcelSessionKey(o.excelSession),'EXCEL_SESSION_KEY');
 need(orderInstant(o.excelSession.startedAtUtc,'NO11_BROKER_EXCEL_START').ns<=start.ns,'EXCEL_START_FUTURE');
 for(const k of ['idRows','orders','executions','positions'])need(Array.isArray(o[k])&&o[k].length<=5000,'ROWS');
 const idRows=o.idRows.map(r=>normalizeId(r,sessionDate,end)),ids=new Set();
 for(const r of idRows){need(!ids.has(r.rssOrderId),'DUPLICATE_RSS_ID');ids.add(r.rssOrderId)}
 const orders=o.orders.map(r=>normalizeOrder(r,sessionDate,end)),numbers=new Set();
 for(const r of orders){need(!numbers.has(r.orderNumber),'DUPLICATE_ORDER');numbers.add(r.orderNumber)}
 const executions=o.executions.map(r=>normalizeExecution(r,sessionDate,end)),positionKeys=new Set();
 const positions=o.positions.map(r=>{const k=JSON.stringify([symbol(r.symbol),text(r.account,'ACCOUNT',64)]);need(integer(r.quantity,1)&&!positionKeys.has(k),'POSITION');positionKeys.add(k);return {...r}});
 need(typeof o.buyingPower==='number'&&Number.isFinite(o.buyingPower)&&o.buyingPower>=0,'BUYING_POWER');
 if(accountSnapshot!==null){
  need(accountSnapshot?.schemaId==='ARK_ACCOUNT_READONLY_SNAPSHOT_V2'&&accountSnapshot.mode==='READ_ONLY'&&accountSnapshot.source==='MARKETSPEED_II_RSS','ACCOUNT_SOURCE');
  need(Object.entries(LOCKED_FLAGS).every(([k,v])=>accountSnapshot.safety?.[k]===v),'ACCOUNT_SAFETY');
  for(const k of ['orders','executions','positions'])need(Array.isArray(accountSnapshot[k]),'ACCOUNT_ROWS');
  need(digest(comparableOrders(accountSnapshot.orders))===digest(comparableOrders(orders))&&digest(comparableExecutions(accountSnapshot.executions))===digest(comparableExecutions(executions))&&digest(comparablePositions(accountSnapshot.positions))===digest(comparablePositions(positions))&&accountSnapshot.buyingPower===o.buyingPower,'ACCOUNT_SNAPSHOT_MISMATCH');
  const a=stamp(accountSnapshot.capturedAt,'ACCOUNT_CAPTURE'),b=stamp(accountSnapshot.captureCompletedAt,'ACCOUNT_CAPTURE');
  need(a.ns>=start.ns&&b.ns>=a.ns&&b.ns<=end.ns,'ACCOUNT_CAPTURE_RANGE');
 }
 verifyPrevious(previous);
 if(previous!==null)need(previous.sessionDate===sessionDate&&stamp(previous.captureCompletedAt,'PREVIOUS_TIME').ns<=end.ns,'PREVIOUS_SESSION_OR_CLOCK');
 if(previous!==null&&stamp(previous.captureCompletedAt,'PREVIOUS_TIME').ns===end.ns){
  need(previous.sourceSha256===digest(o),'SAME_TIME_CHANGED');
  need(previous.accountSnapshotCompared===(accountSnapshot!==null),'SAME_TIME_CONTEXT_CHANGED');
  // A restarted consumer may first reread the same Excel-restart snapshot.
  // Preserve its rebind flag/hash rather than changing it on a duplicate read.
  return Object.freeze({...previous});
 }
 const sessionKey=o.excelSession.sessionKey,rebindRequired=previous!==null&&previous.sessionKey!==sessionKey;
 if(previous!==null&&!rebindRequired){
  for(const old of previous.idRows){
   const row=idRows.find(r=>r.rssOrderId===old.rssOrderId);need(row,'RSS_ID_REMOVED');
   need(['functionName','orderDate','orderTime'].every(k=>row[k]===old[k])&&(old.orderNumber===null||old.orderNumber===row.orderNumber),'RSS_ID_REUSED_OR_CHANGED');
  }
 }
 const unsupportedMarkets=[...new Set([...orders,...executions].map(r=>r.market).filter(m=>!['東証','東証（SOR）','東証(SOR)','JAX','JNX'].includes(m)))].sort();
 const body={schemaId:BROKER_SNAPSHOT_SCHEMA,status:rebindRequired?'OBSERVED_REBIND_REQUIRED':unsupportedMarkets.length?'OBSERVED_UNSUPPORTED_MARKET':'OBSERVED',sessionDate,
  capturedAt:o.capturedAt,captureCompletedAt:o.captureCompletedAt,excelSession:{...o.excelSession},sessionKey,idRows,orders,executions,positions,buyingPower:o.buyingPower,
  sourceSha256:digest(o),sameSnapshotVerified:true,verificationBasis:o.verificationBasis,cashScope:o.cashScope,
  accountComparisonBasis:'CASH_ORDERS_EXECUTIONS_POSITION_QUANTITY_AND_BUYING_POWER',
  completeTables:true,rowsTruncated:false,rebindRequired,unsupportedMarkets,accountSnapshotCompared:accountSnapshot!==null,
  actualFeedTimestampCertified:false,brokerTimestampCertified:false,buyingPowerFreshnessCertified:false,executionPriceAttributed:false,
  realAccountLedgerUpdated:false,readOnly:true,productionReady:false,orderTransmission:false};
 return Object.freeze({...body,snapshotSha256:digest(body)});
}
