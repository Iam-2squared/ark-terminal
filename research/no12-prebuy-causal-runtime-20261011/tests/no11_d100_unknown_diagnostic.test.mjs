import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {aggregateUnknownDiagnostics,SCHEMA} from '../tools/no11_d100_unknown_diagnostic.mjs';
import {DAILY_SOURCE_SCHEMA,DAILY_PLAN_SCHEMA,dailyFormula,requiredDailySessions,
  inspectDailyCapture,summarizeDailyCaptures}
 from '../runtime/no11_rss_daily_trend_census.mjs';

function fixture(){
 const asOf='2026-10-28',dates=requiredDailySessions(asOf);
 const symbols=Array.from({length:429},(_,i)=>String(1000+i)+'.T');
 const plan={schemaId:DAILY_PLAN_SCHEMA,planId:'test-plan',
  createdAtJst:'2026-10-28T19:00:00.000+09:00',
  asOfSession:asOf,expectedSessions:dates,symbols};
 const rows=dates.map(session=>({session,open:'100',high:'101',
  low:'99',close:'100',volume:'100'}));
 const captures=symbols.map((symbol,i)=>({
  schemaId:DAILY_SOURCE_SCHEMA,planId:plan.planId,symbol,asOfSession:asOf,
  period:'D',formula:dailyFormula(symbol),status:'OBSERVED',
  observedStartJst:i<260?'2026-10-28T20:05:00.000+09:00':'2026-10-29T09:05:00.000+09:00',
  observedEndJst:i<260?'2026-10-28T20:05:03.000+09:00':'2026-10-29T09:05:03.000+09:00',
  rows,invalidRows:1,
  priceBasis:'RSS_CHART_UNVERIFIED',
  decimalProvenance:'EXCEL_VALUE2_ROUNDTRIP',
  corporateActionsCleared:false,originalVendorDecimalCertified:false,
  productionReady:false,orderTransmission:false
 }));
 return {plan,captures};
}
test('429 complete daily date windows can STILL be UNKNOWN due malformed observed extra rows',()=>{
 const {plan,captures}=fixture();
 const {summary}=summarizeDailyCaptures(plan,captures);
 const r=aggregateUnknownDiagnostics(plan,captures,inspectDailyCapture,summary);
 assert.equal(r.schemaId,SCHEMA);
 assert.equal(r.sourceFilesVerified,429);
 assert.deepEqual(r.observedG1Counts,{PASS:0,WAIT:0,REJECT:0,UNKNOWN:429});
 assert.deepEqual(r.unknownReasons,{MALFORMED_SOURCE_ROWS:429});
 assert.equal(r.extraDiagnostics.full76DatesPresent,429);
 assert.equal(r.extraDiagnostics.full76ButUnknown,429);
 assert.equal(r.extraDiagnostics.nonzeroInvalidRows,429);
 assert.equal(r.extraDiagnostics.invalidRowsTotal,429);
 assert.equal(r.extraDiagnostics.conditionalRejectAfterIgnoringInvalidCount,429);
 assert.equal(r.captureDayCounts['2026-10-28'].total,260);
 assert.equal(r.captureDayCounts['2026-10-29'].total,169);
 assert.equal(r.hypotheticalInvalidRowBypassIsNotAdmissible,true);
 assert.equal(r.shadowAuthorized,false);
 assert.equal(r.orderTransmission,false);
 assert.equal(r.productionReady,false);
});
test('missing 76th daily date is UNKNOWN even if no malformed rows were counted',()=>{
 const {plan,captures}=fixture();
 for(const row of captures){row.invalidRows=0;row.rows=row.rows.slice(1);}
 const r=aggregateUnknownDiagnostics(plan,captures,inspectDailyCapture,
   summarizeDailyCaptures(plan,captures).summary);
 assert.equal(r.unknownReasons.REQUIRED_SESSIONS_MISSING,429);
 assert.equal(r.extraDiagnostics.full76DatesPresent,0);
 assert.equal(r.extraDiagnostics.conditionalRejectAfterIgnoringInvalidCount,0);
});
test('diagnostic is local and offline; no broker, Excel or immutable-source changes',()=>{
 const code=readFileSync(new URL('../tools/no11_d100_unknown_diagnostic.mjs',import.meta.url),'utf8');
 for(const marker of [
  'originalSourceHashAndPlanPinsVerified:true',
  'h.loadCaptures(run,plan)',
  'plan.codeSha256===h.codeIdentity()',
  "HASH(JSON.stringify(body))===planId",
  "sourceFilesVerified:captures.length",
  'NO11_D100_DIAG_UNKNOWN_REASONS=',
  'NO11_D100_DIAG_CAPTURE_DAYS=',
  'hypotheticalInvalidRowBypassIsNotAdmissible:true',
  'NO11_D100_DIAG_SHADOW=BLOCKED',
  'ORDER_TRANSMISSION=False'
 ])assert.ok(code.includes(marker),marker);
 assert.doesNotMatch(code,/writeFileSync|mkdirSync|renameSync|unlinkSync|rmSync|fetch\s*\(|RssStockOrder\s*\(|RssCancelOrder\s*\(/);
});
