import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {DAILY_PLAN_SCHEMA, DAILY_SOURCE_SCHEMA, requiredDailySessions, lastCompletedSession, validInstant,
  parseRequestSymbols, dailyFormula, inspectDailyCapture, summarizeDailyCaptures} from '../runtime/no11_rss_daily_trend_census.mjs';
import {classifyDailySmaStructure, evaluateOriginalSelectorTrendG1} from '../runtime/no11_existing_selector_trend_prefilter.mjs';
import {immutable, loadCaptures, makePlan, codeIdentity} from '../tools/no11_rss_daily_trend_census.mjs';
const base=path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const asOf='2026-10-23', days=requiredDailySessions(asOf), now='2026-10-23T23:00:00.000+09:00';
const plan=(symbols=['7203.T'])=>({schemaId:DAILY_PLAN_SCHEMA,planId:'test-synthetic',createdAtJst:now,asOfSession:asOf,expectedSessions:days,symbols,baselineAdded:[]});
const payload=(symbol='7203.T', values=days.map((_,i)=>String(100+i)))=>({
  schemaId:DAILY_SOURCE_SCHEMA,planId:'test-synthetic',symbol,asOfSession:asOf,period:'D',formula:dailyFormula(symbol),status:'OBSERVED',
  observedStartJst:now,observedEndJst:now,rows:days.map((session,i)=>({session,open:values[i],high:values[i],low:values[i],close:values[i],volume:'100'})),
  invalidRows:0,priceBasis:'RSS_CHART_UNVERIFIED',decimalProvenance:'EXCEL_VALUE2_ROUNDTRIP',corporateActionsCleared:false,originalVendorDecimalCertified:false,
  productionReady:false,orderTransmission:false,
});
const checksum=bytes=>createHash('sha256').update(bytes).digest('hex');

