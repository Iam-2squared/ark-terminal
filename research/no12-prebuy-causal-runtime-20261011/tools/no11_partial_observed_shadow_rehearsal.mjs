/**
 * No.1.1 OBSERVED-SOURCE SHADOW REHEARSAL (not a paper BUY/SELL run).
 *
 * Exactly the already-saved immutable real RSS Chart50 snapshots are consumed.
 * The original frozen Selector SHA and ten times are verified, and original
 * RSS minute-Va proxy logic is executed as-of each actual first-received time.
 *
 * NO dated master, third-party corporate action review, account ownership,
 * proven market-time latency, first-entry State9, P1/H235 events, or simulated
 * broker fill is invented or inferred. If no valid frozen time was captured,
 * report it explicitly. The resulting private report is NOT a trading result.
 *
 * No Excel, network, broker API, live orders, workbook writes or model fits.
 */
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';

const SCHEMA='ARK_NO11_2026_OBSERVED_PARTIAL_SHADOW_REHEARSAL_V1';
const NO11='NO11_PARTIAL_SHADOW_';
const requireOk=(v,k)=>{if(!v)throw Error(NO11+k);};
const sha=b=>createHash('sha256').update(b).digest('hex');
const fileRE=/^snapshot-([a-f0-9]{64})\.json$/;
const instant=s=>typeof s==='string'&&
 /^20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{3})?\+09:00$/.test(s)&&
 Number.isFinite(Date.parse(s))?Date.parse(s):null;
