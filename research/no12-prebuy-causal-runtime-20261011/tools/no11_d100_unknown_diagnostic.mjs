#!/usr/bin/env node
/**
 * Diagnose, never repair, an already-completed 429-symbol RSS D100 run.
 * Executable from TEMP: dynamically imports only the user's installed,
 * existing protected Ark runtime through --engine-root. Every source is
 * read, SHA-checked, and evaluated using the ORIGINAL G1 contract.
 * No Excel, network, order, mutation, private prices or symbols printed.
 */
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';

export const SCHEMA='ARK_NO11_D100_UNKNOWN_REASONS_DIAGNOSTIC_V1';
const HASH=x=>createHash('sha256').update(x).digest('hex');
const need=(v,code)=>{if(!v)throw Error('NO11_D100_DIAG_'+code)};
function exactArgs(values){
 need(values.length===4,'USAGE_REQUIRED');
 const args={};
 for(let i=0;i<values.length;i+=2){
  need(['--engine-root','--run'].includes(values[i])&&!Object.hasOwn(args,values[i]),
    'USAGE_INVALID');
  args[values[i]]=values[i+1];
 }
 return args;
}
function validPath(value,directory){
 need(typeof value==='string'&&path.isAbsolute(value),'ABSOLUTE_PATH_REQUIRED');
 const location=path.resolve(value);
 let cursor=location;
 for(;;){
  if(fs.existsSync(cursor))need(!fs.lstatSync(cursor).isSymbolicLink(),'REPARSE_SOURCE');
  const parent=path.dirname(cursor);
  if(parent===cursor)break;
  cursor=parent;
 }
 const stat=fs.statSync(location);
 need(directory?stat.isDirectory():stat.isFile(),'SOURCE_TYPE');
 if(!directory)need(stat.size>0&&stat.size<=8_000_000,'SOURCE_SIZE');
 return location;
}
const countBy=(rows,keyFn)=>{
 const result={};
 for(const item of rows){
  const key=keyFn(item);
  result[key]=(result[key]??0)+1;
 }
 return Object.fromEntries(Object.entries(result).sort((a,b)=>a[0].localeCompare(b[0])));
};
export function aggregateUnknownDiagnostics(plan,captures,inspect,summary){
 need(plan&&plan.asOfSession==='2026-10-28'&&
  Array.isArray(plan.symbols)&&plan.symbols.length===429&&
  Array.isArray(plan.expectedSessions)&&plan.expectedSessions.length===76&&
  captures.length===429,'EXPECTED_EXACT_OCT28_429_SCOPE');
 const byDay={},reasonCounts={};
 const buckets={
  observed:0,unavailable:0,nonzeroInvalidRows:0,invalidRowsTotal:0,
  full76DatesPresent:0,full76ButUnknown:0,
  laterRowsIgnoredInTheory:0,rowsTotal:0,conditionalUnknownAfterIgnoringInvalidCount:0,
  conditionalPassAfterIgnoringInvalidCount:0,
  conditionalWaitAfterIgnoringInvalidCount:0,
  conditionalRejectAfterIgnoringInvalidCount:0
 };
 const required=new Set(plan.expectedSessions);
 for(const item of captures){
  const day=item.observedStartJst.slice(0,10);
  if(!Object.hasOwn(byDay,day))
   byDay[day]={total:0,unknown:0,invalidRowSources:0,unavailable:0};
  const bucket=byDay[day];
  bucket.total++;
  buckets.rowsTotal+=item.rows.length;
  const requested=new Set(item.rows.map(b=>b.session));
  const full76=plan.expectedSessions.every(d=>requested.has(d));
  if(full76)buckets.full76DatesPresent++;
  const ignored=item.rows.filter(b=>typeof b.session==='string'&&b.session>plan.asOfSession).length;
  buckets.laterRowsIgnoredInTheory+=ignored;
  if(item.status==='OBSERVED')buckets.observed++;
  if(item.status==='UNAVAILABLE'){buckets.unavailable++;bucket.unavailable++;}
  if(item.invalidRows>0){buckets.nonzeroInvalidRows++;bucket.invalidRowSources++;buckets.invalidRowsTotal+=item.invalidRows;}
  const current=inspect(item,plan);
  reasonCounts[current.reason]=(reasonCounts[current.reason]??0)+1;
  if(current.status==='UNKNOWN'){
   bucket.unknown++;
   if(full76)buckets.full76ButUnknown++;
  }
  // DIAGNOSTIC WHAT-IF ONLY. Results CANNOT be promoted as G1 evidence.
  // The original collector did not record rejected row dates, so even
  // 76 valid-looking bars cannot prove discarded rows are innocuous.
  if(item.invalidRows>0){
   const hypothetical=inspect({...item,invalidRows:0},plan);
   const label={PASS:'conditionalPassAfterIgnoringInvalidCount',
    WAIT:'conditionalWaitAfterIgnoringInvalidCount',
    REJECT:'conditionalRejectAfterIgnoringInvalidCount',
    UNKNOWN:'conditionalUnknownAfterIgnoringInvalidCount'}[hypothetical.status];
   buckets[label]++;
  }
 }
 const unknown=Object.fromEntries(Object.entries(summary.unknownReasons).sort((a,b)=>a[0].localeCompare(b[0])));
 const expected=summary.observedStructureCounts;
 need(summary.requestedSymbols===429&&summary.capturedSymbols===429&&
  expected.UNKNOWN===captures.filter(v=>inspect(v,plan).status==='UNKNOWN').length,
  'SUMMARY_COUNTS_DISAGREE');
 return {
  schemaId:SCHEMA,asOfSession:plan.asOfSession,sourceFilesVerified:captures.length,
  originalSourceHashAndPlanPinsVerified:true,
  observedG1Counts:expected,unknownReasons:unknown,
  captureDayCounts:Object.fromEntries(Object.entries(byDay).sort((a,b)=>a[0].localeCompare(b[0]))),
  extraDiagnostics:buckets,
  hypotheticalInvalidRowBypassIsNotAdmissible:true,
  corporateActionsReviewed:false,originalVendorDecimalCertified:false,
  originalFrozenModelModified:false,shadowAuthorized:false,
  productionReady:false,orderTransmission:false
 };
}
export async function diagnose(engineValue,runValue){
 const engine=validPath(engineValue,true),run=validPath(runValue,true);
 need(engine!==run&&!run.startsWith(engine+path.sep),'CAPTURES_MUST_BE_PRIVATE_OUTSIDE_CODE');
 need(path.basename(run).startsWith('weekly-refresh-2026-10-28-'),'EXPECTED_RUN_NAME');
 const planFile=validPath(path.join(run,'plan.json'),false);
 const payload=fs.readFileSync(planFile);
 const plan=JSON.parse(payload.toString('utf8').replace(/^\uFEFF/,''));
 const {planId,...body}=plan;
 need(plan.schemaId==='ARK_NO11_RSS_DAILY_CENSUS_PLAN_V1'&&
  plan.refreshSchemaId==='ARK_NO11_WEEKLY_G1_DAILY_REFRESH_PLAN_V1'&&
  HASH(JSON.stringify(body))===planId&&
  plan.productionReady===false&&plan.orderTransmission===false,'SOURCE_PLAN_HASH_OR_CONTRACT_INVALID');
 const helper=validPath(path.join(engine,'tools/no11_rss_daily_trend_census.mjs'),false);
 const runtime=validPath(path.join(engine,'runtime/no11_rss_daily_trend_census.mjs'),false);
 const h=await import(pathToFileURL(helper).href),v=await import(pathToFileURL(runtime).href);
 need(plan.codeSha256===h.codeIdentity(),'ORIGINAL_CODE_IDENTITY_CHANGED');
 const captures=h.loadCaptures(run,plan);
 const {summary}=v.summarizeDailyCaptures(plan,captures);
 return aggregateUnknownDiagnostics(plan,captures,v.inspectDailyCapture,summary);
}
if(process.argv[1] && path.resolve(process.argv[1])===path.resolve(new URL(import.meta.url).pathname)){
 // comparison by fileURLToPath is done below for Windows; the importable
 // module form intentionally does not run in tests.
}
import {fileURLToPath} from 'node:url';
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 diagnose(...(()=>{const x=exactArgs(process.argv.slice(2));return [x['--engine-root'],x['--run']];})())
 .then(result=>{
  console.log('NO11_D100_DIAG=PRIVATE_RECEIPTS_VERIFIED_READONLY');
  console.log('NO11_D100_DIAG_G1_COUNTS='+JSON.stringify(result.observedG1Counts));
  console.log('NO11_D100_DIAG_UNKNOWN_REASONS='+JSON.stringify(result.unknownReasons));
  console.log('NO11_D100_DIAG_CAPTURE_DAYS='+JSON.stringify(result.captureDayCounts));
  console.log('NO11_D100_DIAG_EXTRA='+JSON.stringify(result.extraDiagnostics));
  console.log('NO11_D100_DIAG_SHADOW=BLOCKED');
  console.log('ORDER_TRANSMISSION=False');
 }).catch(error=>{
  const reason=/^NO11_D100_DIAG_[A-Z0-9_]+$/.test(error?.message)?error.message:
    'NO11_D100_DIAG_INVALID_LOCAL_SOURCE_OR_INPUT';
  console.log('NO11_D100_DIAG=BLOCKED|'+reason);
  console.log('ORDER_TRANSMISSION=False');
  process.exitCode=2;
 });
}
