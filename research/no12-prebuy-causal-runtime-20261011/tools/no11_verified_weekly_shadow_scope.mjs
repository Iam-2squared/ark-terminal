/**
 * No11 bridge: validate a previously completed weekly-pool DAILY G1 refresh
 * as input for the ORIGINAL received-data Shadow on that next cash session.
 * Disk read-only. No Excel, model, broker, invented security review or orders.
 * Unlike the nighttime producer, this verifier is usable during market hours.
 */
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {verifyWeeklySource,tradingGap} from './no11_weekly_g1_refresh.mjs';
import {YAHOO_SOURCE} from './no11_yahoo_weekly_seed.mjs';
import {codeIdentity,loadCaptures} from './no11_rss_daily_trend_census.mjs';
import {DAILY_PLAN_SCHEMA,requiredDailySessions,summarizeDailyCaptures}
 from '../runtime/no11_rss_daily_trend_census.mjs';
import {makeObservedPassWatchMask} from '../runtime/no11_observed_pass_watch_gate.mjs';
import {validateNo11Chart50Plan} from '../runtime/no11_rss_chart_50_prescreen.mjs';
import {previousJpxCashTradingDays,isJpxCashTradingDay} from '../runtime/jpx_cash_calendar_2026_2027.mjs';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const sha=b=>createHash('sha256').update(b).digest('hex');
const fail=s=>{throw Error('NO11_WEEKLY_SHADOW_'+s)};
const need=(x,s)=>{if(!x)fail(s)};
function privatePath(p,folder=false){
 need(typeof p==='string'&&path.isAbsolute(p),'ABSOLUTE_SOURCE_REQUIRED');
 const full=path.resolve(p);
 need(full!==ROOT&&!full.startsWith(ROOT+path.sep),'SOURCE_INSIDE_REPO');
 let cursor=full;
 while(true){
  need(!fs.lstatSync(cursor).isSymbolicLink(),'SOURCE_REPARSE_FORBIDDEN');
  const parent=path.dirname(cursor);if(parent===cursor)break;cursor=parent;
 }
 const stat=fs.statSync(full);
 need(folder?stat.isDirectory():stat.isFile(),'SOURCE_TYPE');
 if(!folder)need(stat.size>0&&stat.size<=8_000_000,'SOURCE_BYTES');
 return full;
}
function read(p){
 const full=privatePath(p);
 return {value:JSON.parse(fs.readFileSync(full,'utf8').replace(/^\uFEFF/,'')),
  bytes:fs.readFileSync(full)};
}
function receiptName(file,prefix,bytes){
 const name=path.basename(file);
 const pattern=new RegExp('^'+prefix+'-([a-f0-9]{16})\\.json$');
 const match=name.match(pattern);
 need(match!==null&&sha(bytes).startsWith(match[1]),'RECEIPT_HASH_MISMATCH');
}
export function verifyWeeklyShadowScope({runDir,seedDir,maskFile,chartFile,sessionDate}){
 const run=privatePath(runDir,true),seed=privatePath(seedDir,true);
 const maskPath=privatePath(maskFile),chartPath=privatePath(chartFile);
 need(path.dirname(maskPath)===run&&path.dirname(chartPath)===run&&maskPath!==chartPath,
  'DAILY_RUN_RECEIPT_SCOPE_MISMATCH');
 need(typeof sessionDate==='string'&&isJpxCashTradingDay(sessionDate),'SESSION_NOT_CASH_DAY');
 const asOf=previousJpxCashTradingDays(sessionDate,1)[0];
 const weekly=verifyWeeklySource(seed);
 const plan=read(path.join(run,'plan.json')).value;
 // Friday Yahoo seed can select the same Friday's 429 source symbols, but
 // every returned daily candle in this run MUST still come from the RSS
 // source files below; no Yahoo OHLCV is promoted to real-time execution.
 const fridayConfirmed=plan.yahooFridayRssConfirmation===true;
 const lineageGap=fridayConfirmed?
   (weekly.plan.sourceProvider===YAHOO_SOURCE&&weekly.plan.asOfSession===asOf?0:NaN):
   tradingGap(weekly.plan.asOfSession,asOf);
 const {planId,...body}=plan;
 need(plan.schemaId===DAILY_PLAN_SCHEMA&&
  plan.refreshSchemaId==='ARK_NO11_WEEKLY_G1_DAILY_REFRESH_PLAN_V1'&&
  plan.weeklyG1Policy==='WEEKLY_LOCKED_POOL_DAILY_G1_RECOMPUTATION_V1'&&
  plan.universeScope==='WEEKLY_OBSERVED_PASS_POOL_ONLY'&&
  plan.asOfSession===asOf&&plan.codeSha256===codeIdentity()&&
  sha(JSON.stringify(body))===planId&&
  JSON.stringify(plan.expectedSessions)===JSON.stringify(requiredDailySessions(asOf))&&
  JSON.stringify(plan.symbols)===JSON.stringify(weekly.mask.observedPassSymbols)&&
  plan.weeklySource?.originalPlanId===weekly.plan.planId&&
  plan.weeklySource?.asOfSession===weekly.plan.asOfSession&&
  plan.weeklySource?.observedPassCount===weekly.mask.observedPassCount&&
  plan.weeklySource?.observedPassSymbolsSha256===sha(JSON.stringify(plan.symbols))&&
  plan.weeklySource?.originalFullUniverseCount===4328&&
  plan.weeklySource?.elapsedCashSessions===lineageGap&&
  (fridayConfirmed?
   (weekly.plan.sourceProvider===YAHOO_SOURCE&&
    plan.weeklySource?.sourceWasYahooButDailyCandlesAreRss===true&&
    typeof plan.createdAtJst==='string'&&
    plan.createdAtJst.slice(0,10)===asOf&&
    plan.createdAtJst.slice(11,16)>='19:00'):
   plan.weeklySource?.sourceWasYahooButDailyCandlesAreRss===undefined)&&
  (weekly.plan.sourceProvider===YAHOO_SOURCE?
    (plan.weeklySource?.originProvider===YAHOO_SOURCE&&
     plan.weeklySource?.yahooSourcePriceBasisCertified===false&&
     plan.weeklySource?.requiresIndependentPriceReview===true):
    !Object.hasOwn(plan.weeklySource,'originProvider'))&&
  plan.weeklySource?.elapsedCashSessions===tradingGap(weekly.plan.asOfSession,asOf)&&
  plan.newWeeklyBreakoutsIncluded===false&&plan.unknownNotAdmitted===true&&
  plan.priceBasisCertified===false&&plan.productionReady===false&&plan.orderTransmission===false,
  'DAILY_PLAN_NOT_PINNED_TO_ORIGINAL_WEEKLY_POOL');
 const observed=loadCaptures(run,plan);
 need(observed.length===plan.symbols.length&&
  summarizeDailyCaptures(plan,observed).summary.status==='COMPLETE_OBSERVED_STRUCTURE_ONLY',
  'CURRENT_G1_CAPTURE_INCOMPLETE');
 const refreshed=makeObservedPassWatchMask(plan,observed);
 const mr=read(maskPath),cr=read(chartPath);
 receiptName(maskPath,'no11-observed-pass-watch',mr.bytes);
 receiptName(chartPath,'no11-chart50-private',cr.bytes);
 const mask=mr.value,chart=cr.value;
 need(mask.schemaId===refreshed.schemaId&&mask.asOfSession===asOf&&
  mask.planId===plan.planId&&mask.weeklyOriginalAsOfSession===weekly.plan.asOfSession&&
  mask.weeklyPoolSourcePlanId===weekly.plan.planId&&
  mask.weeklyPoolPopulation===plan.symbols.length&&
  (weekly.plan.sourceProvider===YAHOO_SOURCE?
    (mask.weeklyOriginalProvider===YAHOO_SOURCE&&
     mask.yahooWeeklySourceUnverifiedForTrading===true):
    !Object.hasOwn(mask,'weeklyOriginalProvider'))&&
  mask.newBreakoutsOutsideWeeklyPoolNotScanned===true&&
  mask.strictNoUnknownFallback===true&&mask.shadowOnly===true&&
  mask.priceBasisCertified===false&&mask.corporateActionsCertified===false&&
  mask.productionReady===false&&mask.orderTransmission===false&&
  mask.observedPassCount===refreshed.observedPassCount&&
  JSON.stringify(mask.observedPassSymbols)===JSON.stringify(refreshed.observedPassSymbols),
  'CURRENT_MASK_NOT_DERIVED_FROM_OBSERVED_CAPTURE');
 const sourceNames=fs.readdirSync(path.join(run,'sources')).filter(n=>n.endsWith('.json')).sort();
 need(mask.sourceManifestSha256===sha(JSON.stringify(sourceNames)),'CURRENT_MASK_SOURCE_MANIFEST_CHANGED');
 need(chart.schemaId==='ARK_NO11_CHART50_PRIVATE_EXPORT_RECEIPT_V1'&&
  chart.source==='WEEKLY_POOL_DAILY_REFRESH_ONLY_NOT_CURRENT_FULL_MARKET'&&
  chart.currentRefreshAsOfSession===asOf&&
  chart.weeklyFullAsOfSession===weekly.plan.asOfSession&&
  chart.weeklyCandidateCount===plan.symbols.length&&
  (weekly.plan.sourceProvider===YAHOO_SOURCE?
    chart.weeklyOriginalProvider===YAHOO_SOURCE:
    (chart.weeklyOriginalProvider===undefined||
     chart.weeklyOriginalProvider==='MSII_RSS_ORIGINAL_WEEKLY'))&&
  chart.productionReady===false&&chart.orderTransmission===false,
  'CURRENT_CHART_RECEIPT_WRONG_SOURCE');
 const selected=validateNo11Chart50Plan({chartPlan:chart.chartPlan,mask,sessionDate});
 need(selected.length>=1&&selected.length<=47,'CHART50_SELECTOR_CAPACITY');
 return Object.freeze({status:'CURRENT_COMPLETED_G1_CHART50_VERIFIED_NOT_SECURITY_REVIEW',
  sessionDate,previousSession:asOf,selectedCount:selected.length,
  passCount:mask.observedPassCount,weeklyPopulation:plan.symbols.length,
  weeklyScope:weekly.plan.sourceProvider===YAHOO_SOURCE?
    'YAHOO_WEEKLY_UNOFFICIAL_PLUS_REAL_DAILY_RSS_NOT_PRICE_CERTIFIED':
    'FRIDAY_OR_OCT26_PINNED_PASS_POOL_ONLY',
  precomputedChartReceipt:chartPath,precomputedG1Mask:maskPath,
  dailyRun:run,weeklySourceRun:seed,externalReviewCertified:false,
  fullShadowPreflightPassed:false,readOnly:true,productionReady:false,orderTransmission:false});
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){
 try{
  const args=process.argv.slice(2);
  need(args.length===10,'USAGE');
  const allowed=['--run-dir','--weekly-source-run','--mask','--chart','--session'];
  const flags={};
  for(let i=0;i<10;i+=2){
   need(allowed.includes(args[i])&&!Object.hasOwn(flags,args[i]),'USAGE');
   flags[args[i]]=args[i+1];
  }
  need(allowed.every(x=>flags[x]),'USAGE');
  const result=verifyWeeklyShadowScope({
   runDir:flags['--run-dir'],seedDir:flags['--weekly-source-run'],
   maskFile:flags['--mask'],chartFile:flags['--chart'],sessionDate:flags['--session']});
  console.log('NO11_WEEKLY_SHADOW_SCOPE=PASS_OBSERVED_NOT_EXTERNALLY_REVIEWED');
  console.log('NO11_WEEKLY_SHADOW_DAY='+result.sessionDate);
  console.log('NO11_WEEKLY_SHADOW_G1='+result.passCount);
  console.log('NO11_WEEKLY_SHADOW_SELECTED='+result.selectedCount);
  console.log('NO11_WEEKLY_SHADOW_CHART='+result.precomputedChartReceipt);
  console.log('NO11_WEEKLY_SHADOW_MASK='+result.precomputedG1Mask);
  console.log('NO11_WEEKLY_SHADOW_EXTERNAL_REVIEW=NOT_CERTIFIED');
  console.log('NO11_WEEKLY_SHADOW_FULL_PREFLIGHT=NOT_PASSED');
  console.log('ORDER_TRANSMISSION=False');
 }catch(e){
  console.log('NO11_WEEKLY_SHADOW_SCOPE=BLOCKED|'+
   (/^NO11_(?:WEEKLY_SHADOW|WEEKLY|DAILY|DAYPASS|CHART50)_[A-Z0-9_]+$/.test(e?.message)?
    e.message:'NO11_WEEKLY_SHADOW_PRIVATE_SOURCE_OR_VALIDATION_FAILURE'));
  console.log('ORDER_TRANSMISSION=False');process.exitCode=2;
 }
}