function absolute(p,label){
 requireOk(typeof p==='string'&&path.isAbsolute(p),label+'_ABSOLUTE');
 const full=path.resolve(p);
 let cur=full;
 while(true){
   if(fs.existsSync(cur))requireOk(!fs.lstatSync(cur).isSymbolicLink(),label+'_SYMLINK');
   const parent=path.dirname(cur);if(parent===cur)break;cur=parent;
 }
 return full;
}
function directory(p,label){
 const full=absolute(p,label);
 requireOk(fs.statSync(full).isDirectory(),label+'_DIR');
 return full;
}
function loadFile(p,max=32_000_000){
 const full=absolute(p,'SOURCE');
 const stat=fs.statSync(full);
 requireOk(stat.isFile()&&stat.size>0&&stat.size<=max,'SOURCE_FILE');
 const bytes=fs.readFileSync(full);
 return {data:JSON.parse(bytes.toString('utf8').replace(/^\uFEFF/,'')),bytes};
}
function options(args){
 const allowed=new Set(['--engine-root','--daily-run','--plan','--mask',
   '--capture-folder','--output-root']);
 requireOk(args.length===12,'USAGE');
 const o={};
 for(let i=0;i<args.length;i+=2){
   requireOk(allowed.has(args[i])&&!Object.hasOwn(o,args[i])&&args[i+1],
      'ARGUMENT_INVALID');
   o[args[i]]=args[i+1];
 }
 requireOk(Object.keys(o).length===6,'USAGE');
 return o;
}
function within(child,parent){
 const rel=path.relative(parent,child);
 return rel.length>0&&!rel.startsWith('..'+path.sep)&&rel!=='..'&&
   !path.isAbsolute(rel);
}
function snapshotFiles(folder){
 const files=fs.readdirSync(folder).filter(s=>s.startsWith('snapshot-'));
 requireOk(files.length>=2&&files.length<=650,'TWO_TO_650_SNAPSHOTS_REQUIRED');
 let total=0;
 const collected=files.map(name=>{
   const m=fileRE.exec(name);
   requireOk(m!==null,'SNAPSHOT_NAME_INVALID');
   const full=path.join(folder,name);
   const {bytes,data}=loadFile(full,25_000_000);
   requireOk(sha(bytes)===m[1],'SNAPSHOT_BYTES_NOT_IMMUTABLE');
   total+=bytes.length;
   requireOk(total<=250_000_000,'SNAPSHOT_TOTAL_BYTES_LIMIT');
   requireOk(instant(data?.observedEndJst)!==null,'SNAPSHOT_CLOCK_INVALID');
   return {hash:m[1],data};
 });
 collected.sort((a,b)=>a.data.observedEndJst.localeCompare(b.data.observedEndJst));
 for(let i=1;i<collected.length;i++)
   requireOk(collected[i].data.observedEndJst>collected[i-1].data.observedEndJst,
     'DUPLICATE_OR_BACKWARDS_RECEIPT');
 return collected;
}
function saveImmutable(root,body){
 const bytes=Buffer.from(JSON.stringify(body,null,2)+'\n','utf8');
 const dest=path.join(root,'partial-observed-shadow-'+sha(bytes).slice(0,20)+'.json');
 if(fs.existsSync(dest)){
   requireOk(fs.readFileSync(dest).equals(bytes),'EXISTING_RECEIPT_CHANGED');
 }else{
   const fd=fs.openSync(dest,'wx',0o600);
   try{fs.writeSync(fd,bytes);fs.fsyncSync(fd);}
   finally{fs.closeSync(fd);}
 }
 return dest;
}
export async function inspect(args){
 const a=options(args);
 const engine=directory(a['--engine-root'],'ENGINE');
 const run=directory(a['--daily-run'],'RUN');
 const captures=directory(a['--capture-folder'],'CAPTURE');
 const out=absolute(a['--output-root'],'OUTPUT');
 const root=path.resolve(engine,'../../..');
 requireOk(root!==run&&!within(run,root)&&!within(root,run),'PRIVATE_SOURCE_IN_REPO');
 requireOk(within(captures,run),'CAPTURE_MUST_BELONG_TO_DAILY_RUN');
 requireOk(within(absolute(a['--plan'],'PLAN'),run)&&
           within(absolute(a['--mask'],'MASK'),run),
  'MASK_AND_PLAN_MUST_BELONG_TO_DAILY_RUN');
 requireOk(out!==root&&!within(out,root)&&!within(root,out) &&
           out!==run&&!within(run,out),'OUTPUT_PRIVATE_ROOT');
 if(fs.existsSync(out)){
   requireOk(fs.statSync(out).isDirectory(),'OUTPUT_DIRECTORY_INVALID');
 }else fs.mkdirSync(out,{recursive:true});
 directory(out,'OUTPUT');

 const plan=loadFile(a['--plan'],1_000_000).data;
 const mask=loadFile(a['--mask'],1_000_000).data;
 requireOk(plan?.schemaId==='ARK_NO11_CHART50_PRIVATE_EXPORT_RECEIPT_V1'&&
   plan.orderTransmission===false&&plan.productionReady===false &&
   plan.chartPlan?.sessionDate==='2026-10-27'&&
   mask.orderTransmission===false&&mask.productionReady===false,
   'ORIGINAL_SCOPE_RECEIPT_REQUIRED');
 const {validateNo11Chart50Plan}=await import(pathToFileURL(
   path.join(engine,'runtime/no11_rss_chart_50_prescreen.mjs')));
 const {inspectFrozenSelectorAsset}=await import(pathToFileURL(
   path.join(engine,'runtime/no11_frozen_selector_native_shadow.mjs')));
 const {mergeNo11PrivateChartSnapshots}=await import(pathToFileURL(
   path.join(engine,'tools/no11_import_chart50_continuous_snapshot.mjs')));

 const selected=validateNo11Chart50Plan({
   chartPlan:plan.chartPlan,mask,sessionDate:'2026-10-27'
 });
 requireOk(selected.length===47,'CHART50_NOT_EXPECTED_47');
 const frozen=inspectFrozenSelectorAsset();
 requireOk(frozen.originalFrozenWeightsVerified===true &&
   frozen.originalFrozenCodeUsed===true,'FROZEN_SELECTOR_ASSET_REQUIRED');
 const times=frozen.spec.ranking.decisionTimesJst;
 requireOk(Array.isArray(times)&&times.length===10,'TEN_FROZEN_DECISION_TIMES_REQUIRED');

 const source=snapshotFiles(captures);
 const received=source.map(x=>x.data);
 const first=received[0].observedEndJst,last=received.at(-1).observedEndJst;
 const joined=mergeNo11PrivateChartSnapshots({
   sessionDate:'2026-10-27',decisionAtJst:last,
   chartPlanSha256:plan.chartPlan.planSha256,
   selectedSymbols:selected,snapshots:received
 });
 requireOk(joined.receipt.orderTransmission===false&&
  joined.receipt.selectedSymbolsCount===selected.length&&
  joined.receipt.importedSnapshots===received.length,'OBSERVED_SOURCE_JOIN_INVALID');

 // Do not create a late Selector decision: a slot must be observed within 90s
 // of the *original* frozen cutoff. This only checks possible source windows.
 // Actual Selector requires dated master and separately audited prices.
 const windows=[];
 for(const clock of times){
   const cutoff='2026-10-27T'+clock+':00+09:00',edge=Date.parse(cutoff)+90_000;
   const withinWindow=received.filter(x=>
      Date.parse(x.observedEndJst)>=Date.parse(cutoff)&&
      Date.parse(x.observedEndJst)<=edge);
   let status;
   if(instant(last)<Date.parse(cutoff))
      status='NOT_REACHED_BY_SAVED_SOURCE';
   else if(withinWindow.length===0)
      status='MISSED_NO_TIMELY_RECEIPT_NEVER_BACKFILLED';
   else
      status='TIMELY_RECEIPT_SEEN_BUT_DATED_MASTER_NOT_VERIFIED';
   windows.push({originalFrozenCutoffJst:clock,status,
     originalSelectorExecuted:false,orderIntentGenerated:false});
 }
 const sourceReached=windows.filter(x=>
    x.status==='TIMELY_RECEIPT_SEEN_BUT_DATED_MASTER_NOT_VERIFIED').length;
 const report={
   schemaId:SCHEMA,sessionDate:'2026-10-27',
   mode:'OBSERVED_REAL_RSS_SOURCE_REHEARSAL_ONLY_NOT_PAPER_TRADES',
   captureWindow:{firstObservedAtJst:first,lastObservedAtJst:last,
     immutableSnapshots:source.length,sourceFingerprintSha256:sha(
       JSON.stringify(source.map(x=>x.hash)))},
   originalFrozenSelectorAssetChecked:true,
   originalDecisionTimesJst:[...times],decisionWindows:windows,
   decisionWindowsWithReceivedEvidence:sourceReached,
   originalSelectorExecuted:false,
   selectedSymbolsObserved:selected.length,
   originalG1ObservedPassCount:mask.observedPassCount,
   importedRealChartRows:joined.receipt.uniqueUnmodifiedClosedChartRows,
   revisedChartRowsInvalidated:joined.receipt.invalidatedRevisedChartRows,
   approximateVaRows:joined.receipt.approximateMinuteVaRows,
   exactExchangeMinuteVaCertified:false,
   masterValidated:false,externalCorporateActionReviewValidated:false,
   previousContextFullyCertified:false,accountReconciled:false,
   firstEntryState9Executed:false,frozenP1Executed:false,
   frozenH235Executed:false,capitalV5Executed:false,structuralExitExecuted:false,
   actualPaperBuyCount:0,actualPaperSellCount:0,
   simulatedOrderExecutionAuthorized:false,liveBrokerOrdersAuthorized:false,
   allDayEquivalent:false,realMarketPerformanceEvaluated:false,
   sourceTimeNotBackdated:true,missedDecisionsNeverFabricated:true,
   productionReady:false,orderTransmission:false
 };
 const file=saveImmutable(out,report);
 return {file,report};
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){
 try{
   const {file,report:r}=await inspect(process.argv.slice(2));
   console.log('NO11_PARTIAL_SHADOW_SOURCE=HASH_VERIFIED_REAL_RSS');
   console.log('NO11_PARTIAL_SHADOW_SNAPSHOTS='+r.captureWindow.immutableSnapshots);
   console.log('NO11_PARTIAL_SHADOW_CHART50='+r.selectedSymbolsObserved);
   console.log('NO11_PARTIAL_SHADOW_CLOSED_BARS='+r.importedRealChartRows);
   console.log('NO11_PARTIAL_SHADOW_PROXY_VA_ROWS='+r.approximateVaRows);
   console.log('NO11_PARTIAL_SHADOW_FIRST_FROZEN_SELECTOR_TIME='+r.originalDecisionTimesJst[0]);
   console.log('NO11_PARTIAL_SHADOW_TIMELY_FROZEN_WINDOWS='+r.decisionWindowsWithReceivedEvidence);
   console.log('NO11_PARTIAL_SHADOW_ACTUAL_SELECTOR=NOT_EXECUTED_NO_DATED_MASTER');
   console.log('NO11_PARTIAL_SHADOW_PAPER_BUY_SELL=NOT_EXECUTED');
   console.log('NO11_PARTIAL_SHADOW_RECEIPT='+file);
   console.log('NO11_PARTIAL_SHADOW_EXCEL_TOUCHED=False');
   console.log('NO11_PARTIAL_SHADOW_LIVE_ORDERS=False');
   console.log('ORDER_TRANSMISSION=False');
 }catch(e){
   const code=/^NO11_PARTIAL_SHADOW_[A-Z0-9_]+$/.test(String(e.message))?
     e.message:NO11+'UNVERIFIED_OR_PRIVATE_SOURCE_FAILURE';
   console.log('NO11_PARTIAL_SHADOW=BLOCKED|'+code);
   console.log('ORDER_TRANSMISSION=False');
   process.exitCode=2;
 }
}
