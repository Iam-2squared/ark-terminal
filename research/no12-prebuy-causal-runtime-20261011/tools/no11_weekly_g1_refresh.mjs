/**
 * WEEKLY FULL MARKET G1 + DAILY LIMITED POOL REFRESH.
 * Source scan: a complete, cryptographically pinned original full-universe
 * daily RSS run (Friday after 18:00 JST; the 2026-10-26 observed scan can be
 * used once as the initial Monday seed). Only its observed PASS universe is
 * reread on subsequent cash sessions. Unscanned new breakouts are intentionally
 * unavailable until the next full-market weekly scan.
 *
 * This adapter NEVER relabels old prices as a new trading day's observation.
 * Every daily mask is generated from fresh, genuinely received D/100 history
 * for all members of the weekly PASS pool, and retains explicit weekly lineage.
 * Does not open Excel, place orders, train/modify models or certify price basis.
 */
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {codeIdentity,loadCaptures,immutable} from './no11_rss_daily_trend_census.mjs';
import {DAILY_PLAN_SCHEMA,ORIGINAL_SYMBOLS_SHA256,lastCompletedSession,jstNow,requiredDailySessions,
  summarizeDailyCaptures} from '../runtime/no11_rss_daily_trend_census.mjs';
import {isJpxCashTradingDay} from '../runtime/jpx_cash_calendar_2026_2027.mjs';
import {verifyYahooWeeklySeed,YAHOO_SEED_SCHEMA,YAHOO_SOURCE} from './no11_yahoo_weekly_seed.mjs';
import {makeObservedPassWatchMask}
  from '../runtime/no11_observed_pass_watch_gate.mjs';
import {rankVerifiedG1PassForChartBudget,makeNo11G1Chart50Plan}
  from '../runtime/no11_rss_chart_50_prescreen.mjs';

const HERE=path.dirname(fileURLToPath(import.meta.url));
const ROOT=path.resolve(HERE,'../../..');
const SHA=x=>createHash('sha256').update(x).digest('hex');
const fail=s=>{throw Error('NO11_WEEKLY_'+s)};
const need=(x,s)=>{if(!x)fail(s)};
const initialSeed='2026-10-26'; // a single already-observed Monday warm start
const dailySchema='ARK_NO11_WEEKLY_G1_DAILY_REFRESH_PLAN_V1';
const contract='WEEKLY_LOCKED_POOL_DAILY_G1_RECOMPUTATION_V1';

function regular(p,limit=8_000_000){
  need(path.isAbsolute(p),'ABSOLUTE_PATH_REQUIRED');
  const full=path.resolve(p);
  need(full!==ROOT&&!full.startsWith(ROOT+path.sep),'PRIVATE_PATH_REQUIRED');
  const stat=fs.lstatSync(full);
  need(stat.isFile()&&!stat.isSymbolicLink()&&stat.size>0&&stat.size<=limit,'PRIVATE_FILE_INVALID');
  return JSON.parse(fs.readFileSync(full,'utf8').replace(/^\uFEFF/,''));
}
function directory(p,create=false){
  need(typeof p==='string'&&path.isAbsolute(p),'PRIVATE_DIRECTORY_REQUIRED');
  const x=path.resolve(p);
  need(x!==ROOT&&!x.startsWith(ROOT+path.sep),'OUTSIDE_REPOSITORY_REQUIRED');
  if(create)fs.mkdirSync(x,{recursive:true});
  const stat=fs.lstatSync(x);
  need(stat.isDirectory()&&!stat.isSymbolicLink(),'UNSAFE_DIRECTORY');
  return x;
}
export function isoFriday(d){return new Date(d+'T00:00:00Z').getUTCDay()===5}
function advanceDay(d){return new Date(Date.parse(d+'T00:00:00Z')+86_400_000).toISOString().slice(0,10)}
export function tradingGap(anchor,asOf){
  need(isJpxCashTradingDay(anchor)&&isJpxCashTradingDay(asOf)&&anchor<asOf,'TRADING_DATES_INVALID');
  let count=0;
  for(let d=advanceDay(anchor);d<=asOf;d=advanceDay(d))
    if(isJpxCashTradingDay(d))count++;
  return count;
}
export function verifyWeeklyPool(weeklyRun){
  const run=directory(weeklyRun);
  const plan=regular(path.join(run,'plan.json'),4_000_000);
  const {planId,...body}=plan;
  need(plan.schemaId===DAILY_PLAN_SCHEMA&&
    SHA(JSON.stringify(body))===planId&&plan.codeSha256===codeIdentity()&&
    plan.sourceSymbolsSha256===ORIGINAL_SYMBOLS_SHA256&&
    Array.isArray(plan.symbols)&&plan.symbols.length===4328,
    'FULL_RUN_CODE_OR_PLAN_PIN_INVALID');
  need(isoFriday(plan.asOfSession)||plan.asOfSession===initialSeed,
    'SOURCE_MUST_BE_FRIDAY_OR_INITIAL_SEED');
  const captures=loadCaptures(run,plan);
  need(captures.length===plan.symbols.length,'FULL_WEEKLY_SWEEP_NOT_COMPLETE');
  const mask=makeObservedPassWatchMask(plan,captures);
  need(mask.observedPassCount>0&&mask.observedPassCount<=500,
    'WEEKLY_PASS_POPULATION_OUTSIDE_RSS_CAP');
  return {run,plan,mask};
}
/** Explicit provider seam: original RSS weekly seed OR verified Yahoo source.
 * The subsequent daily D100 candidate refresh remains physical RSS.
 * Do not relabel Yahoo daily prices as RSS captures.
 */
