/**
 * No.1.1 original Selector / daily G1 — CONDITIONAL numeric exclusion audit.
 *
 * Reads previously captured and verified local RSS daily data only.
 * No new acquisition, Excel, broker, order transmission or learner.
 * The original classifier status for MALFORMED and UNAVAILABLE stays UNKNOWN.
 *
 * Partial arithmetic answers: "Given the preserved usable closes, can the
 * 4 SMA-up gates simultaneously be true?" This is conditional on unverified
 * provider price basis and therefore never a production eligibility proof.
 */
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {codeIdentity, loadCaptures, immutable}
  from './no11_rss_daily_trend_census.mjs';
import {diagnoseStoredUnknowns}
  from './no11_rss_daily_unknown_audit.mjs';
import {DAILY_PLAN_SCHEMA, inspectDailyCapture}
  from '../runtime/no11_rss_daily_trend_census.mjs';

const PERIODS=Object.freeze([5,15,25,75]);
const HERE=path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT=path.resolve(HERE,'../../..');
const SHA=data=>createHash('sha256').update(data).digest('hex');
function must(condition,code){
  if(!condition)throw Error('NO11_DAILY_PARTIAL_'+code);
}
function readJson(file){
  const st=fs.lstatSync(file);
  must(st.isFile() && !st.isSymbolicLink() && st.size < 4_000_000,
    'INPUT_FILE_INVALID');
  return JSON.parse(fs.readFileSync(file,'utf8').replace(/^\uFEFF/,''));
}
function decimal(value){
  if(typeof value!=='string'||value.length>96||
     !/^(?:0|[1-9]\d*)(?:\.\d+)?$/.test(value))return null;
  const chunks=value.split('.'),digits=chunks.join('');
  const coefficient=BigInt(digits);
  return coefficient>0n ?
    {coefficient,precision:(chunks[1]??'').length}:null;
}
function cmpGreater(left,right,precision){
  const a=left.coefficient*10n**BigInt(precision-left.precision);
  const b=right.coefficient*10n**BigInt(precision-right.precision);
  return a>b;
}
function smaGreater(price,others,n,precision){
  const fixed=price.coefficient*10n**BigInt(precision-price.precision);
  const sum=others.reduce((s,item)=>
    s+item.coefficient*10n**BigInt(precision-item.precision),0n);
  return BigInt(n)*fixed>sum;
}

