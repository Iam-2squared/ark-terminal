/**
 * Diagnostic only: identify precisely which observed RssMarket fields fail
 * the current No11 gate. Never promotes this source to a reviewed master.
 * It works on the already-saved immutable private RSS/clipboard receipt;
 * no Excel, broker, historical backfill or order operations.
 */
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {isJpxCashTradingDay} from '../runtime/jpx_cash_calendar_2026_2027.mjs';

const HERE=path.resolve(new URL('../../..',import.meta.url).pathname);
const fail=code=>{throw Error('NO11_REFERENCE_DIAG_'+code)};
const need=(v,code)=>{if(!v)fail(code)};
const positive=v=>typeof v==='number'&&Number.isFinite(v)&&v>0&&v<=1_000_000_000;
const validDay=d=>typeof d==='string'&&/^20\d{2}-\d{2}-\d{2}$/.test(d)&&
  !Number.isNaN(Date.parse(d+'T00:00:00Z'))&&
  new Date(d+'T00:00:00Z').toISOString().slice(0,10)===d;

export function previousCashDay(day){
 need(validDay(day)&&isJpxCashTradingDay(day),'TARGET_NOT_CASH_SESSION');
 const start=Date.parse(day+'T00:00:00Z');
 for(let i=1;i<=14;i++){
  const previous=new Date(start-i*86_400_000).toISOString().slice(0,10);
  if(isJpxCashTradingDay(previous))return previous;
 }
 fail('PREVIOUS_CASH_SESSION_UNAVAILABLE');
}
export function auditReference(raw,session){
 need(raw&&typeof raw==='object'&&validDay(session)&&isJpxCashTradingDay(session),'SESSION');
 need(raw.schemaId==='ARK_NO11_RSS_SESSION_REFERENCE_CAPTURE_V1'&&
   raw.source==='RssMarket_SELECTED_REFERENCE_READONLY'&&
   raw.sessionDate===session&&raw.readOnly===true&&
   raw.corporateActionReviewPerformed===false&&
   raw.orderTransmission===false&&raw.productionReady===false,'UNREVIEWED_SOURCE');
 need(Array.isArray(raw.rows)&&raw.rows.length>=1&&raw.rows.length<=50&&
   Array.isArray(raw.selectedSymbols)&&raw.selectedSymbols.length===raw.rows.length,
   'SYMBOL_SCOPE');
 const seen=new Set();
 for(let i=0;i<raw.rows.length;i++){
  const row=raw.rows[i],symbol=row?.symbol;
  need(typeof symbol==='string'&&/^[0-9A-Z]{4}\.T$/.test(symbol)&&
    symbol===raw.selectedSymbols[i]&&!seen.has(symbol),'SYMBOL_SCOPE_OR_ORDER');
  seen.add(symbol);
 }
 // These timestamps are local receipt times, NOT certified RSS feed times.
 for(const k of ['capturedAtJst','completedAtJst']){
  need(typeof raw[k]==='string'&&raw[k].startsWith(session+'T')&&
    /\+09:00$/.test(raw[k])&&!Number.isNaN(Date.parse(raw[k])),'RECEIPT_CLOCK');
 }
 need(Date.parse(raw.capturedAtJst)<=Date.parse(raw.completedAtJst),
   'RECEIPT_CLOCK_REVERSED');
 const previous=previousCashDay(session),rows=raw.rows;
 const fieldChecks={
  MARKET_CODE_T:r=>r.marketCode==='T',
  MARKET_DATE_CURRENT:r=>r.marketDate===session,
  PREVIOUS_DATE_CASH_SESSION:r=>r.previousDate===previous,
  PREVIOUS_CLOSE_POSITIVE:r=>positive(r.previousClose),
  DAY_BASE_PRICE_POSITIVE:r=>positive(r.dayBasePrice),
  MARKET_SECTION_RECOGNIZED:r=>['東証P','東証S','東証G'].includes(r.marketSection),
  LOT_SHARES_100:r=>typeof r.lotShares==='number'&&r.lotShares===100
 };
 const present=Object.fromEntries(Object.entries(fieldChecks).map(([k,test])=>
   [k,rows.reduce((n,row)=>n+(test(row)?1:0),0)]));
 const complete=rows.filter(row=>Object.values(fieldChecks).every(test=>test(row))).length;
 return Object.freeze({
  status:complete===rows.length?'FIELDS_PRESENT_NOT_EXTERNALLY_REVIEWED':'FIELDS_INCOMPLETE_NOT_AUTHORIZED',
  sessionDate:session,expectedPreviousSession:previous,selectedCount:rows.length,
  completeRows:complete,missingRows:rows.length-complete,present,
  sourceClockCertified:false,independentCorporateReview:false,
  datedMasterCreated:false,shadowPreflightPassed:false,
  readOnly:true,productionReady:false,orderTransmission:false
 });
}
function loadPrivate(filename){
 need(typeof filename==='string'&&path.isAbsolute(filename),'ABSOLUTE_PRIVATE_SOURCE_REQUIRED');
 const absolute=path.resolve(filename),root=path.resolve(new URL('../../..',import.meta.url).pathname);
 need(absolute!==root&&!absolute.startsWith(root+path.sep),'SOURCE_INSIDE_REPOSITORY');
 let dir=absolute;
 do{
  const stat=fs.lstatSync(dir);
  need(!stat.isSymbolicLink(),'SYMLINK_IN_PRIVATE_SOURCE');
  if(dir===absolute)need(stat.isFile()&&stat.size>0&&stat.size<=5_000_000,'SOURCE_SIZE');
  dir=path.dirname(dir);
 }while(dir!==path.dirname(dir));
 const name=path.basename(absolute).match(/^session-reference-([a-f0-9]{64})\.json$/);
 need(!!name,'IMMUTABLE_SOURCE_FILENAME');
 const bytes=fs.readFileSync(absolute);
 need(createHash('sha256').update(bytes).digest('hex')===name[1],'IMMUTABLE_SOURCE_HASH');
 return JSON.parse(bytes.toString('utf8').replace(/^\uFEFF/,''));
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){
 try{
  const a=process.argv.slice(2);
  need(a.length===4&&a[0]==='--reference'&&a[2]==='--session','USAGE');
  const result=auditReference(loadPrivate(a[1]),a[3]);
  console.log('NO11_REFERENCE_DIAG_STATUS='+result.status);
  console.log('NO11_REFERENCE_DIAG_SESSION='+result.sessionDate);
  console.log('NO11_REFERENCE_DIAG_PREVIOUS='+result.expectedPreviousSession);
  console.log('NO11_REFERENCE_DIAG_ROWS_COMPLETE='+result.completeRows+'/'+result.selectedCount);
  for(const [field,count] of Object.entries(result.present)){
   console.log('NO11_REFERENCE_DIAG_'+field+'='+count+'/'+result.selectedCount);
  }
  console.log('NO11_REFERENCE_DIAG_EXTERNAL_REVIEW=NOT_PERFORMED');
  console.log('NO11_REFERENCE_DIAG_DATED_MASTER=NOT_CREATED');
  console.log('NO11_REFERENCE_DIAG_SHADOW_PREFLIGHT=NOT_PASSED');
  console.log('ORDER_TRANSMISSION=False');
 }catch(e){
  const reason=/^NO11_REFERENCE_DIAG_[A-Z0-9_]+$/.test(e?.message)?
   e.message:'NO11_REFERENCE_DIAG_SOURCE_UNAVAILABLE_OR_INVALID';
  console.log('NO11_REFERENCE_DIAG=BLOCKED|'+reason);
  console.log('ORDER_TRANSMISSION=False');
  process.exitCode=2;
 }
}
