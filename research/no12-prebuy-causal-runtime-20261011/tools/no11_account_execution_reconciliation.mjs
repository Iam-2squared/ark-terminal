/** Read-only consistency of current-day RSS orders, executions and positions.
 * RSS ExecutionList has NO order number or unique execution id. Consequently
 * this module never attributes a price to an Ark order, credits spendable cash,
 * or treats buying power as cash. All amounts below are observed GROSS sums.
 * Official output contract: marketspeed.jp/ms2_rss/onlinehelp/ohm_002/ohm_002_07.html
 */
import {digest,LOCKED_FLAGS} from '../../../integration/no1-1-msii/runtime/locked_intent.mjs';
import {observedCashOrder,cashSide} from './no11_broker_order_state.mjs';
const SCHEMA='ARK_NO11_ACCOUNT_EXECUTION_CONSISTENCY_V1';
const need=(ok,code)=>{if(!ok)throw Error('NO11_ACCOUNT_RECON_'+code)};
const own=(obj,key)=>Object.hasOwn(obj,key);
const units=x=>Number.isSafeInteger(x)&&x>=0&&x<=1000000000;
const sym=x=>{need(typeof x==='string'&&/^[0-9A-Z]{4}(?:\.T)?$/.test(x),'SYMBOL');return x.endsWith('.T')?x:x+'.T'};
const account=x=>{need(typeof x==='string'&&x.length>0&&x.length<=64,'ACCOUNT');return x};
const key=(s,a)=>JSON.stringify([s,a]);
function ticks(value){
 need((typeof value==='number'&&Number.isFinite(value))||typeof value==='string','PRICE');
 const text=String(value);need(/^(?:0|[1-9]\d{0,12})(?:\.\d{1,6})?$/.test(text),'PRICE');
 const [a,b='']=text.split('.');const n=BigInt(a)*1000000n+BigInt(b.padEnd(6,'0'));
 need(n>0n,'PRICE');return n;
}
function decimal(n){const sign=n<0n?'-':'';if(n<0n)n=-n;const a=n/1000000n,b=(n%1000000n).toString().padStart(6,'0').replace(/0+$/,'');return sign+a.toString()+(b?'.'+b:'')}
function executionTime(value,session,end){
 if(value===undefined||value===null||value==='')return null;
 need(typeof value==='string','EXECUTION_TIME');
 const m=/^(20\d\d)[\/-](\d{1,2})[\/-](\d{1,2})[ T](\d{2}):(\d{2}):(\d{2})(?:\+09:00)?$/.exec(value);
 need(m!==null,'EXECUTION_TIME');
 const day=m[1]+'-'+m[2].padStart(2,'0')+'-'+m[3].padStart(2,'0');
 need(day===session&&+m[4]<24&&+m[5]<60&&+m[6]<60,'EXECUTION_TIME');
 const stamp=day+'T'+m[4]+':'+m[5]+':'+m[6]+'+09:00',ms=Date.parse(stamp);
 need(Number.isFinite(ms)&&ms<=end,'EXECUTION_TIME');return stamp;
}
function add(obj,k,n){const next=(obj[k]??0)+n;need(Number.isSafeInteger(next)&&Math.abs(next)<=1000000000000,'QUANTITY_SUM');obj[k]=next}
function restore(previous,session){
 if(previous===null)return null;
 need(previous&&previous.schemaId===SCHEMA&&previous.sessionDate===session,'STATE');
 const {stateSha256,...body}=previous;need(stateSha256===digest(body),'STATE_HASH');
 need(body.productionReady===false&&body.orderTransmission===false&&typeof body.baselinePositions==='object'&&
      typeof body.baselineNetExecuted==='object'&&typeof body.seenExecutionRows==='object'&&Array.isArray(body.latchedIssues),'STATE');
 return structuredClone(body);
}
export function reconcileAccountExecutions({snapshot,sessionDate,previous=null}){
 need(snapshot?.schemaId==='ARK_ACCOUNT_READONLY_SNAPSHOT_V2'&&snapshot.source==='MARKETSPEED_II_RSS'&&snapshot.mode==='READ_ONLY'&&
  Object.entries(LOCKED_FLAGS).every(([k,v])=>snapshot.safety?.[k]===v),'READONLY_SNAPSHOT');
 need(typeof sessionDate==='string'&&/^20\d\d-\d\d-\d\d$/.test(sessionDate),'SESSION');
 const end=Date.parse(snapshot.captureCompletedAt);
 need(typeof snapshot.captureCompletedAt==='string'&&snapshot.captureCompletedAt.startsWith(sessionDate+'T')&&Number.isFinite(end),'CAPTURE_TIME');
 for(const k of ['orders','executions','positions'])need(Array.isArray(snapshot[k])&&snapshot[k].length<=5000,'ROWS');
 let state=restore(previous,sessionDate);
 if(state)need(end>=Date.parse(state.lastSourceAt),'SOURCE_CLOCK_REVERSED');
 const groups=new Map(),positions={},net={},multiplicity={},seenIds=new Set(),issues=[];
 let grossBuy=0n,grossSell=0n,missingTimes=0;
 function group(s,a,side){const k=JSON.stringify([s,a,side]);if(!groups.has(k))groups.set(k,{symbol:s,account:a,side,orderFilledQuantity:0,executionQuantity:0,gross:0n,filledOrderCount:0});return groups.get(k)}
 for(const row of snapshot.orders){
  const o=observedCashOrder(row);need(!seenIds.has(row.orderNumber),'DUPLICATE_ORDER');seenIds.add(row.orderNumber);
  need(units(o.quantity)&&units(o.filledQty),'ORDER_QUANTITY');account(o.account);
  const g=group(o.symbol,o.account,o.side);g.orderFilledQuantity+=o.filledQty;need(Number.isSafeInteger(g.orderFilledQuantity),'QUANTITY_SUM');
  if(o.filledQty>0)g.filledOrderCount++;
 }
 for(const row of snapshot.executions){
  const s=sym(row.symbol),a=account(row.account),side=cashSide(row.side),q=row.quantity;
  need(units(q)&&q>0,'EXECUTION_QUANTITY');const p=ticks(row.price),t=executionTime(row.executionDate,sessionDate,end);
  if(t===null)missingTimes++;
  const g=group(s,a,side);g.executionQuantity+=q;need(Number.isSafeInteger(g.executionQuantity),'QUANTITY_SUM');g.gross+=p*BigInt(q);
  add(net,key(s,a),side==='BUY'?q:-q);
  if(side==='BUY')grossBuy+=p*BigInt(q);else grossSell+=p*BigInt(q);
  const fingerprint=digest([s,a,side,t,q,p.toString()]);multiplicity[fingerprint]=(multiplicity[fingerprint]??0)+1;
 }
 for(const row of snapshot.positions){
  const k=key(sym(row.symbol),account(row.account));need(units(row.quantity)&&row.quantity>0&&!own(positions,k),'POSITION');positions[k]=row.quantity;
 }
 if(missingTimes)issues.push('EXECUTION_TIME_UNAVAILABLE');
 const summaries=[...groups.values()].sort((a,b)=>JSON.stringify([a.symbol,a.account,a.side]).localeCompare(JSON.stringify([b.symbol,b.account,b.side]))).map(g=>{
  const quantityMatched=g.orderFilledQuantity===g.executionQuantity;
  if(!quantityMatched)issues.push('ORDER_EXECUTION_QUANTITY_MISMATCH');
  return {symbol:g.symbol,account:g.account,side:g.side,orderFilledQuantity:g.orderFilledQuantity,
   executionQuantity:g.executionQuantity,grossConsiderationJpy:decimal(g.gross),filledOrderCount:g.filledOrderCount,
   quantityMatched,individualOrderPriceAttributed:false};
 });
 if(state===null)state={schemaId:SCHEMA,sessionDate,baselineAt:snapshot.captureCompletedAt,
  baselinePositions:structuredClone(positions),baselineNetExecuted:structuredClone(net),seenExecutionRows:{},latchedIssues:[],
  productionReady:false,orderTransmission:false};
 for(const [fingerprint,count] of Object.entries(state.seenExecutionRows)){
  if((multiplicity[fingerprint]??0)<count)state.latchedIssues.push('EXECUTION_ROWS_REMOVED_OR_REVISED');
 }
 for(const [fingerprint,count] of Object.entries(multiplicity))state.seenExecutionRows[fingerprint]=Math.max(count,state.seenExecutionRows[fingerprint]??0);
 need(Object.keys(state.seenExecutionRows).length<=5000,'EXECUTION_HISTORY_LIMIT');
 const compared=end>Date.parse(state.baselineAt),positionChecks=[];
 if(compared){
  const all=[...new Set([...Object.keys(state.baselinePositions),...Object.keys(positions),...Object.keys(net),...Object.keys(state.baselineNetExecuted)])].sort();
  for(const k of all){
   const expected=(state.baselinePositions[k]??0)+(net[k]??0)-(state.baselineNetExecuted[k]??0),actual=positions[k]??0;
   const matched=expected>=0&&expected===actual;
   if(!matched)issues.push('POSITION_EXECUTION_QUANTITY_MISMATCH');
   const [symbol,account]=JSON.parse(k);positionChecks.push({symbol,account,expectedQuantity:expected,observedQuantity:actual,matched});
  }
 }
 state.latchedIssues=[...new Set(state.latchedIssues)].sort();state.lastSourceAt=snapshot.captureCompletedAt;
 const blockers=[...new Set([...issues,...state.latchedIssues])].sort();
 return {state:{...state,stateSha256:digest(state)},report:{schemaId:'ARK_NO11_ACCOUNT_EXECUTION_CONSISTENCY_REPORT_V1',
  status:blockers.length?'INCOMPLETE_OR_MISMATCH':'OBSERVED_CONSISTENCY_ONLY',blockers,sessionDate,
  groups:summaries,positionConservationCompared:compared,positionChecks,missingExecutionTimes:missingTimes,
  observedGrossBuyConsiderationJpy:decimal(grossBuy),observedGrossSellConsiderationJpy:decimal(grossSell),
  observedGrossCashFlowJpy:decimal(grossSell-grossBuy),individualOrderPriceAttributed:false,
  buyingPowerIsCash:false,feesAndTaxesReconciled:false,spendableCashReconciled:false,
  realAccountLedgerUpdated:false,realFillsAppliedToShadow:false,executionAllowed:false,
  productionReady:false,orderTransmission:false}};
}