/** Observed-close-only, partial evidence. NEVER returns a live PASS status. */
export function partialDailyUpEvidence(expectedSessions,rawRows){
  must(Array.isArray(expectedSessions)&&expectedSessions.length===76,
    'CALENDAR_REQUIRED');
  must(Array.isArray(rawRows), 'ROWS_REQUIRED');
  const wanted=new Set(expectedSessions),rows=new Map();
  let duplicateRequiredDates=0,invalidStoredClosing=0;
  for(const row of rawRows){
    if(!row || !wanted.has(row.session))continue;
    if(rows.has(row.session)){
      duplicateRequiredDates++;
      continue;
    }
    const parsed=decimal(row.close);
    if(parsed===null)invalidStoredClosing++;
    rows.set(row.session,parsed);
  }
  if(duplicateRequiredDates || invalidStoredClosing)
    return {
      category:'UNRESOLVED', reason:'DUPLICATE_OR_UNPARSEABLE_REQUIRED_CLOSE',
      knownFalsePeriods:[],knownTruePeriods:[],unknownPeriods:[...PERIODS],
      missingRequiredDates:expectedSessions.filter(d=>!rows.has(d)).length,
      duplicateRequiredDates,invalidStoredClosing,
    };
  const values=expectedSessions.map(date=>rows.get(date)??null);
  const missingRequiredDates=values.filter(v=>v===null).length;
  const newest=values[75], maxPrecision=Math.max(
    0,...values.filter(Boolean).map(v=>v.precision));
  const knownFalsePeriods=[],knownTruePeriods=[],unknownPeriods=[];
  for(const n of PERIODS){
    let slope=null,above=null;
    const past=values[75-n];
    if(newest!==null && past!==null)
      slope=cmpGreater(newest,past,maxPrecision);
    const recent=values.slice(76-n);
    if(newest!==null && recent.every(v=>v!==null))
      above=smaGreater(newest,recent,n,maxPrecision);
    const up=(slope===false||above===false) ? false :
      ((slope===true&&above===true)?true:null);
    if(up===false)knownFalsePeriods.push(n);
    else if(up===true)knownTruePeriods.push(n);
    else unknownPeriods.push(n);
  }
  const category=knownFalsePeriods.length ? 'OBSERVED_NUMERIC_CANNOT_PASS' :
    (knownTruePeriods.length===PERIODS.length ?
      'OBSERVED_NUMERIC_ALL_UP_BUT_SOURCE_UNCERTIFIED':'UNRESOLVED');
  return {
    category,
    knownFalsePeriods,knownTruePeriods,unknownPeriods,
    missingRequiredDates,duplicateRequiredDates,invalidStoredClosing,
  };
}
export function measureUnknownConditionalBounds(plan,captures){
  // Existing original count/status/receipt invariants, including UNKNOWN=710.
  const baseline=diagnoseStoredUnknowns(plan,captures).report;
  const counts={
    malformedObservedCannotPass:0,
    malformedObservedAllUpButSourceUncertified:0,
    malformedUnresolved:0,
    unavailable:0,otherUnknown:0,
    perPeriod:{
      '5':{true:0,false:0,unknown:0},
      '15':{true:0,false:0,unknown:0},
      '25':{true:0,false:0,unknown:0},
      '75':{true:0,false:0,unknown:0},
    }
  };
  const privateDetails=[];
  for(const capture of captures){
    const original=inspectDailyCapture(capture,plan);
    if(original.status!=='UNKNOWN')continue;
    if(original.reason==='MALFORMED_SOURCE_ROWS'){
      const evidence=partialDailyUpEvidence(plan.expectedSessions,capture.rows);
      const key=evidence.category==='OBSERVED_NUMERIC_CANNOT_PASS'?
        'malformedObservedCannotPass':
        evidence.category==='OBSERVED_NUMERIC_ALL_UP_BUT_SOURCE_UNCERTIFIED'?
          'malformedObservedAllUpButSourceUncertified':'malformedUnresolved';
      counts[key]++;
      for(const n of PERIODS){
        const name=String(n),item=counts.perPeriod[name];
        if(evidence.knownFalsePeriods.includes(n))item.false++;
        else if(evidence.knownTruePeriods.includes(n))item.true++;
        else item.unknown++;
      }
      privateDetails.push({symbol:capture.symbol,originalReason:original.reason,
        invalidRows:capture.invalidRows,...evidence});
    } else {
      if(original.reason==='SOURCE_UNAVAILABLE')counts.unavailable++;
      else counts.otherUnknown++;
      privateDetails.push({symbol:capture.symbol,originalReason:original.reason,
        category:'UNRESOLVED'});
    }
  }
  const malformed=counts.malformedObservedCannotPass+
    counts.malformedObservedAllUpButSourceUncertified+
    counts.malformedUnresolved;
  must(malformed===baseline.unknownReasons.malformedRows,
    'MALFORMED_COUNT_MISMATCH');
  must(counts.unavailable===baseline.unknownReasons.unavailable &&
       counts.otherUnknown===baseline.unknownReasons.otherCapturedUnknown,
    'UNKNOWN_REASON_COUNT_MISMATCH');
  const observedPass=baseline.originalStructureCounts.PASS;
  const unresolved=baseline.originalStructureCounts.UNKNOWN;
  const conditionalUpper=observedPass+unresolved-counts.malformedObservedCannotPass;
  const report={
    schemaId:'ARK_NO11_RSS_DAILY_PARTIAL_NUMERIC_BOUNDS_V1',
    status:'CONDITIONAL_RSS_OBSERVED_ARITHMETIC_ONLY',
    planId:plan.planId,
    asOfSession:plan.asOfSession,
    requestedSymbols:baseline.requestedSymbols,
    capturedSymbols:baseline.capturedSymbols,
    originalCounts:baseline.originalStructureCounts,
    originalUnknownReasons:baseline.unknownReasons,
    remainingUncaptured:baseline.uncapturedSymbols,
    observedPass,
    conditionalObservedCannotPass:counts.malformedObservedCannotPass,
    conditionalStillCouldPass:unresolved-counts.malformedObservedCannotPass,
    conditionalPossiblePassUpperBound:conditionalUpper,
    unconditionalObservedUpperBound:observedPass+unresolved,
    passLowerBoundOnObservedStructure:observedPass,
    counts,
    rssMarketCeiling:500,
    conditional500CeilingEstablished:conditionalUpper<=500,
    fullUniverse500CeilingCertified:false,
    remainingUnknownRowsStayUnknown:true,
    knownInvalidRowDatesPreserved:false,
    priceBasisCertified:false,
    corporateActionsCertified:false,
    minuteVaCertified:false,
    currentDatedMasterCertified:false,
    providerReceivedAtCertified:false,
    originalSelectorLiveConnected:false,
    newModelTraining:false,
    productionReady:false,
    orderTransmission:false,
  };
  return {report,privateDetails};
}
export function auditLocalRun(args){
  must(args.length===2 && args[0]==='--run' && args[1],
    'ARGUMENTS');
  const run=path.resolve(args[1]);
  must(path.isAbsolute(args[1])&&
    !run.startsWith(REPO_ROOT+path.sep)&&run!==REPO_ROOT,
    'PRIVATE_RUN_REQUIRED');
  const st=fs.lstatSync(run);
  must(st.isDirectory()&&!st.isSymbolicLink(),'RUN_DIRECTORY_INVALID');
  const plan=readJson(path.join(run,'plan.json'));
  must(plan.schemaId===DAILY_PLAN_SCHEMA,'PLAN_SCHEMA');
  const {planId,...body}=plan;
  must(SHA(JSON.stringify(body))===planId,'PLAN_HASH');
  must(plan.codeSha256===codeIdentity(),'CAPTURE_CODE_IDENTITY_CHANGED');
  const captures=loadCaptures(run,plan);
  const {report,privateDetails}=measureUnknownConditionalBounds(plan,captures);
  const names=fs.readdirSync(path.join(run,'sources'))
    .filter(name=>name.endsWith('.json')).sort();
  report.sourceManifestSha256=SHA(JSON.stringify(names));
  const detailBytes=Buffer.from(JSON.stringify(privateDetails)+'\n');
  report.privateDetailsSha256=SHA(detailBytes);
  immutable(path.join(run,'private-partial-numeric-unknown-'
    +report.privateDetailsSha256.slice(0,16)+'.json'),privateDetails);
  const bytes=Buffer.from(JSON.stringify(report)+'\n');
  const resultFile=path.join(run,'no11-daily-partial-bound-'
    +SHA(bytes).slice(0,16)+'.json');
  immutable(resultFile,report);
  console.log('NO11_DAILY_PARTIAL_AUDIT='+report.status);
  console.log('NO11_DAILY_PARTIAL_CATEGORIES='+
    JSON.stringify(report.counts));
  console.log('NO11_DAILY_CONDITIONAL_POSSIBLE_PASS_UPPER='+
    report.conditionalPossiblePassUpperBound);
  console.log('NO11_DAILY_PARTIAL_REPORT='+resultFile);
  console.log('NO11_PRODUCTION_READY=False');
  console.log('ORDER_TRANSMISSION=False');
}
if(process.argv[1]&&
   import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){
  try{auditLocalRun(process.argv.slice(2));}
  catch(error){
    console.error(/^NO11_DAILY_/.test(error.message)?
      error.message:'NO11_DAILY_PARTIAL_LOCAL_IO_FAILURE');
    process.exitCode=2;
  }
}