export function verifyWeeklySource(weeklyRun){
  const run=directory(weeklyRun);
  const plan=regular(path.join(run,'plan.json'));
  if(plan.schemaId===YAHOO_SEED_SCHEMA)return verifyYahooWeeklySeed(run);
  need(plan.schemaId===DAILY_PLAN_SCHEMA,'UNKNOWN_WEEKLY_SOURCE_PROVIDER');
  return verifyWeeklyPool(run);
}
export function nightlyWindow(now){
  const local=now.slice(0,10),clock=now.slice(11,16);
  const date=lastCompletedSession(now);
  const sameEvening=isJpxCashTradingDay(local)&&date===local&&clock>='18:00';
  const followingPreopen=nextCashDate(date)===local&&clock<'08:30'&&!isoFriday(date);
  need(sameEvening||followingPreopen,'CURRENT_COMPLETED_CASH_SESSION_REQUIRED');
  return {date,now,followingPreopen};
}
/**
 * Deliberate RECOVERY after the 08:30 preopen deadline. The as-of day stays
 * the REAL completed previous cash day; receipt/plan creation uses current JST.
 * The unchanged inspector excludes any following-day partial D100 rows.
 * This never converts a current intraday price into yesterday's close.
 */
export function daytimeCatchUpWindow(now,explicitAsOf){
  need(typeof now==='string'&&typeof explicitAsOf==='string'&&
    /^20\d{2}-\d{2}-\d{2}$/.test(explicitAsOf),'CATCHUP_ARGUMENT_INVALID');
  const local=now.slice(0,10),clock=now.slice(11,16);
  need(isJpxCashTradingDay(local)&&isJpxCashTradingDay(explicitAsOf)&&
    nextCashDate(explicitAsOf)===local&&lastCompletedSession(now)===explicitAsOf&&
    clock>='08:30'&&clock<'18:00'&&!isoFriday(explicitAsOf),
    'CATCHUP_REQUIRES_ACTUAL_PREVIOUS_CASH_DAY');
  return {date:explicitAsOf,now,daytimeHistoricalRecovery:true};
}
export function yahooFridayConfirmationWindow(now){
  const date=now.slice(0,10),clock=now.slice(11,16);
  need(isJpxCashTradingDay(date)&&isoFriday(date)&&clock>='19:00'&&
    lastCompletedSession(now)===date,'YAHOO_FRIDAY_RSS_CONFIRM_AFTER_1900_ONLY');
  return {date,now,yahooFridayRssConfirmation:true};
}
function currentAsOf(catchUpAsOf='',confirmYahooFriday=false){
  need(!(catchUpAsOf&&confirmYahooFriday),'CATCHUP_AND_FRIDAY_MODES_CONFLICT');
  if(confirmYahooFriday)return yahooFridayConfirmationWindow(jstNow());
  const {date,now,daytimeHistoricalRecovery=false}=catchUpAsOf?
    daytimeCatchUpWindow(jstNow(),catchUpAsOf):nightlyWindow(jstNow());
  need(!isoFriday(date),'FRIDAY_FULL_MARKET_SWEEP_REQUIRED');
  return {date,now,daytimeHistoricalRecovery};
}
function assembleDailyPlan(source,date,now,daytimeHistoricalRecovery=false,yahooFridayRssConfirmation=false){
  const sameFriday=yahooFridayRssConfirmation&&source.plan.sourceProvider===YAHOO_SOURCE&&
    isoFriday(date)&&date===source.plan.asOfSession;
  need(!yahooFridayRssConfirmation||sameFriday,
    'FRIDAY_CONFIRM_REQUIRES_MATCHING_YAHOO_SEED');
  const gap=sameFriday?0:tradingGap(source.plan.asOfSession,date);
  need(sameFriday||(gap>=1&&gap<=4),'WEEKLY_POOL_EXPIRED_FULL_SWEEP_REQUIRED');
  const symbols=[...source.mask.observedPassSymbols];
  const poolDigest=SHA(JSON.stringify(symbols));
  const body={
    schemaId:DAILY_PLAN_SCHEMA,
    createdAtJst:now,
    asOfSession:date,
    expectedSessions:requiredDailySessions(date),
    sourceSymbolsSha256:poolDigest,
    codeSha256:codeIdentity(),
    symbols,baselineAdded:[],
    refreshSchemaId:dailySchema,
    weeklyG1Policy:contract,
    universeScope:'WEEKLY_OBSERVED_PASS_POOL_ONLY',
    weeklySource:{asOfSession:source.plan.asOfSession,
      originalPlanId:source.plan.planId,observedPassCount:symbols.length,
      observedPassSymbolsSha256:poolDigest,originalFullUniverseCount:source.plan.symbols.length,
      elapsedCashSessions:gap},
    newWeeklyBreakoutsIncluded:false,
    unknownNotAdmitted:true,
    priceBasisCertified:false,
    productionReady:false,orderTransmission:false
  };
  if(source.plan.sourceProvider===YAHOO_SOURCE){
    body.weeklySource.originProvider=YAHOO_SOURCE;
    body.weeklySource.yahooSourcePriceBasisCertified=false;
    body.weeklySource.requiresIndependentPriceReview=true;
  }
  if(sameFriday){
    body.yahooFridayRssConfirmation=true;
    body.weeklySource.sourceWasYahooButDailyCandlesAreRss=true;
  }
  if(daytimeHistoricalRecovery){
    // Source is retrieved NOW, never backdated to yesterday. G1 evaluates
    // yesterday's 76 CASH sessions, explicitly ignoring today's partial bar.
    body.daytimeHistoricalRecovery=true;
    body.recoveryObservedCalendarDay=now.slice(0,10);
    body.historicalAsOfSession=date;
    body.futurePartialBarsExcludedFromG1=true;
  }
  return {planId:SHA(JSON.stringify(body)),...body};
}
function stagePlan(weeklyRun,root,catchUpAsOf='',confirmYahooFriday=false){
  const source=verifyWeeklySource(weeklyRun);
  const {date,now,daytimeHistoricalRecovery=false,yahooFridayRssConfirmation=false}=
    currentAsOf(catchUpAsOf,confirmYahooFriday);
  const base=directory(root,true);
  const fragment=source.plan.planId.slice(0,16);
  const run=directory(path.join(base,'weekly-refresh-'+date+'-'+fragment),true);
  directory(path.join(run,'sources'),true);
  const planFile=path.join(run,'plan.json');
  if(!fs.existsSync(planFile))immutable(planFile,assembleDailyPlan(source,date,now,daytimeHistoricalRecovery,yahooFridayRssConfirmation));
  const plan=regular(planFile);
  validateRefreshPlan(plan,source,date);
  const captures=loadCaptures(run,plan);
  return {run,plan,captures,
    resumed:captures.length,
    remaining:plan.symbols.filter(s=>!new Set(captures.map(v=>v.symbol)).has(s))};
}
function validateRefreshPlan(plan,source,date){
  const {planId,...body}=plan;
  need(plan.schemaId===DAILY_PLAN_SCHEMA&&
    plan.refreshSchemaId===dailySchema&&plan.weeklyG1Policy===contract&&
    plan.asOfSession===date&&plan.codeSha256===codeIdentity()&&
    SHA(JSON.stringify(body))===planId&&
    JSON.stringify(plan.expectedSessions)===JSON.stringify(requiredDailySessions(date))&&
    JSON.stringify(plan.symbols)===JSON.stringify(source.mask.observedPassSymbols)&&
    plan.weeklySource.originalPlanId===source.plan.planId&&
    plan.weeklySource.asOfSession===source.plan.asOfSession&&
    plan.weeklySource.observedPassCount===source.mask.observedPassCount&&
    plan.weeklySource.observedPassSymbolsSha256===SHA(JSON.stringify(plan.symbols))&&
    (source.plan.sourceProvider===YAHOO_SOURCE?
      (plan.weeklySource.originProvider===YAHOO_SOURCE&&
       plan.weeklySource.yahooSourcePriceBasisCertified===false&&
       plan.weeklySource.requiresIndependentPriceReview===true):
      !Object.hasOwn(plan.weeklySource,'originProvider'))&&
    plan.newWeeklyBreakoutsIncluded===false&&plan.unknownNotAdmitted===true&&
    plan.productionReady===false&&plan.orderTransmission===false,
    'REFRESH_PLAN_LINEAGE_OR_CONTENT_INVALID');
  if(plan.yahooFridayRssConfirmation===true){
    need(source.plan.sourceProvider===YAHOO_SOURCE&&
      plan.weeklySource.sourceWasYahooButDailyCandlesAreRss===true&&
      source.plan.asOfSession===date&&isoFriday(date)&&
      typeof plan.createdAtJst==='string'&&
      plan.createdAtJst.slice(0,10)===date&&
      plan.createdAtJst.slice(11,16)>='19:00'&&
      plan.weeklySource.elapsedCashSessions===0,
      'YAHOO_FRIDAY_REAL_RSS_PLAN_CONTRACT');
  }
  if(plan.daytimeHistoricalRecovery===true){
    need(plan.recoveryObservedCalendarDay===nextCashDate(date)&&
      plan.historicalAsOfSession===date&&
      plan.futurePartialBarsExcludedFromG1===true&&
      typeof plan.createdAtJst==='string'&&
      plan.createdAtJst.slice(0,10)===plan.recoveryObservedCalendarDay&&
      plan.createdAtJst.slice(11,16)>='08:30',
      'CATCHUP_ACTUAL_RECEIPT_CLOCK_INVALID');
  }
  if(plan.yahooFridayRssConfirmation!==true){
    need(tradingGap(source.plan.asOfSession,date)>=1&&
      tradingGap(source.plan.asOfSession,date)<=4,'WEEKLY_POOL_EXPIRED');
  }
  return plan;
}
export function runCli(args){
  const action=args[0], flags={};
  if(action==='schedule'){
    need(args.length===1,'USAGE');
    const {date,now,followingPreopen}=nightlyWindow(jstNow());
    console.log(JSON.stringify({schemaId:'ARK_NO11_WEEKLY_REFRESH_SCHEDULE_V1',
      asOfSession:date,sessionDate:nextCashDate(date),
      mode:isoFriday(date)?'FULL_MARKET_FRIDAY':'WEEKLY_POOL_CANDIDATES_ONLY',
      completedDailyDataMustBeObserved:true,
      productionReady:false,orderTransmission:false}));
    return;
  }
  need(['plan','report'].includes(action)&&args.length%2===1,'USAGE');
  for(let i=1;i<args.length;i+=2){
    need(['--weekly-run','--root','--run','--pins-file','--catch-up-asof','--yahoo-friday-rss-confirm'].includes(args[i])&&!flags[args[i]],'USAGE');
    flags[args[i]]=args[i+1];
  }
  need(flags['--weekly-run'],'WEEKLY_RUN_REQUIRED');
  if(action==='plan'){
    need(flags['--root']&&!flags['--run']&&!flags['--pins-file'],'USAGE');
    need(!flags['--yahoo-friday-rss-confirm']||flags['--yahoo-friday-rss-confirm']==='true',
      'YAHOO_FRIDAY_CONFIRM_FLAG_INVALID');
    const staged=stagePlan(flags['--weekly-run'],flags['--root'],
      flags['--catch-up-asof']??'',flags['--yahoo-friday-rss-confirm']==='true');
    console.log(JSON.stringify({run:staged.run,plan:staged.plan,
      resumed:staged.resumed,remaining:staged.remaining,
      weeklyRestrictedUniverse:true}));
  } else {
    need(flags['--run']&&!flags['--root'],'USAGE');
    const source=verifyWeeklySource(flags['--weekly-run']);
    const run=directory(flags['--run']);
    const plan=regular(path.join(run,'plan.json'));
    const {date}=currentAsOf(flags['--catch-up-asof']??'',flags['--yahoo-friday-rss-confirm']==='true');
    validateRefreshPlan(plan,source,date);
    const captures=loadCaptures(run,plan);
    const {summary}=summarizeDailyCaptures(plan,captures);
    const completeness=summary.status==='COMPLETE_OBSERVED_STRUCTURE_ONLY';
    console.log('NO11_WEEKLY_REFRESH_CAPTURES='+captures.length+'/'+plan.symbols.length);
    console.log('NO11_WEEKLY_REFRESH_OBSERVED_G1='+JSON.stringify(summary.observedStructureCounts));
    if(!completeness){
      console.log('NO11_WEEKLY_REFRESH=INCOMPLETE_NO_MASK_OR_PLAN');
      console.log('ORDER_TRANSMISSION=False');
      process.exitCode=2;return;
    }
    const mask=makeObservedPassWatchMask(plan,captures);
    need(mask.observedPassCount>0&&mask.observedPassCount<=500,'DAILY_PASS_COUNT_INVALID');
    mask.source='WEEKLY_LOCKED_POOL_FRESH_DAILY_RSS_CHART_D100';
    mask.weeklyG1Policy=contract;
    mask.weeklyOriginalAsOfSession=source.plan.asOfSession;
    mask.originalWeeklyFullUniverseCount=source.plan.symbols.length;
    mask.weeklyPoolSourcePlanId=source.plan.planId;
    mask.weeklyPoolPopulation=plan.symbols.length;
    if(source.plan.sourceProvider===YAHOO_SOURCE){
      mask.weeklyOriginalProvider=YAHOO_SOURCE;
      mask.yahooWeeklySourceUnverifiedForTrading=true;
    }
    mask.newBreakoutsOutsideWeeklyPoolNotScanned=true;
    if(plan.daytimeHistoricalRecovery===true){
      mask.daytimeHistoricalRecovery=true;
      mask.recoveryObservedCalendarDay=plan.recoveryObservedCalendarDay;
      mask.historicalAsOfSession=date;
      mask.futurePartialBarsExcludedFromG1=true;
    }
    mask.sourceManifestSha256=SHA(JSON.stringify(
      fs.readdirSync(path.join(run,'sources')).filter(n=>n.endsWith('.json')).sort()));
    const mBytes=Buffer.from(JSON.stringify(mask)+'\n');
    const maskFile=path.join(run,'no11-observed-pass-watch-'+SHA(mBytes).slice(0,16)+'.json');
    immutable(maskFile,mask);
    const priorities=rankVerifiedG1PassForChartBudget(plan,captures,mask);
    let slots={heldSymbols:[],activeWatchSymbols:[],pendingOrderSymbols:[],
      otherChartFunctions:0,emptySafetySlots:3,otherQuoteCapacity:0,otherQuoteSymbols:[]};
    if(flags['--pins-file']){
      const pins=regular(flags['--pins-file'],100_000);
      const requested=['heldSymbols','activeWatchSymbols','pendingOrderSymbols',
        'otherChartFunctions','emptySafetySlots','otherQuoteCapacity','otherQuoteSymbols'];
      need(pins.schemaId==='ARK_NO11_CHART50_PRIVATE_PINS_V1'&&
        pins.sessionDate===nextCashDate(date)&&
        pins.productionReady===false&&pins.orderTransmission===false&&
        requested.every(k=>Object.hasOwn(pins,k)),'PINS_CONTRACT_INVALID');
      slots=Object.fromEntries(requested.map(k=>[k,pins[k]]));
    }
    const sessionDate=nextCashDate(date);
    const chartPlan=makeNo11G1Chart50Plan({mask,priorityRows:priorities,
      sessionDate,...slots});
    const receipt={schemaId:'ARK_NO11_CHART50_PRIVATE_EXPORT_RECEIPT_V1',
      source:'WEEKLY_POOL_DAILY_REFRESH_ONLY_NOT_CURRENT_FULL_MARKET',
      chartPlan,originalSourceCaptured:captures.length,noRecapture:true,
      weeklyG1Policy:contract,weeklyFullAsOfSession:source.plan.asOfSession,
      weeklyOriginalProvider:source.plan.sourceProvider??'MSII_RSS_ORIGINAL_WEEKLY',
      currentRefreshAsOfSession:date,weeklyCandidateCount:plan.symbols.length,
      accountPositionsBrokerVerified:false,
      actualChartFunctionOccupancyVerified:false,
      selectedRankingEconomicEquivalenceVerified:false,
      selectorLiveConnected:false,
      daytimeHistoricalRecovery:plan.daytimeHistoricalRecovery===true,
      recoveryObservedCalendarDay:plan.recoveryObservedCalendarDay??null,
      historicalAsOfSession:date,
      futurePartialBarsExcludedFromG1:plan.daytimeHistoricalRecovery===true,
      shadowOnly:true,
      productionReady:false,orderTransmission:false};
    const rBytes=Buffer.from(JSON.stringify(receipt)+'\n');
    const receiptFile=path.join(run,'no11-chart50-private-'+SHA(rBytes).slice(0,16)+'.json');
    immutable(receiptFile,receipt);
    console.log('NO11_WEEKLY_REFRESH_DAYTIME_CATCHUP='+(plan.daytimeHistoricalRecovery===true?'ACTUAL_RSS_NOW_PRIOR_ASOF_ONLY':'NO'));
    console.log('NO11_WEEKLY_REFRESH_PASS='+mask.observedPassCount);
    console.log('NO11_WEEKLY_REFRESH_CHARTS='+chartPlan.arkChartsUsed);
    console.log('NO11_WEEKLY_REFRESH_WEEKLY_ORIGIN='+source.plan.asOfSession);
    console.log('NO11_WEEKLY_REFRESH_CURRENT_CLOSE='+date);
    console.log('NO11_WEEKLY_REFRESH_YAHOO_FRIDAY_RSS_CONFIRM='+(plan.yahooFridayRssConfirmation===true));
    console.log('NO11_WEEKLY_REFRESH_MASK='+maskFile);
    console.log('NO11_WEEKLY_REFRESH_CHART50='+receiptFile);
    console.log('NO11_WEEKLY_REFRESH_SCOPE=WEEKLY_POOL_ONLY_EXCLUDES_NEW_BREAKOUTS');
    console.log('NO11_WEEKLY_REFRESH=COMPLETE_SHADOW_CAPACITY_ONLY');
    console.log('ORDER_TRANSMISSION=False');
  }
}
export function nextCashDate(d){
  for(let cur=new Date(Date.parse(d+'T00:00:00Z')+86_400_000),i=0;i<14;i++,cur=new Date(cur.getTime()+86_400_000)){
    const x=cur.toISOString().slice(0,10);
    if(isJpxCashTradingDay(x))return x;
  }
  fail('NEXT_CASH_SESSION_MISSING');
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){
  try{runCli(process.argv.slice(2));}
  catch(e){console.error(/^NO11_WEEKLY_/.test(e.message)?e.message:'NO11_WEEKLY_PRIVATE_SOURCE_FAILURE');process.exitCode=2;}
}
