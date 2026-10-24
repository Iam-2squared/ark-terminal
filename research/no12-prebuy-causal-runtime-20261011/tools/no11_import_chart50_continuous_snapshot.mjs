/**
 * Strict, private, read-only RSS Chart50 per-minute observation importer.
 * Consumes locally captured immutable snapshots; turns usable RssChart 1M and
 * RssMarket cumulative quotes into *approximate* minute-Va rows.
 * Does not choose 2026 model folds, generate BUY intents, trade or fit.
 */
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {makeNo11RssVaProxyMinuteFeed}
 from '../runtime/no11_rss_vendor_va_shadow_adapter.mjs';

export const CAPTURE_SCHEMA='ARK_NO11_RSS_CHART50_1M_CAPTURE_V1';
const SHA=x=>createHash('sha256')
 .update(typeof x==='string'||Buffer.isBuffer(x)?x:JSON.stringify(x))
 .digest('hex');
const NAME=/^snapshot-([a-f0-9]{64})\.json$/;
const SYM=/^[0-9A-Z]{4}\.T$/;
const DATE=/^20\d{2}-\d{2}-\d{2}$/;
const JST=/^20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?\+09:00$/;
const here=path.dirname(fileURLToPath(import.meta.url));
const repo=path.resolve(here,'../../..');
const blocked=x=>{throw Error('NO11_RSS_CHART50_IMPORT_'+x)};
const check=(v,msg)=>{if(!v)blocked(msg)};
function readFile(filename,max=20_000_000){
 const s=fs.lstatSync(filename);
 check(s.isFile()&&!s.isSymbolicLink()&&s.size>0&&s.size<=max,
  'PRIVATE_FILE_INVALID');
 return fs.readFileSync(filename);
}
function unique(list){
 return Array.isArray(list)&&list.length>0&&list.length<=50&&
   list.every(s=>typeof s==='string'&&SYM.test(s))&&
   new Set(list).size===list.length;
}
function dateTime(s){return typeof s==='string'&&JST.test(s)&&
 Number.isFinite(Date.parse(s))}
