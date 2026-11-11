import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {inspectDailyCapture,requiredDailySessions,dailyFormula,DAILY_SOURCE_SCHEMA} from '../runtime/no11_rss_daily_trend_census.mjs';
const here=path.dirname(fileURLToPath(import.meta.url));
const candidate=path.resolve(here,'../tools/no11_weekly_g1_refresh.completed-test.mjs');
const {nightlyWindow,nextCashDate,isoFriday}=await import(pathToFileURL(candidate).href);

for(const time of ['00:01','07:00','08:29','08:30','09:00','10:15','12:30','15:20','17:59']){
 test('normal data button Monday '+time+' retains real Friday close',()=>{
  const now='2026-11-09T'+time+':00+09:00';
  const w=nightlyWindow(now);
  assert.equal(w.date,'2026-11-06');
  assert.equal(w.now,now); // no pretend Friday receipt clock
  assert.equal(nextCashDate(w.date),'2026-11-09');
  assert.equal(isoFriday(w.date),true); // original FULL_MARKET_FRIDAY route
  assert.equal(w.daytimeHistoricalRecovery,time>='08:30');
 });
}
test('after finalized Monday switches to real Monday / Tuesday',()=>{
 const w=nightlyWindow('2026-11-09T18:00:00+09:00');
 assert.equal(w.date,'2026-11-09');
 assert.equal(nextCashDate(w.date),'2026-11-10');
 assert.equal(isoFriday(w.date),false);
 assert.equal(w.daytimeHistoricalRecovery,false);
});
test('existing weekend and holiday calendar remain real source dates',()=>{
 for(const now of ['2026-11-07T11:00:00+09:00','2026-11-08T21:00:00+09:00']){
  assert.equal(nightlyWindow(now).date,'2026-11-06');
 }
 const holiday=nightlyWindow('2026-11-03T10:00:00+09:00');
 assert.equal(holiday.date,'2026-11-02');
 assert.equal(nextCashDate(holiday.date),'2026-11-04');
});
test('normal weekday daytime pool marks the genuine observation time',()=>{
 const w=nightlyWindow('2026-11-05T10:00:00+09:00');
 assert.equal(w.date,'2026-11-04');
 assert.equal(nextCashDate(w.date),'2026-11-05');
 assert.equal(w.daytimeHistoricalRecovery,true);
});
test('invalid or non-JST clock is not silently normalized',()=>{
 assert.throws(()=>nightlyWindow('2026-11-09T10:00:00Z'));
 assert.throws(()=>nightlyWindow('2026-99-99T10:00:00+09:00'));
});
function source(){
 const asOfSession='2026-11-06',createdAtJst='2026-11-09T09:10:00+09:00';
 const plan={planId:'a'.repeat(64),symbols:['7203.T'],asOfSession,createdAtJst,
  expectedSessions:requiredDailySessions(asOfSession)};
 const rows=plan.expectedSessions.map((session,index)=>({session,
  open:String(100+index),high:String(101+index),low:String(99+index),
  close:String(100+index),volume:'1000'}));
 const capture={schemaId:DAILY_SOURCE_SCHEMA,planId:plan.planId,symbol:'7203.T',
  formula:dailyFormula('7203.T'),asOfSession,period:'D',orderTransmission:false,
  productionReady:false,priceBasis:'RSS_CHART_UNVERIFIED',decimalProvenance:'EXCEL_VALUE2_ROUNDTRIP',
  corporateActionsCleared:false,originalVendorDecimalCertified:false,
  observedStartJst:createdAtJst,observedEndJst:'2026-11-09T09:10:20+09:00',
  status:'OBSERVED',invalidRows:0,rows};
 return {plan,capture};
}
test('real Monday partial bar never influences Friday G1 classification',()=>{
 const {plan,capture}=source();
 const baseline=inspectDailyCapture(capture,plan);
 const withPartial=inspectDailyCapture({...capture,rows:[...capture.rows,
  {session:'2026-11-09',open:'1',high:'99999999',low:'1',close:'99999999',volume:'1'}]},plan);
 assert.equal(withPartial.ignoredLaterRows,1);
 assert.deepEqual({...withPartial,ignoredLaterRows:0},baseline);
});
test('Monday row does not substitute for a missing Friday close',()=>{
 const {plan,capture}=source();
 const result=inspectDailyCapture({...capture,rows:[...capture.rows.slice(0,-1),
  {session:'2026-11-09',open:'100',high:'101',low:'99',close:'100',volume:'1000'}]},plan);
 assert.equal(result.status,'UNKNOWN');
 assert.equal(result.reason,'REQUIRED_SESSIONS_MISSING');
});
