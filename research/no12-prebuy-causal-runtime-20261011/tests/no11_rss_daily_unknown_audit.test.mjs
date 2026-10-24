import test from 'node:test';
import assert from 'node:assert/strict';
import {diagnoseStoredUnknowns} from '../tools/no11_rss_daily_unknown_audit.mjs';
import {DAILY_SOURCE_SCHEMA,DAILY_PLAN_SCHEMA,requiredDailySessions}
  from '../runtime/no11_rss_daily_trend_census.mjs';

const session='2026-10-23';
const expected=requiredDailySessions(session);
const common={
  schemaId:DAILY_SOURCE_SCHEMA,planId:'synthetic-plan',
  asOfSession:session,period:'D',
  observedStartJst:'2026-10-23T19:00:00.000+09:00',
  observedEndJst:'2026-10-23T19:01:00.000+09:00',
  priceBasis:'RSS_CHART_UNVERIFIED',
  decimalProvenance:'EXCEL_VALUE2_ROUNDTRIP',
  corporateActionsCleared:false,originalVendorDecimalCertified:false,
  productionReady:false,orderTransmission:false,
};
const plan=names=>({
  schemaId:DAILY_PLAN_SCHEMA,planId:'synthetic-plan',
  createdAtJst:'2026-10-23T18:00:00.000+09:00',
  asOfSession:session,expectedSessions:expected,
  symbols:names,baselineAdded:[],
});
const rows=()=>expected.map((date,i)=>({
  session:date,open:String(100+i),high:String(101+i),
  low:String(99+i),close:String(100+i),volume:'1000',
}));
const capture=(name,{invalidRows=0,skip=0,status='OBSERVED'}={})=>({
  ...common,symbol:name,
  formula:'=RssChart($A$2:$J$2,"'+name+'","D",100)',
  invalidRows,status,rows:status==='UNAVAILABLE'?[]:rows().slice(skip),
});
test('valid, malformed, unavailable retain separate statuses',()=>{
  const names=['1111.T','2222.T','3333.T'];
  const out=diagnoseStoredUnknowns(plan(names),[
    capture('1111.T'),capture('2222.T',{invalidRows:1}),
    capture('3333.T',{status:'UNAVAILABLE'}),
  ]);
  assert.equal(out.report.originalStructureCounts.PASS,1);
  assert.deepEqual(out.report.unknownReasons,
    {malformedRows:1,unavailable:1,otherCapturedUnknown:0,notCaptured:0});
  assert.equal(out.report.malformed.withAll76ParsedDates,1);
  assert.equal(out.report.passesCertifiedForLive,0);
  assert.equal(out.report.malformedAutomaticallyPromoted,0);
});
test('malformed entries missing expected dates still UNKNOWN',()=>{
  const r=diagnoseStoredUnknowns(plan(['1111.T']),[
    capture('1111.T',{invalidRows:2,skip:3}),
  ]).report;
  assert.equal(r.originalStructureCounts.UNKNOWN,1);
  assert.equal(r.malformed.withMissingRequiredDates,1);
  assert.equal(r.malformed.withAll76ParsedDates,0);
  assert.equal(r.malformed.invalidRowCountBuckets['2'],1);
});
test('future rows, duplicates and missing captures remain visible',()=>{
  const c=capture('1111.T',{invalidRows:6});
  c.rows.push({...c.rows[5]});
  c.rows.push({...c.rows[0],session:'2026-10-26'});
  const r=diagnoseStoredUnknowns(plan(['1111.T','2222.T']),[c]).report;
  assert.equal(r.malformed.withDuplicateRequiredDates,1);
  assert.equal(r.malformed.withFutureRows,1);
  assert.equal(r.unknownReasons.notCaptured,1);
  assert.equal(r.originalStructureCounts.UNKNOWN,2);
  assert.equal(r.malformed.invalidRowCountBuckets['6_plus'],1);
});
test('invalid source provenance rejected before diagnostic',()=>{
  const c=capture('1111.T');
  c.corporateActionsCleared=true;
  assert.throws(()=>diagnoseStoredUnknowns(plan(['1111.T']),[c]),
    /NO11_DAILY_CAPTURE_CONTRACT_INVALID/);
});
test('aggregate receipt never contains private symbols or observed prices',()=>{
  const r=diagnoseStoredUnknowns(plan(['1111.T']),[
    capture('1111.T',{invalidRows:1}),
  ]);
  const reportJson=JSON.stringify(r.report);
  assert.equal(reportJson.includes('1111.T'),false);
  assert.equal(reportJson.includes('"1000"'),false);
  assert.equal(r.privateDetails.length,1);
  assert.equal(r.report.orderTransmission,false);
  assert.equal(r.report.productionReady,false);
});