function deepEqual(a,b){return JSON.stringify(a)===JSON.stringify(b)}
function checkedCapture(c,scope,previous){
 check(c?.schemaId===CAPTURE_SCHEMA&&c.sessionDate===scope.sessionDate&&
   c.chartPlanSha256===scope.chartPlanSha256&&
   deepEqual(c.selectedSymbols,scope.selectedSymbols)&&
   c.source==='RssChart_1M_AND_RssMarket_CUMULATIVE_READONLY'&&
   c.productionReady===false&&c.orderTransmission===false&&
   c.shadowOnly===true,'CAPTURE_HEADER_INVALID');
 check(dateTime(c.observedEndJst)&&
   c.observedEndJst.startsWith(scope.sessionDate)&&
   (previous===null||c.observedEndJst>previous),'SNAPSHOT_CLOCK_INVALID');
 check(Array.isArray(c.chartRows)&&Array.isArray(c.marketObservations)&&
   c.chartRows.length<=scope.selectedSymbols.length*1000&&
   c.marketObservations.length===scope.selectedSymbols.length,
   'CAPTURE_ROWS_INVALID');
 return c.observedEndJst;
}
export function mergeNo11PrivateChartSnapshots({
  sessionDate,decisionAtJst,chartPlanSha256,selectedSymbols,snapshots
}={}){
 check(DATE.test(sessionDate)&&dateTime(decisionAtJst)&&
   decisionAtJst.slice(0,10)===sessionDate,'SESSION_CLOCK_INVALID');
 check(typeof chartPlanSha256==='string'&&/^[a-f0-9]{64}$/.test(chartPlanSha256)&&
   unique(selectedSymbols),'PLAN_OR_CHART_SYMBOLS_INVALID');
 check(Array.isArray(snapshots)&&snapshots.length>=2&&snapshots.length<=650,
   'SNAPSHOT_COUNT_INVALID');
 const scope={sessionDate,chartPlanSha256,selectedSymbols};
 const present=new Set(selectedSymbols),markets=[],charts=new Map();
 let prev=null,rawChart=0,duplicateChartRows=0,validSamples=0;
 for(const c of snapshots){
  prev=checkedCapture(c,scope,prev);
  // Market first-seen RECEIPT: bulk read END timestamp only. It is not the
  // venue field timestamp, and must never be backdated to the Excel cell time.
  check(dateTime(c.marketObservedAtJst)&&
    c.marketObservedAtJst<=c.observedEndJst&&
    c.marketObservedAtJst.startsWith(scope.sessionDate),
    'MARKET_RECEIPT_CLOCK_INVALID');
  const seenMarkets=new Set();
  for(const r of c.marketObservations){
   check(r&&present.has(r.symbol)&&!seenMarkets.has(r.symbol)&&
     (r.marketDate===sessionDate||r.marketDate===null),
     'MARKET_ROW_IDENTITY_INVALID');
   seenMarkets.add(r.symbol);
   markets.push({...r,observedEndJst:c.marketObservedAtJst});
   validSamples++;
  }
  const seenChartInCapture=new Set();
  for(const r of c.chartRows){
   check(r&&present.has(r.Code)&&r.Date===sessionDate&&
      typeof r.Time==='string'&&/^\d{2}:\d{2}$/.test(r.Time)&&
      dateTime(r.knownAtJst)&&r.knownAtJst<=c.observedEndJst,
     'CHART_ROW_IDENTITY_OR_CAUSALITY_INVALID');
   const k=r.Code+'|'+r.Time;
   check(!seenChartInCapture.has(k),'DUPLICATE_SAME_SNAPSHOT_CHART');
   seenChartInCapture.add(k);
   rawChart++;
   if(charts.has(k)){
    const original=charts.get(k);
    // Later RssChart snapshots can revise incomplete 1M bars. Use only
    // first observed, already closed and stable row. Conflicting revisions
    // are dropped; never overwrite earlier values with future information.
    const fields=['O','H','L','C','Vo'];
    if(original!==null&&fields.some(x=>original[x]!==r[x])){
      charts.set(k,null);
    } else duplicateChartRows++;
   }else if(!charts.has(k)){
    charts.set(k,{...r});
   }
  }
 }
 const chartRows=[...charts.values()].filter(Boolean);
 const joined=makeNo11RssVaProxyMinuteFeed({
   sessionDate,decisionAtJst,selectedSymbols,
   chartRows,marketObservations:markets
 });
 const receipt={
   schemaId:'ARK_NO11_RSS_CHART50_OFFLINE_JOIN_V1',
   sessionDate,decisionAtJst,chartPlanSha256,
   importedSnapshots:snapshots.length,
   marketRowsImported:validSamples,
   chartRowsObserved:rawChart,
   uniqueUnmodifiedClosedChartRows:chartRows.length,
   duplicateRepeatedChartRows:duplicateChartRows,
   invalidatedRevisedChartRows:[...charts.values()].filter(v=>v===null).length,
   approximateMinuteVaRows:joined.rows.length,
   selectedSymbolsCount:selectedSymbols.length,
   skippedBars:joined.receipt.skippedBarsByReason,
   nativeSelectorExecuted:false,
   frozenSelectorOriginalExactVaReplaced:true,
   readOnly:true,shadowOnly:true,
   productionReady:false,orderTransmission:false,
   sourceSnapshotsSha256:SHA(snapshots),
   proxyReceipt:joined.receipt
 };
 return Object.freeze({receipt,rows:joined.rows});
}
function safePrivateJson(filepath,max){
 const b=readFile(filepath,max);
 return JSON.parse(b.toString('utf8').replace(/^\uFEFF/,''));
}
export function runNo11ChartSnapshotImport(args){
 check(args.length===6&&args[0]==='--folder'&&args[2]==='--plan'&&
   args[4]==='--decision','ARGUMENTS');
 const planFile=args[3],decisionAtJst=args[5];
 const folder=path.resolve(args[1]),stat=fs.lstatSync(folder);
 check(path.isAbsolute(args[1])&&
   stat.isDirectory()&&!stat.isSymbolicLink()&&
   !folder.startsWith(repo+path.sep)&&folder!==repo,
   'PRIVATE_FOLDER_REQUIRED');
 const source=safePrivateJson(planFile,250_000);
 const p=source.chartPlan;
 check(source.schemaId==='ARK_NO11_CHART50_PRIVATE_EXPORT_RECEIPT_V1'&&
   p?.schemaId==='ARK_NO11_G1_PASS_CHART50_SHADOW_CAPACITY_V1'&&
   p.orderTransmission===false&&p.productionReady===false&&
   typeof p.planSha256==='string'&&
   p.planSha256===SHA(Object.fromEntries(
    Object.entries(p).filter(([k])=>k!=='planSha256'))),
   'PRIVATE_CHART_PLAN_INVALID');
 const selected=p.selectorInputSymbols;
 check(unique(selected),'SELECTOR_CHART_SYMBOLS_INVALID');
 const candidates=fs.readdirSync(folder).filter(name=>name.startsWith('snapshot-'));
 check(candidates.length>=2&&candidates.length<=650,'CAPTURE_FILE_COUNT_INVALID');
 const snapshots=[];
 for(const name of candidates){
   const m=NAME.exec(name);
   check(m!==null,'SNAPSHOT_NAME_INVALID');
   const bytes=readFile(path.join(folder,name));
   check(SHA(bytes)===m[1],'SNAPSHOT_HASH_MISMATCH');
   snapshots.push(JSON.parse(bytes.toString('utf8').replace(/^\uFEFF/,'')));
 }
 snapshots.sort((a,b)=>a.observedEndJst.localeCompare(b.observedEndJst));
 const {receipt,rows}=mergeNo11PrivateChartSnapshots({
   sessionDate:p.sessionDate,
   decisionAtJst,chartPlanSha256:p.planSha256,
   selectedSymbols:selected,
   snapshots
 });
 const payload=Buffer.from(JSON.stringify({receipt,rows})+'\n');
 const out=path.join(folder,'private-approx-va-'+SHA(payload).slice(0,16)+'.json');
 try{fs.writeFileSync(out,payload,{flag:'wx'});}
 catch(e){
  if(e.code!=='EEXIST'||!fs.readFileSync(out).equals(payload))throw e;
 }
 console.log('NO11_CHART50_SNAPSHOTS='+receipt.importedSnapshots);
 console.log('NO11_CHART50_APPROX_VA_ROWS='+receipt.approximateMinuteVaRows);
 console.log('NO11_CHART50_APPROX_VA_IMPORT='+out);
 console.log('NO11_CHART50_SELECTOR_ACTUAL_EXCHANGE_VA_CERTIFIED=False');
 console.log('NO11_PRODUCTION_READY=False');
 console.log('ORDER_TRANSMISSION=False');
 return {receipt,rows,out};
}
if(process.argv[1]&&
  import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){
 try{runNo11ChartSnapshotImport(process.argv.slice(2));}
 catch(e){
  console.error(/^NO11_RSS_CHART50_IMPORT_/.test(e.message)?
    e.message:'NO11_RSS_CHART50_PRIVATE_IO_ERROR');
  process.exitCode=2;
 }
}
