/**
 * Non-invasive on-disk watcher for the ALREADY RUNNING C50 collector.
 * No Excel COM, no broker, no orders, no model execution, NO new collector.
 * Reuses ORIGINAL strict saved-snapshot diagnostics and original Chart50 plan
 * validator; reports only aggregate counts and first-received times.
 *
 * node <this.mjs> --engine-root <absolute research/no12... path>
 *                 --daily-run <absolute existing private daily G1 run>
 *                 --mask <absolute original G1 mask receipt>
 *                 --plan <absolute original Chart50 receipt>
 *
 * This is NOT a Frozen Selector/P1/H235 or simulated BUY/SELL execution.
 */
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';

const fail=code=>{throw Error('NO11_PARALLEL_CHART_WATCH_'+code)};
const need=(ok,code)=>{if(!ok)fail(code)};
const sha=b=>createHash('sha256').update(b).digest('hex');
function absolute(v,code){
 need(typeof v==='string'&&path.isAbsolute(v),code+'_ABSOLUTE_REQUIRED');
 return path.resolve(v);
}
function rootDirectory(v,code){
 const p=absolute(v,code);
 const st=fs.lstatSync(p);
 need(st.isDirectory()&&!st.isSymbolicLink(),code+'_DIRECTORY_INVALID');
 return p;
}
function fileBytes(v,limit=40_000_000){
 const p=absolute(v,'PRIVATE_FILE');
 const st=fs.lstatSync(p);
 need(st.isFile()&&!st.isSymbolicLink()&&st.size>0&&st.size<=limit,'SOURCE_FILE_INVALID');
 return fs.readFileSync(p);
}
function readJson(v,limit=40_000_000){
 return JSON.parse(fileBytes(v,limit).toString('utf8').replace(/^\uFEFF/,''));
}
function cli(argv){
 const allowed=new Set(['--engine-root','--daily-run','--mask','--plan']);
 need(argv.length===8,'REQUIRED_ARGUMENTS');
 const obj={};
 for(let i=0;i<argv.length;i+=2){
  need(allowed.has(argv[i])&&typeof argv[i+1]==='string'&&!Object.hasOwn(obj,argv[i]),
    'UNKNOWN_OR_DUPLICATE_ARGUMENT');
  obj[argv[i]]=argv[i+1];
 }
 need(allowed.size===Object.keys(obj).length,'REQUIRED_ARGUMENTS');
 return obj;
}
function isSubPath(child,parent){
 return child.startsWith(parent+path.sep)&&child!==parent;
}
function latestCaptureFolder(run,session){
 const candidates=[];
 for(const dir of fs.readdirSync(run,{withFileTypes:true})){
  if(!dir.isDirectory()||!new RegExp('^chart50-shadow-'+session+'-[0-9]{6}-[0-9]+$').test(dir.name))continue;
  const folder=path.join(run,dir.name);
  const entries=fs.readdirSync(folder,{withFileTypes:true});
  const snapshots=entries.filter(x=>x.isFile()&&/^snapshot-[a-f0-9]{64}\.json$/.test(x.name));
  if(snapshots.length<2)continue;
  const stats=snapshots.map(x=>{
   const file=path.join(folder,x.name),stat=fs.lstatSync(file);
   need(stat.isFile()&&!stat.isSymbolicLink(),'SNAPSHOT_SYMLINK_OR_TYPE');
   return {file,name:x.name,mtime:stat.mtimeMs};
  }).sort((a,b)=>b.mtime-a.mtime||b.name.localeCompare(a.name));
  candidates.push({folder,snapshots:stats,latest:stats[0].mtime});
 }
 if(candidates.length===0)return null;
 candidates.sort((a,b)=>b.latest-a.latest);
 return candidates[0];
}
export async function inspect(argv){
 const a=cli(argv);
 const engine=rootDirectory(a['--engine-root'],'ENGINE');
 const run=rootDirectory(a['--daily-run'],'RUN');
 need(!isSubPath(run,engine)&&!isSubPath(engine,run)&&run!==engine,'ENGINE_AND_PRIVATE_OVERLAP');
 const maskPath=absolute(a['--mask'],'MASK'),planPath=absolute(a['--plan'],'PLAN');
 need(isSubPath(maskPath,run)&&isSubPath(planPath,run),'PLAN_AND_MASK_MUST_BE_IN_DAILY_RUN');
 const mask=readJson(maskPath,4_000_000),receipt=readJson(planPath,4_000_000);
 const plan=receipt.chartPlan;
 need(receipt.schemaId==='ARK_NO11_CHART50_PRIVATE_EXPORT_RECEIPT_V1'&&
  plan?.schemaId==='ARK_NO11_G1_PASS_CHART50_SHADOW_CAPACITY_V1'&&
  plan.sessionDate==='2026-10-27'&&plan.productionReady===false&&
  plan.orderTransmission===false&&receipt.productionReady===false&&
  receipt.orderTransmission===false&&mask.orderTransmission===false,
  'ORIGINAL_PLAN_CONTRACT_INVALID');
 const prescreen=await import(pathToFileURL(
  path.join(engine,'runtime/no11_rss_chart_50_prescreen.mjs')));
 const validated=prescreen.validateNo11Chart50Plan({
  chartPlan:plan,mask,sessionDate:'2026-10-27'
 });
 need(Array.isArray(validated)&&validated.length===47,
  'EXPECTED_CHART50_SCOPE_NOT_47');
 const selected=plan.selectorInputSymbols;
 const capture=latestCaptureFolder(run,plan.sessionDate);
 if(capture===null){
  return {status:'WAITING_FOR_TWO_COMPLETE_FRAMES',snapshots:0,
   marketObserved:0,chartRows:0,approximateMinuteVaRows:0,
   latestKnownAtJst:null,excelTouched:false,modelsExecuted:false,
   integratedShadowRunning:false,orderTransmission:false};
 }
 // Latest 3 bounded immutable captures; protect concurrent CreateNew writes.
 const sampleFiles=capture.snapshots.slice(0,Math.min(3,capture.snapshots.length));
 let frames;
 try{
  frames=sampleFiles.map(x=>{
   const bytes=fileBytes(x.file);
   need(sha(bytes)===x.name.slice(9,73),'SNAPSHOT_CONTENT_SHA_CHANGED');
   return JSON.parse(bytes.toString('utf8').replace(/^\uFEFF/,''));
  });
 }catch(e){
  if(['EBUSY','EACCES','EPERM'].includes(e.code)){
   return {status:'SNAPSHOT_CURRENTLY_WRITING_RETRY_LATER',snapshots:capture.snapshots.length,
    marketObserved:0,chartRows:0,approximateMinuteVaRows:0,
    latestKnownAtJst:null,excelTouched:false,modelsExecuted:false,
    integratedShadowRunning:false,orderTransmission:false};
  }
  throw e;
 }
 frames.sort((a,b)=>a.observedEndJst.localeCompare(b.observedEndJst));
 const diagnoser=await import(pathToFileURL(
  path.join(engine,'tools/no11_saved_chart_diagnostics.mjs')));
 const report=diagnoser.diagnoseCaptures(frames);
 need(report.orderTransmission===false&&report.excelAccessed===false&&
   report.sessionDate===plan.sessionDate&&
   report.selectedSymbolsCount===selected.length&&
   frames.every(x=>x.chartPlanSha256===plan.planSha256&&
     JSON.stringify(x.selectedSymbols)===JSON.stringify(selected)),
   'SOURCE_PLAN_OR_READONLY_DIFFERENCE');
 const latest=report.frames.at(-1);
 const ageSeconds=Math.max(0,(Date.now()-Date.parse(latest.captureFinishedAt))/1000);
 return {
  status:ageSeconds>300?'STALE_CAPTURE_NO_LIVE_PROOF':'SAVED_RSS_FRAMES_VERIFIED',
  snapshots:capture.snapshots.length,
  validatedFrames:frames.length,selectedSymbols:report.selectedSymbolsCount,
  marketObserved:latest.chartRows===null?null:frames.at(-1).marketObservations.length,
  chartRows:report.uniqueUnmodifiedClosedChartRows,
  approximateMinuteVaRows:report.approximateMinuteVaRows,
  invalidatedRevisedChartRows:report.invalidatedRevisedChartRows,
  latestChartBarTime:latest.latestChartBarTime,
  latestKnownAtJst:latest.captureFinishedAt,
  addedBarKeys:report.frames.at(-1).addedBarKeys,
  newBarKeysObserved:report.newBarKeysObserved,
  sourceDataImportedNotSelector:report.status,
  exchangeNativeOneMinuteVaCertified:false,
  p1Executed:false,h235Executed:false,capitalExecuted:false,exitExecuted:false,
  integratedShadowRunning:false,excelTouched:false,modelsExecuted:false,
  orderTransmission:false
 };
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){
 try{
  const r=await inspect(process.argv.slice(2));
  console.log('NO11_PARALLEL_CHART_STATUS='+r.status);
  console.log('NO11_PARALLEL_CHART_SNAPSHOTS='+r.snapshots);
  console.log('NO11_PARALLEL_CHART_VERIFIED_FRAMES='+(r.validatedFrames??0));
  console.log('NO11_PARALLEL_CHART_SELECTED='+(r.selectedSymbols??47));
  console.log('NO11_PARALLEL_CHART_MARKET_OBSERVATIONS='+r.marketObserved);
  console.log('NO11_PARALLEL_CHART_CLOSED_ROWS='+r.chartRows);
  console.log('NO11_PARALLEL_CHART_PROXY_VA_ROWS='+r.approximateMinuteVaRows);
  console.log('NO11_PARALLEL_CHART_BAR_KEYS_ADDED='+r.addedBarKeys);
  console.log('NO11_PARALLEL_CHART_LAST_RECEIVED_AT_JST='+r.latestKnownAtJst);
  console.log('NO11_PARALLEL_CHART_NATIVE_VA_CERTIFIED=False');
  console.log('NO11_PARALLEL_CHART_MODE=OBSERVATION_ONLY_NOT_SELECTOR_NOT_BUY_SELL');
  console.log('NO11_PARALLEL_CHART_EXCEL_TOUCHED=False');
  console.log('ORDER_TRANSMISSION=False');
 }catch(e){
  const safe=/^NO11_PARALLEL_CHART_WATCH_[A-Z0-9_]+$/.test(String(e.message));
  console.log('NO11_PARALLEL_CHART=BLOCKED|'+(
    safe?e.message:'NO11_PARALLEL_CHART_WATCH_SOURCE_OR_PRIVATE_IO_FAILURE'));
  console.log('ORDER_TRANSMISSION=False');
  process.exitCode=2;
 }
}