test('76 exchange sessions include current closed day; no invented weekend/holiday rows',()=>{
 assert.equal(days.length,76);assert.equal(days[0],'2026-07-02');assert.equal(days.at(-1),asOf);
 for(const holiday of ['2026-07-20','2026-08-11','2026-09-21','2026-09-22','2026-09-23','2026-10-12'])assert.ok(!days.includes(holiday));
 assert.throws(()=>requiredDailySessions('2026-10-24'),/ASOF_NOT_CASH_SESSION/);
 assert.throws(()=>requiredDailySessions('2025-10-23'),/YEAR_UNPINNED/);
});
test('date rolls at 18:00 conservative policy and weekends/holiday remain correct',()=>{
 assert.equal(lastCompletedSession('2026-10-23T17:59:59+09:00'),'2026-10-22');
 assert.equal(lastCompletedSession('2026-10-23T18:00:00+09:00'),asOf);
 assert.equal(lastCompletedSession('2026-10-24T00:00:00+09:00'),asOf);
 assert.equal(lastCompletedSession('2026-10-13T09:00:00+09:00'),'2026-10-09');
});
test('reject impossible dates/times, not Date.parse normalization',()=>{
 for(const stamp of ['2026-02-30T09:00:00+09:00','2026-10-23T24:00:00+09:00','2026-10-23T09:60:00+09:00','2026-10-23T09:00:00Z'])assert.equal(validInstant(stamp),false);
 assert.equal(validInstant(now),true);
});
test('original request list plus previously excluded 7203, not a new ranked top-K',()=>{
 assert.deepEqual(parseRequestSymbols('\uFEFF1301.T\r\n1332.T\r\n').symbols,['1301.T','1332.T','7203.T']);
 assert.deepEqual(parseRequestSymbols('7203.T\n').baselineAdded,[]);
 assert.throws(()=>parseRequestSymbols('7203.T\n7203.T'),/SYMBOL_LIST_INVALID/);
 assert.throws(()=>parseRequestSymbols('7203.T");BAD('),/SYMBOL_LIST_INVALID/);
 assert.throws(()=>dailyFormula('bad'),/SYMBOL_INVALID/);
 assert.throws(()=>makePlan(Buffer.from('7203.T'),now,codeIdentity()),/ORIGINAL_SYMBOL_LIST_PIN_MISMATCH/);
});
test('diagnostic PASS never fabricates source certification or live admission',()=>{
 const p=payload(), r=summarizeDailyCaptures(plan(),[p]);
 assert.equal(r.summary.observedStructureCounts.PASS,1);assert.equal(r.summary.admittedLiveSymbols,null);
 assert.equal(r.summary.priceBasisCertified,false);assert.equal(r.summary.productionReady,false);
 assert.equal(r.summary.orderTransmission,false);assert.equal(r.summary.capacity.liveCapacityCertified,false);
 assert.equal(evaluateOriginalSelectorTrendG1({instrument:{priceBasis:p.priceBasis,corporateActionsCleared:false,bars:[]},expectedSessions:days,decisionCutoffJst:'2026-10-26T09:30:00+09:00'}).status,'UNKNOWN');
});
test('same shared exact arithmetic as strict gate, original coefficients and timings unchanged',()=>{
 const p=payload();
 const strict=evaluateOriginalSelectorTrendG1({instrument:{priceBasis:'COMPARABLE_RAW',corporateActionsCleared:true,
  bars:p.rows.map(row=>({...row,knownAtJst:now.slice(0,19)+'+09:00'}))},expectedSessions:days,decisionCutoffJst:'2026-10-26T09:30:00+09:00'});
 assert.equal(inspectDailyCapture(p,plan()).status,strict.status);
 assert.deepEqual(inspectDailyCapture(p,plan()).axes,strict.axes);
 assert.equal(summarizeDailyCaptures(plan(),[p]).summary.originalIntradaySelectionScheduleModified,false);
});
test('falling and flat reject, mixed WAIT; tiny positive decimals survive',()=>{
 assert.equal(inspectDailyCapture(payload('7203.T',days.map((_,i)=>String(200-i))),plan()).status,'REJECT');
 assert.equal(inspectDailyCapture(payload('7203.T',days.map(()=>'100')),plan()).status,'REJECT');
 const mixed=days.map((_,i)=>String(100+i));mixed.splice(71,5,'168','167','166','165','164');
 assert.equal(inspectDailyCapture(payload('7203.T',mixed),plan()).status,'WAIT');
 const tiny=days.map((_,i)=>'100.'+String(i+1).padStart(24,'0'));
 assert.equal(classifyDailySmaStructure(tiny).status,'PASS');
});
test('missing session / no trade / duplicate / invalid row => UNKNOWN, never fill-forward',()=>{
 const missing=payload();missing.rows.splice(2,1);assert.equal(inspectDailyCapture(missing,plan()).reason,'REQUIRED_SESSIONS_MISSING');
 const duplicate=payload();duplicate.rows.push({...duplicate.rows[0]});assert.equal(inspectDailyCapture(duplicate,plan()).reason,'DUPLICATE_SESSION');
 const invalid=payload();invalid.invalidRows=1;assert.equal(inspectDailyCapture(invalid,plan()).status,'UNKNOWN');
 const noTrade=payload();noTrade.rows[3].close='0';assert.equal(inspectDailyCapture(noTrade,plan()).reason,'SOURCE_OHLCV_INVALID');
 const footer=payload();footer.rows[3].high='1';assert.equal(inspectDailyCapture(footer,plan()).reason,'SOURCE_OHLCV_INVALID');
});
test('later daily bars cannot enter this historical-close window',()=>{
 const p=payload();p.rows.push({session:'2026-10-26',close:'999999'});
 assert.equal(inspectDailyCapture(p,plan()).status,'PASS');assert.equal(inspectDailyCapture(p,plan()).ignoredLaterRows,1);
});
test('receipt before window closes or before plan, wrong formula/schema/flags => stop',()=>{
 for(const [field,value] of [['observedStartJst','2026-10-23T17:00:00.000+09:00'],['period','1M'],['formula','=BAD()'],['planId','other'],['orderTransmission',true],['priceBasis','COMPARABLE_RAW'],['corporateActionsCleared',true]]){
  const p=payload();p[field]=value;assert.throws(()=>inspectDailyCapture(p,plan()),/CAPTURE_CONTRACT_INVALID/);
 }
});
test('partial coverage cannot masquerade as complete or capacity success',()=>{
 const r=summarizeDailyCaptures(plan(['1301.T','7203.T']),[payload()]);
 assert.equal(r.summary.status,'PARTIAL_OBSERVED_STRUCTURE_ONLY');assert.equal(r.summary.observedStructureCounts.UNKNOWN,1);
 assert.equal(r.summary.capacity.liveCapacityCertified,false);assert.equal(r.summary.capacity.fullMarketBreadthInputResolved,false);
});
test('501 observed passing symbols not silently cut at 500',()=>{
 const symbols=Array.from({length:501},(_,i)=>String(1000+i)+'.T');
 const r=summarizeDailyCaptures(plan(symbols),symbols.map(symbol=>payload(symbol)));
 assert.equal(r.summary.observedStructureCounts.PASS,501);assert.equal(r.details.length,501);
 assert.equal(r.summary.capacity.observedCountExceedsMarketCeiling,true);assert.equal(r.summary.capacity.truncated,false);
});
test('no duplicate response, wrong target or bad calendar',()=>{
 assert.throws(()=>summarizeDailyCaptures(plan(),[payload(),payload()]),/DUPLICATE_CAPTURE/);
 const bad=plan();bad.expectedSessions=days.slice(1);assert.throws(()=>summarizeDailyCaptures(bad,[]),/PLAN_INVALID/);
});
test('source resume hash, immutable write, duplicate/tampered archive detection',()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'no11-daily-'));fs.mkdirSync(path.join(root,'sources'));
 try{
  const bytes=Buffer.from(JSON.stringify(payload())+'\n'), file=path.join(root,'sources','7203.T-'+checksum(bytes)+'.json');
  fs.writeFileSync(file,bytes);assert.equal(loadCaptures(root,plan()).length,1);
  fs.writeFileSync(path.join(root,'sources','crash.pending'),'incomplete');assert.equal(loadCaptures(root,plan()).length,1);
  const receipt=path.join(root,'test.json');immutable(receipt,{a:1});immutable(receipt,{a:1});assert.throws(()=>immutable(receipt,{a:2}));
  fs.appendFileSync(file,' ');assert.throws(()=>loadCaptures(root,plan()),/SOURCE_HASH_OR_IDENTITY_MISMATCH/);
 }finally{fs.rmSync(root,{recursive:true,force:true})}
});
test('no live input objects are mutated',()=>{
 const p=payload(),before=structuredClone(p);summarizeDailyCaptures(plan(),[p]);assert.deepEqual(p,before);
});
test('runner reuses unique visible Ark Excel, one temporary book, no execution writes',()=>{
 const ps=fs.readFileSync(path.join(base,'windows/Run-No11RssDailyTrendCensusReadOnly.ps1'),'utf8');
 assert.match(ps,/AccessibleObjectFromWindow/);assert.match(ps,/MainWindowHandle -ne/);
 assert.match(ps,/\$book\.Close\(\$false\)/);assert.match(ps,/\$existing\+\$BatchSize -gt 50/);
 assert.match(ps,/ALL_EMPTY_WAVE_RETRY_AFTER_RECONNECT/);assert.match(ps,/NO_FULL_HISTORY_IN_WAVE/);
 assert.doesNotMatch(ps,/RssStockOrder|RssCancelOrder|RegisterXLL|\.Save\(|\.SaveAs\(|\.Quit\(|Stop-Process|New-Object -ComObject/i);
 assert.ok([...ps].every(c=>c.charCodeAt(0)<128));
});
test('Windows PowerShell 5 parser and offline self-test without Excel/network', {skip:process.platform!=='win32'},()=>{
 const script=path.join(base,'windows/Run-No11RssDailyTrendCensusReadOnly.ps1');
 const parsed=spawnSync('powershell.exe',['-NoProfile','-Command',`$t=$null;$e=$null;[void][System.Management.Automation.Language.Parser]::ParseFile('${script.replaceAll("'","''")}',[ref]$t,[ref]$e);if($e.Count){$e|Out-String|Write-Output;exit 2}`],{encoding:'utf8',timeout:45000});
 assert.equal(parsed.status,0,parsed.stdout+parsed.stderr);
 const result=spawnSync('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass','-File',script,'-OfflineSelfTest'],{encoding:'utf8',timeout:45000});
 assert.equal(result.status,0,result.stdout+result.stderr);assert.match(result.stdout,/NO11_DAILY_OFFLINE_SELFTEST=PASS/);
});
test('strict gate rejects invalid expected sessions, 24:00 and oversized decimal',()=>{
 const instrument={priceBasis:'COMPARABLE_RAW',corporateActionsCleared:true,bars:payload().rows.map(row=>({...row,knownAtJst:'2026-10-23T23:00:00+09:00'}))};
 assert.throws(()=>evaluateOriginalSelectorTrendG1({instrument,expectedSessions:[...days].reverse(),decisionCutoffJst:'2026-10-26T09:30:00+09:00'}),/EXPECTED_SESSIONS_INVALID/);
 assert.throws(()=>evaluateOriginalSelectorTrendG1({instrument,expectedSessions:days,decisionCutoffJst:'2026-10-26T24:00:00+09:00'}),/DECISION_CUTOFF_INVALID/);
 assert.throws(()=>classifyDailySmaStructure(days.map(()=>'1'.repeat(100))),/CLOSE_WINDOW_INVALID/);
});
