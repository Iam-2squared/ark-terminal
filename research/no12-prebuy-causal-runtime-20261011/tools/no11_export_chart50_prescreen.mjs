/**
 * Private offline G1-348 to Chart50 prescreen exporter. No Excel/network/broker.
 * Does not alter the original immutable daily plan or captures.
 * Account pinned slots can ONLY be supplied from a separate private local file;
 * without one, plan is a capacity dry-run NOT eligible for live chart wiring.
 */
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {codeIdentity,loadCaptures,immutable}
  from './no11_rss_daily_trend_census.mjs';
import {DAILY_PLAN_SCHEMA}
  from '../runtime/no11_rss_daily_trend_census.mjs';
import {makeObservedPassWatchMask}
  from '../runtime/no11_observed_pass_watch_gate.mjs';
import {rankVerifiedG1PassForChartBudget,makeNo11G1Chart50Plan}
  from '../runtime/no11_rss_chart_50_prescreen.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const hash=x=>createHash('sha256').update(x).digest('hex');
const fail=(reason)=>{throw Error('NO11_CHART50_'+reason)};
function privateFile(filename,sizeLimit){
  if(typeof filename!=='string'||!path.isAbsolute(filename))
    fail('ABSOLUTE_PRIVATE_FILE_REQUIRED');
  const full=path.resolve(filename);
  if(full===root||full.startsWith(root+path.sep))
    fail('FILE_IN_REPO_FORBIDDEN');
  const stat=fs.lstatSync(full);
  if(!stat.isFile()||stat.isSymbolicLink()||stat.size>sizeLimit)
    fail('INVALID_PRIVATE_FILE');
  return JSON.parse(fs.readFileSync(full,'utf8').replace(/^\uFEFF/,''));
}
export function runNo11Chart50OfflineExport(args){
  if(args.length!==4&&args.length!==6)
    fail('USAGE');
  if(args[0]!=='--run'||args[2]!=='--session')
    fail('USAGE');
  const run=path.resolve(args[1]),sessionDate=args[3];
  if(!path.isAbsolute(args[1])||run===root||
    run.startsWith(root+path.sep)||!fs.lstatSync(run).isDirectory()||
    fs.lstatSync(run).isSymbolicLink())
    fail('PRIVATE_RUN_REQUIRED');
  const plan=privateFile(path.join(run,'plan.json'),4_000_000);
  const {planId,...body}=plan;
  if(plan.schemaId!==DAILY_PLAN_SCHEMA||
    hash(JSON.stringify(body))!==planId||plan.codeSha256!==codeIdentity())
    fail('SAVED_CENSUS_PLAN_PIN_MISMATCH');
  const captures=loadCaptures(run,plan);
  const mask=makeObservedPassWatchMask(plan,captures);
  const priorities=rankVerifiedG1PassForChartBudget(plan,captures,mask);
  let slots={
    heldSymbols:[],activeWatchSymbols:[],pendingOrderSymbols:[],
    otherChartFunctions:0,emptySafetySlots:3,
    otherQuoteCapacity:0,otherQuoteSymbols:[]
  },source='NO_ACCOUNT_STATE_SUPPLIED_CAPACITY_ONLY';
  if(args.length===6){
    if(args[4]!=='--pins-file')fail('USAGE');
    const input=privateFile(args[5],100_000);
    if(input.schemaId!=='ARK_NO11_CHART50_PRIVATE_PINS_V1'||
      input.sessionDate!==sessionDate||
      input.orderTransmission!==false||
      input.productionReady!==false)
      fail('PINS_CONTRACT_INVALID');
    const fields=[
      'heldSymbols','activeWatchSymbols','pendingOrderSymbols',
      'otherChartFunctions','emptySafetySlots',
      'otherQuoteCapacity','otherQuoteSymbols'
    ];
    if(fields.some(key=>!Object.hasOwn(input,key)))
      fail('PINS_FIELDS_INCOMPLETE');
    slots=Object.fromEntries(fields.map(key=>[key,input[key]]));
    source='USER_SUPPLIED_PRIVATE_PINS_NOT_BROKER_CERTIFIED';
  }
  const chartPlan=makeNo11G1Chart50Plan({
    mask,priorityRows:priorities,sessionDate,...slots
  });
  const receipt={
    schemaId:'ARK_NO11_CHART50_PRIVATE_EXPORT_RECEIPT_V1',
    source,chartPlan,
    originalSourceCaptured:captures.length,
    noRecapture:true,
    accountPositionsBrokerVerified:false,
    actualChartFunctionOccupancyVerified:false,
    selectedRankingEconomicEquivalenceVerified:false,
    selectorLiveConnected:false,shadowOnly:true,
    productionReady:false,orderTransmission:false
  };
  const bytes=Buffer.from(JSON.stringify(receipt)+'\n');
  const name='no11-chart50-private-'+hash(bytes).slice(0,16)+'.json';
  const output=path.join(run,name);
  immutable(output,receipt);
  console.log('NO11_CHART50_G1PASS='+chartPlan.observedG1PassCount);
  console.log('NO11_CHART50_SCAN='+chartPlan.scanChartSymbols.length);
  console.log('NO11_CHART50_PROTECTED='+chartPlan.protectedChartSymbols.length);
  console.log('NO11_CHART50_OTHER_FUNCTIONS='+chartPlan.occupiedByOtherChartFunctions);
  console.log('NO11_CHART50_SAFETY_EMPTY='+chartPlan.reserveEmptyChartSlots);
  console.log('NO11_CHART50_TOTAL_CHARTS='+chartPlan.totalChartFunctionsBudgeted+'/50');
  console.log('NO11_CHART50_RECEIPT='+output);
  console.log('NO11_CHART50_ACTUAL_RSS_VERIFIED=False');
  console.log('ORDER_TRANSMISSION=False');
  return receipt;
}
if(process.argv[1]&&
  import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){
  try{runNo11Chart50OfflineExport(process.argv.slice(2));}
  catch(e){
    console.error(/^NO11_CHART50_/.test(e.message)?e.message:
      'NO11_CHART50_PRIVATE_IO_FAILURE');
    process.exitCode=2;
  }
}
