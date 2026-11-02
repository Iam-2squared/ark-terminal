/** One-time 2026-11-02 selected-share scope; source-only, no LIVE approval.
 *
 * Reuses the 47/47 actual Friday RSS archives. Selects only the 24 names
 * explicitly supplied by the operator and corroborated by the ORIGINAL
 * 2026-09-30 JPX month-end domestic-equity reference. A month-end category is
 * NOT same-day commonEquity/corporate-action/price-basis certification.
 *
 * Creates an immutable DERIVED Chart50 receipt and keeps the original mask,
 * source captures, previous archive, frozen weights and broker permissions.
 * Same-day independent review remains compulsory for EVERY selected symbol
 * before the existing dated-master validator can pass.
 */
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';

const session='2026-11-02', prior='2026-10-30';
const approvedMonthlyBaseline=Object.freeze([
 '3753.T','4478.T','2002.T','8163.T','5273.T','2810.T','1914.T',
 '7678.T','9245.T','2705.T','9900.T','7581.T','4733.T','8070.T',
 '2004.T','4502.T','4565.T','4544.T','7083.T','6532.T','7821.T',
 '219A.T','8923.T','3023.T'
]);
const banned=Object.freeze(['1690.T','2014.T','2038.T','4347.T','5029.T','2612.T']);
const hash=x=>createHash('sha256').update(x).digest('hex');
const fail=x=>{throw Error('NO11_NOV02_24_'+x)};
const need=(v,s)=>{if(!v)fail(s)};
function file(p,size=8000000){
 need(typeof p==='string'&&path.isAbsolute(p),'ABSOLUTE_PATH_REQUIRED');
 const full=path.resolve(p);
 let cur=full;
 while(true){
  if(fs.existsSync(cur))need(!fs.lstatSync(cur).isSymbolicLink(),'SYMLINK_NOT_ALLOWED');
  const parent=path.dirname(cur);
  if(cur===parent)break;
  cur=parent;
 }
 const st=fs.statSync(full);
 need(st.isFile()&&st.size>0&&st.size<=size,'FILE_SIZE_OR_TYPE');
 return full;
}
function read(p,limit){
 const full=file(p,limit),bytes=fs.readFileSync(full);
 return {file:full,value:JSON.parse(bytes.toString('utf8').replace(/^\uFEFF/,'')),bytes};
}
function findOne(dir,prefix){
 need(fs.statSync(dir).isDirectory(),'RUN_DIRECTORY_MISSING');
 const a=fs.readdirSync(dir).filter(s=>s.startsWith(prefix)&&s.endsWith('.json'));
 need(a.length>=1&&a.length<=100,'RUN_RECEIPT_COUNT');
 return a.map(name=>read(path.join(dir,name),8000000));
}
function validateReceiptName(record,prefix){
 const name=path.basename(record.file);
 const m=new RegExp('^'+prefix+'-([a-f0-9]{16})\\.json$').exec(name);
 need(m!==null&&hash(record.bytes).slice(0,16)===m[1],'RECEIPT_DIGEST');
}
function outputFile(run,prefix,obj){
 const bytes=Buffer.from(JSON.stringify(obj)+'\n','utf8');
 const digest=hash(bytes);
 const target=path.join(run,prefix+'-'+digest.slice(0,16)+'.json');
 if(fs.existsSync(target)){
  need(fs.readFileSync(target).equals(bytes),'IMMUTABLE_CONFLICT');
 }else{
  fs.writeFileSync(target,bytes,{flag:'wx',mode:0o600});
 }
 return target;
}
async function stage({engine,run,seed,stageFile,jpxReport}){
 const root=path.resolve(engine),daily=path.resolve(run),priorSeed=path.resolve(seed);
 need(path.isAbsolute(engine)&&path.isAbsolute(run)&&path.isAbsolute(seed),
   'ABSOLUTE_DIRECTORIES_REQUIRED');
 need(fs.statSync(root).isDirectory()&&fs.statSync(daily).isDirectory()&&
   fs.statSync(priorSeed).isDirectory(),'ROOTS_MISSING');
 need(![daily,priorSeed].some(p=>p===root||p.startsWith(root+path.sep)),
   'CAPTURES_MUST_BE_OUTSIDE_ENGINE');
 const mod=await import(pathToFileURL(path.join(root,
   'runtime/no11_rss_chart_50_prescreen.mjs')).href);
 const verified=await import(pathToFileURL(path.join(root,
   'tools/no11_verified_weekly_shadow_scope.mjs')).href);
 const stageRecord=read(stageFile,8000000);
 const name=path.basename(stageRecord.file);
 const token=/^previous-archive-stage-([a-f0-9]{64})\.json$/.exec(name);
 need(token!==null&&hash(stageRecord.bytes)===token[1],'STAGE_IMMUTABLE_DIGEST');
 const previous=stageRecord.value;
 need(previous.schemaId==='ARK_NO11_PREVIOUS_ARCHIVE_STAGE_V1'&&
   previous.sessionDate===session&&previous.previousSession===prior&&
   previous.orderTransmission===false&&previous.productionReady===false&&
   Array.isArray(previous.selectedSymbols)&&previous.selectedSymbols.length===47&&
   typeof previous.symbols==='object'&&
   Object.keys(previous.symbols).length===47&&
   Object.keys(previous.omittedSymbols).length===0,
   'SAVED_47_STAGE_INVALID');
 const originalMatches=findOne(daily,'no11-chart50-private-').filter(r=>
   r.value?.chartPlan?.planSha256===previous.chartPlanSha256);
 need(originalMatches.length===1,'ORIGINAL_CHART47_NOT_UNIQUE');
 const original=originalMatches[0];
 validateReceiptName(original,'no11-chart50-private');
 const masks=findOne(daily,'no11-observed-pass-watch-');
 need(masks.length===1,'ORIGINAL_G1_MASK_NOT_UNIQUE');
 const mask=masks[0];
 validateReceiptName(mask,'no11-observed-pass-watch');
 const originalScope=verified.verifyWeeklyShadowScope({
   runDir:daily,seedDir:priorSeed,maskFile:mask.file,
   chartFile:original.file,sessionDate:session
 });
 need(originalScope.selectedCount===47&&
   JSON.stringify(original.value.chartPlan.selectorInputSymbols)===
   JSON.stringify(previous.selectedSymbols),'ORIGINAL_CHART_AND_STAGE_DISAGREE');
 const jpx=read(jpxReport,8000000);
 const ref=jpx.value;
 need(ref.schemaId==='ARK_NO11_JPX_MONTH_END_EQUITY_REFERENCE_V1'&&
   ref.jpxMonthEndDate==='2026-09-30'&&
   ref.allowTrading===false&&ref.ordinarySharesOnSessionCertified===false&&
   ref.corporateActionsOnSessionCleared===false&&
   Array.isArray(ref.rows),'JPX_REFERENCE_IS_NOT_MONTH_END_ONLY');
 const baseline=new Map(ref.rows.map(x=>[x.symbol,x]));
 need(baseline.size===ref.rows.length,'JPX_REPORT_DUPLICATE_SYMBOLS');
 const oldChart=original.value.chartPlan;
 const selected=oldChart.selectorInputSymbols.filter(s=>
   approvedMonthlyBaseline.includes(s));
 need(approvedMonthlyBaseline.length===24&&
   new Set(approvedMonthlyBaseline).size===24&&
   selected.length===24&&
   approvedMonthlyBaseline.every(s=>selected.includes(s))&&
   selected.every(s=>!banned.includes(s)&&
     baseline.get(s)?.baselineStatus==='DOMESTIC_EQUITY_MONTH_END_REFERENCE'),
   '24_MONTH_END_SOURCE_OR_ORIGINAL_CHART_NOT_MATCHED');
 const allowed=new Set(selected);
 const pinned=new Set(oldChart.protectedChartSymbols);
 const oldScan=new Set(oldChart.scanChartSymbols);
 const narrowedScan=oldChart.scanChartSymbols.filter(s=>allowed.has(s));
 const narrowedCharts=oldChart.allRequestedChartSymbols.filter(s=>
   pinned.has(s)||(oldScan.has(s)&&allowed.has(s)));
 const narrowedSelected=narrowedCharts.filter(s=>allowed.has(s));
 need(narrowedSelected.length===24&&
   JSON.stringify(narrowedSelected)===JSON.stringify(selected)&&
   narrowedCharts.length<=47,'SCOPE_OR_CAPACITY_CHANGED');
 const {planSha256:oldPlanSha,...body}=oldChart;
 const derivedBody={
   ...body,
   scanChartSymbols:narrowedScan,
   allRequestedChartSymbols:narrowedCharts,
   selectorInputSymbols:narrowedSelected,
   g1UnscannedCount:mask.value.observedPassCount-narrowedSelected.length,
   arkChartsUsed:narrowedCharts.length,
   totalChartFunctionsBudgeted:body.occupiedByOtherChartFunctions+narrowedCharts.length,
   provisionalScope:'JPX_2026_09_30_MONTH_END_REFERENCE_ONLY',
   provisionalScopeSymbols:[...selected],
   previousChartPlanSha256:oldPlanSha,
   provisionalJpxReportSha256:hash(jpx.bytes),
   independentSessionReviewStillRequired:true,
   provisionalScopeIsNotTradingApproval:true,
   productionReady:false,
   orderTransmission:false
 };
 const derivedPlan={...derivedBody,planSha256:hash(JSON.stringify(derivedBody))};
 const validated=mod.validateNo11Chart50Plan({
   chartPlan:derivedPlan,mask:mask.value,sessionDate:session
 });
 need(JSON.stringify(validated)===JSON.stringify(selected),'DERIVED_CHART_VALIDATION');
 const newReceipt={
   ...original.value,
   chartPlan:derivedPlan,
   originalChartPlanSha256:oldPlanSha,
   provisionalJpxMonthEndReportSha256:hash(jpx.bytes),
   narrowedToMonthlyReferenceCount:24,
   excludedSourceSelectedCount:23,
   independentSessionReviewStillRequired:true,
   productionReady:false,
   orderTransmission:false
 };
 const target=outputFile(daily,'no11-chart50-private',newReceipt);
 const checked=verified.verifyWeeklyShadowScope({
   runDir:daily,seedDir:priorSeed,maskFile:mask.file,
   chartFile:target,sessionDate:session
 });
 need(checked.selectedCount===24,'DERIVED_WEEKLY_ORIGIN_NOT_VERIFIED');
 return {chart:target,mask:mask.file,selected,originalCount:47,
   selectedCount:24,archiveMemberCount:Object.keys(previous.symbols).length};
}
async function main(args){
 need(args.length===10,'USAGE');
 const keys=['--engine','--run','--seed','--stage','--jpx'], flags={};
 for(let i=0;i<10;i+=2){
  need(keys.includes(args[i])&&!Object.hasOwn(flags,args[i]),'USAGE');
  flags[args[i]]=args[i+1];
 }
 need(keys.every(k=>flags[k]),'USAGE');
 const result=await stage({
  engine:flags['--engine'],run:flags['--run'],seed:flags['--seed'],
  stageFile:flags['--stage'],jpxReport:flags['--jpx']
 });
 console.log('NO11_NOV02_24_SOURCE_CHART47=VERIFIED');
 console.log('NO11_NOV02_24_JPX_MONTH_END=DOMESTIC_EQUITY_BASELINE_ONLY');
 console.log('NO11_NOV02_24_ARCHIVED_SOURCE_COUNT='+result.archiveMemberCount);
 console.log('NO11_NOV02_24_SELECTED='+result.selectedCount);
 console.log('NO11_NOV02_24_CHART='+result.chart);
 console.log('NO11_NOV02_24_MASK='+result.mask);
 console.log('NO11_NOV02_24_INDEPENDENT_REVIEW=REQUIRED_BEFORE_ANY_BUY');
 console.log('NO11_NOV02_24_LIVE_CONFIG=NOT_CREATED');
 console.log('ORDER_TRANSMISSION=False');
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){
 main(process.argv.slice(2)).catch(error=>{
  const msg=String(error?.message||'');
  console.error(/^NO11_NOV02_24_[A-Z0-9_]+$/.test(msg)?msg:
   'NO11_NOV02_24_SOURCE_VALIDATION_OR_IO_FAILURE');
  console.log('ORDER_TRANSMISSION=False');
  process.exitCode=2;
 });
}
export {approvedMonthlyBaseline,stage};
