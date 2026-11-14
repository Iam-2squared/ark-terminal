/**
 * Post-capture OFFLINE quality audit for existing No.1.1 RSS daily SMA census.
 * No Excel, RSS, accounts, orders, model fitting or source modifications.
 * Invalid rows lack preserved dates, so no UNKNOWN can be auto-promoted.
 */
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {codeIdentity, immutable, loadCaptures} from './no11_rss_daily_trend_census.mjs';
import {DAILY_PLAN_SCHEMA, inspectDailyCapture, summarizeDailyCaptures} from '../runtime/no11_rss_daily_trend_census.mjs';

const sha = input => createHash('sha256').update(input).digest('hex');
const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '../../..');
const requireCondition = (ok, code) => {
  if (!ok) throw new Error('NO11_DAILY_UNKNOWN_' + code);
};
function readSmallJson(file) {
  const st = fs.lstatSync(file);
  requireCondition(st.isFile() && !st.isSymbolicLink() && st.size < 4_000_000, 'FILE_INVALID');
  return JSON.parse(fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
}
function coverageMetrics(capture, plan) {
  const wanted = new Set(plan.expectedSessions), seen = new Set();
  let duplicateWantedDates = 0, futureDates = 0;
  for (const row of capture.rows) {
    if (row.session > plan.asOfSession) futureDates++;
    if (wanted.has(row.session)) {
      if (seen.has(row.session)) duplicateWantedDates++;
      seen.add(row.session);
    }
  }
  return {
    observedWantedDates: seen.size,
    missingWantedDates: wanted.size - seen.size,
    duplicateWantedDates,
    futureDates,
  };
}
export function diagnoseStoredUnknowns(plan, captures) {
  const {summary} = summarizeDailyCaptures(plan, captures);
  const buckets = {'1':0,'2':0,'3_to_5':0,'6_plus':0};
  const malformed = {
    count:0, withAll76ParsedDates:0, withMissingRequiredDates:0,
    withDuplicateRequiredDates:0, withFutureRows:0, totalInvalidRows:0,
    invalidRowCountBuckets:buckets,
  };
  const privateDetails = [];
  let unavailable=0, otherUnknown=0;
  for (const capture of captures) {
    const result = inspectDailyCapture(capture, plan);
    if (result.reason === 'MALFORMED_SOURCE_ROWS') {
      malformed.count++;
      malformed.totalInvalidRows += capture.invalidRows;
      const metrics = coverageMetrics(capture, plan);
      if (metrics.missingWantedDates === 0 && metrics.duplicateWantedDates === 0)
        malformed.withAll76ParsedDates++;
      if (metrics.missingWantedDates > 0) malformed.withMissingRequiredDates++;
      if (metrics.duplicateWantedDates > 0) malformed.withDuplicateRequiredDates++;
      if (metrics.futureDates > 0) malformed.withFutureRows++;
      const n = capture.invalidRows;
      buckets[n === 1 ? '1' : n === 2 ? '2' : n <= 5 ? '3_to_5' : '6_plus']++;
      privateDetails.push({symbol:capture.symbol, reason:result.reason,
        invalidRows:n,...metrics});
    } else if (result.reason === 'SOURCE_UNAVAILABLE') {
      unavailable++;
      privateDetails.push({symbol:capture.symbol,reason:result.reason});
    } else if (result.status === 'UNKNOWN') {
      otherUnknown++;
      privateDetails.push({symbol:capture.symbol,reason:result.reason});
    }
  }
  const uncaptured=summary.uncapturedSymbols;
  requireCondition(summary.observedStructureCounts.UNKNOWN ===
    malformed.count+unavailable+otherUnknown+uncaptured,'COUNT_INCONSISTENT');
  return {
    report:{
      schemaId:'ARK_NO11_RSS_DAILY_UNKNOWN_OFFLINE_DIAG_V1',
      status:'OBSERVED_SOURCE_DIAGNOSTIC_ONLY',
      planId:plan.planId,
      asOfSession:plan.asOfSession,
      requestedSymbols:summary.requestedSymbols,
      capturedSymbols:summary.capturedSymbols,
      uncapturedSymbols:uncaptured,
      originalStructureCounts:summary.observedStructureCounts,
      capturedUnknown:malformed.count+unavailable+otherUnknown,
      unknownReasons:{
        malformedRows:malformed.count,unavailable,otherCapturedUnknown:otherUnknown,notCaptured:uncaptured,
      },
      malformed,
      strictObservedPassLowerBound:summary.observedStructureCounts.PASS,
      potentialPassUpperBound:summary.observedStructureCounts.PASS+summary.observedStructureCounts.UNKNOWN,
      rssMarketCeiling:500,rssChartFunctionCeiling:50,
      passesCertifiedForLive:0,malformedAutomaticallyPromoted:0,
      exactReceivedAtCertified:false,priceBasisCertified:false,
      corporateActionsCertified:false,nativeMinuteVaResolved:false,
      originalSelectorLiveConnected:false,newModelTraining:false,
      productionReady:false,orderTransmission:false,
      note:'Original capture did not retain dates of invalid rows. Parsed 76/76 does NOT certify a malformed symbol.',
    },privateDetails,
  };
}
export function runUnknownAudit(argv) {
  requireCondition(argv.length === 2 && argv[0] === '--run' && argv[1], 'ARGUMENTS');
  const run=argv[1];
  requireCondition(path.isAbsolute(run),'ROOT_REQUIRED');
  const full=path.resolve(run), st=fs.lstatSync(full);
  requireCondition(st.isDirectory() && !st.isSymbolicLink(),'RUN_DIRECTORY_INVALID');
  requireCondition(full!==repoRoot && !full.startsWith(repoRoot+path.sep),'RUN_IN_REPO_FORBIDDEN');
  const plan=readSmallJson(path.join(full,'plan.json'));
  requireCondition(plan.schemaId===DAILY_PLAN_SCHEMA,'PLAN_SCHEMA');
  const {planId,...body}=plan;
  requireCondition(sha(JSON.stringify(body))===planId,'PLAN_HASH');
  requireCondition(plan.codeSha256===codeIdentity(),'CODE_IDENTITY');
  const captures=loadCaptures(full,plan);
  const {report,privateDetails}=diagnoseStoredUnknowns(plan,captures);
  const names=fs.readdirSync(path.join(full,'sources')).filter(x=>x.endsWith('.json')).sort();
  report.sourceManifestSha256=sha(JSON.stringify(names));
  const detailBytes=Buffer.from(JSON.stringify(privateDetails)+'\n');
  report.privateDetailsSha256=sha(detailBytes);
  immutable(path.join(full,'private-unknown-details-'+report.privateDetailsSha256.slice(0,16)+'.json'),privateDetails);
  const bytes=Buffer.from(JSON.stringify(report)+'\n');
  const reportPath=path.join(full,'no11-daily-unknown-audit-'+sha(bytes).slice(0,16)+'.json');
  immutable(reportPath,report);
  console.log('NO11_DAILY_UNKNOWN_AUDIT='+report.status);
  console.log('NO11_DAILY_UNKNOWN_REASONS='+JSON.stringify(report.unknownReasons));
  console.log('NO11_DAILY_MALFORMED_COVERAGE='+JSON.stringify(report.malformed));
  console.log('NO11_DAILY_UNKNOWN_REPORT='+reportPath);
  console.log('NO11_PRODUCTION_READY=False');
  console.log('ORDER_TRANSMISSION=False');
}
if(process.argv[1] && import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href) {
  try{runUnknownAudit(process.argv.slice(2));}
  catch(error){
    console.error(/^NO11_DAILY_/.test(error.message)?error.message:'NO11_DAILY_UNKNOWN_LOCAL_IO_FAILURE');
    process.exitCode=2;
  }
}
