/**
 * Diagnostic-only Oct 28 No.1.1 REAL-RSS Shadow pre-open gate.
 * No Excel, broker, network, model fitting, order or source mutation.
 * Uses original pinned G1/Chart50 validators; never manufactures missing
 * previous context, EXTERNALLY_REVIEWED evidence or any dated master.
 * All displayed values are aggregate counters or status codes, not holdings,
 * model scores, private stock prices, or symbols.
 */
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {codeIdentity,loadCaptures} from './no11_rss_daily_trend_census.mjs';
import {verifyWeeklyPool} from './no11_weekly_g1_refresh.mjs';
import {DAILY_PLAN_SCHEMA,requiredDailySessions,summarizeDailyCaptures} from '../runtime/no11_rss_daily_trend_census.mjs';
import {makeObservedPassWatchMask} from '../runtime/no11_observed_pass_watch_gate.mjs';
import {validateNo11Chart50Plan} from '../runtime/no11_rss_chart_50_prescreen.mjs';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const PREV='2026-10-27',TARGET='2026-10-28',SEED='2026-10-26';
const SEED_DIR='daily-trend-capture/daily-2026-10-26-e84a2ec53b0fdf41';
const SOURCE='session-reference/2026-10-27/session-reference-10d87dfd162e21cbff34551eb862b4fba0df494ad77f29fce0f309d3cb5653bd.json';
const sha=b=>createHash('sha256').update(b).digest('hex');
const bad=s=>{throw Error('NO11_OCT28_DOCTOR_'+s)};
const need=(v,s)=>{if(!v)bad(s)};
function safePath(p,dir=false){
 need(typeof p==='string'&&path.isAbsolute(p),'ABSOLUTE_PRIVATE_PATH_REQUIRED');
 const full=path.resolve(p);
 need(full!==ROOT&&!full.startsWith(ROOT+path.sep),'PATH_INSIDE_REPO');
 const st=fs.lstatSync(full);
 need((dir?st.isDirectory():st.isFile())&&!st.isSymbolicLink(),'PATH_TYPE_OR_LINK');
 return full;
}
function read(p,max=20_000_000){
 const full=safePath(p),b=fs.readFileSync(full);
 need(b.length>0&&b.length<=max,'SOURCE_SIZE_INVALID');
 return {data:JSON.parse(b.toString('utf8').replace(/^\uFEFF/,'')),bytes:b};
}
function listing(dir,reg){
 if(!fs.existsSync(dir))return [];
 need(fs.lstatSync(dir).isDirectory()&&!fs.lstatSync(dir).isSymbolicLink(),'SOURCE_DIRECTORY_INVALID');
 return fs.readdirSync(dir).filter(s=>reg.test(s)).sort().map(s=>path.join(dir,s));
}
function newest(records,limit){
 need(records.length<=limit,'AMBIGUOUS_TOO_MANY_RECEIPTS');
 if(records.length===0)return null;
 need(records.length===1,'AMBIGUOUS_RECEIPTS_REQUIRE_REVIEW');
 return records[0];
}
function diagRssReference(p){
 if(!fs.existsSync(p))return {status:'NO_SAVED_REFERENCE'};
 const raw=read(p,5_000_000).data;
 need(raw.schemaId==='ARK_NO11_RSS_SESSION_REFERENCE_CAPTURE_V1'&&
  raw.sessionDate===PREV&&raw.orderTransmission===false&&
  Array.isArray(raw.rows)&&raw.rows.length===47,'PREVIOUS_REFERENCE_INVALID');
 const rows=raw.rows;
 const isPrice=x=>typeof x==='number'&&Number.isFinite(x)&&x>0;
 const present={
  marketCodeT:rows.filter(r=>r.marketCode==='T').length,
  marketDateOct27:rows.filter(r=>r.marketDate===PREV).length,
  previousDateOct26:rows.filter(r=>r.previousDate===SEED).length,
  previousClosePositive:rows.filter(r=>isPrice(r.previousClose)).length,
  dayBasePricePositive:rows.filter(r=>isPrice(r.dayBasePrice)).length,
  segmentRecognized:rows.filter(r=>['東証P','東証S','東証G'].includes(r.marketSection)).length,
  lotShares100:rows.filter(r=>r.lotShares===100).length,
 };
 const allValid=Object.values(present).every(x=>x===47);
 return {status:allValid?'RAW_RSS_REFERENCE_FIELDS_PRESENT_NOT_REVIEWED':
     'RAW_RSS_REFERENCE_FIELDS_INCOMPLETE',selected:47,counts:present,
     externalCorporateReview:false};
}
function weeklyStage(local,seed,io,missing){
 const result={status:'NOT_CAPTURED',asOf:PREV,session:TARGET,
   refreshSymbols:0,passCount:0,chartCount:0,mask:null,chart:null,run:null};
 const root=path.join(local,'weekly-pool-refresh');
 const runs=listing(root,/^weekly-refresh-2026-10-27-[a-f0-9]{16}$/);
 if(!runs.length){missing.push('OCT27_FRESH_G1_POOL');return result;}
 const run=newest(runs,2);
 const p=read(path.join(run,'plan.json'),3_000_000).data;
 const {planId,...body}=p;
 need(p.schemaId==='ARK_NO11_WEEKLY_G1_DAILY_REFRESH_PLAN_V1'&&
  p.asOfSession===PREV&&p.codeSha256===codeIdentity()&&
  p.weeklySource?.asOfSession===SEED&&
  p.weeklySource?.originalPlanId===seed.plan.planId&&
  JSON.stringify(p.symbols)===JSON.stringify(seed.mask.observedPassSymbols)&&
  JSON.stringify(p.expectedSessions)===JSON.stringify(requiredDailySessions(PREV))&&
  sha(JSON.stringify(body))===planId,'REFRESH_PLAN_IDENTITY_INVALID');
 result.run=run;result.refreshSymbols=p.symbols.length;
 const observed=loadCaptures(run,p);
 if(observed.length!==p.symbols.length){
  result.status='CAPTURE_INCOMPLETE';missing.push('OCT27_FRESH_G1_POOL');
  return result;
 }
 const count=summarizeDailyCaptures(p,observed);
 need(count.summary.status==='COMPLETE_OBSERVED_STRUCTURE_ONLY','REFRESH_SOURCE_NOT_FULL_OBSERVED');
 const fresh=makeObservedPassWatchMask(p,observed);
 result.passCount=fresh.observedPassCount;
 const masks=listing(run,/^no11-observed-pass-watch-[a-f0-9]{16}\.json$/);
 const charts=listing(run,/^no11-chart50-private-[a-f0-9]{16}\.json$/);
 if(!masks.length||!charts.length){
  result.status='REFRESH_COMPLETE_RECEIPT_MISSING';
  missing.push('OCT28_CHART50_MASK');
  return result;
 }
 const m=read(newest(masks,3),1_000_000).data;
 const c=read(newest(charts,3),1_000_000).data;
 need(m.asOfSession===PREV&&
  JSON.stringify(m.observedPassSymbols)===JSON.stringify(fresh.observedPassSymbols)&&
  m.observedPassCount===fresh.observedPassCount&&
  m.weeklyOriginalAsOfSession===SEED&&m.orderTransmission===false&&
  c.schemaId==='ARK_NO11_CHART50_PRIVATE_EXPORT_RECEIPT_V1'&&
  c.orderTransmission===false&&c.productionReady===false&&
  c.currentRefreshAsOfSession===PREV,'FRESH_MASK_OR_CHART_SCOPE_MISMATCH');
 const selected=validateNo11Chart50Plan({chartPlan:c.chartPlan,mask:m,sessionDate:TARGET});
 result.chartCount=selected.length;result.status='PASS_FRESH_G1_CHART50';
 result.mask=newest(masks,3);result.chart=newest(charts,3);
 return result;
}
function previousStage(local,weekly,missing){
 if(!weekly.chart)return {status:'BLOCKED_UNTIL_NEW_CHART50'};
 const root=path.join(local,'previous-source',TARGET);
 const files=listing(root,/^previous-archive-stage-[a-f0-9]{64}\.json$/);
 if(!files.length){missing.push('OCT27_PREVIOUS_1M_FOR_OCT28');return {status:'NOT_STAGED'};}
 const p=newest(files,3),b=read(p,20_000_000);
 const stage=b.data;
 const wanted=weekly.chart?read(weekly.chart).data.chartPlan.selectorInputSymbols:[];
 need(stage.schemaId==='ARK_NO11_PREVIOUS_ARCHIVE_STAGE_V1'&&
  stage.sessionDate===TARGET&&stage.previousSession===PREV&&
  stage.chartPlanSha256===read(weekly.chart).data.chartPlan.planSha256&&
  stage.orderTransmission===false&&
  [...Object.keys(stage.symbols||{}),...Object.keys(stage.omittedSymbols||{})].length===wanted.length,
  'PREVIOUS_STAGE_SOURCE_MISMATCH');
 const usable=Object.keys(stage.symbols||{}).length;
 const omitted=Object.keys(stage.omittedSymbols||{}).length;
 if(omitted>0)missing.push('OCT27_PREVIOUS_MINUTES_INCOMPLETE');
 return {status:omitted?'PARTIAL_PREVIOUS_BARS':'STAGED_PRICE_ONLY_NOT_CONTEXT',
   usable,missing:omitted,masterCertified:false};
}
function launcher(local,missing){
 const p=path.join(local,'shadow-oneclick-classic','launcher-settings.json');
 if(!fs.existsSync(p)){missing.push('CLASSIC_SHADOW_CONFIG');return {status:'NOT_CONFIGURED'};}
 const s=read(p,100_000).data;
 need(s.schemaId==='ARK_SHADOW_ONECLICK_SETTINGS_V1'&&
  s.orderTransmission===false,'LAUNCHER_SETTINGS_NOT_READONLY');
 const configPath=s.preparedConfigFile||s.bootstrapTemplateFile||'';
 const hasConfig=typeof configPath==='string'&&path.isAbsolute(configPath)&&fs.existsSync(configPath);
 if(!hasConfig)missing.push('ACTUAL_DATED_MASTER_AND_PREPARED_BOOTSTRAP');
 const external=typeof s.securityEvidenceFile==='string'&&
  path.isAbsolute(s.securityEvidenceFile)&&fs.existsSync(s.securityEvidenceFile)&&
  typeof s.evidenceDocumentsDir==='string'&&path.isAbsolute(s.evidenceDocumentsDir)&&
  fs.existsSync(s.evidenceDocumentsDir);
 if(!external)missing.push('INDEPENDENT_SECURITY_REVIEW');
 return {status:hasConfig?'CONFIG_PRESENT_NOT_PREFLIGHTED':'SOURCE_CONFIG_ABSENT',
   externalSourceFilesPresent:external,preflightPassed:false};
}
export function inspect(args){
 need(args.length===2&&args[0]==='--local-root','USAGE');
 const local=safePath(args[1],true);
 const missing=[],seed=verifyWeeklyPool(path.join(local,SEED_DIR));
 need(seed.plan.asOfSession===SEED&&seed.mask.observedPassCount===429,
  'WEEKLY_SEED_CHANGED_FROM_VERIFIED_20261026');
 const recent=diagRssReference(path.join(local,SOURCE));
 const weekly=weeklyStage(local,seed,null,missing);
 const prev=previousStage(local,weekly,missing);
 const settings=launcher(local,missing);
 // Never allow previous-session evidence or a synthetic account to become
 // today's security master, user ownership pin or broker reconciliation.
 missing.push('OCT28_SAME_DAY_RSS_REFERENCE');
 missing.push('OCT28_EXTERNAL_SECURITY_AND_PRICE_BASIS_REVIEW');
 missing.push('OCT28_ACCOUNT_PINS_AND_SIM_ACCOUNT_RECONCILIATION');
 missing.push('OCT28_SAME_DAY_MASTER_AND_PREVIOUS_CONTEXT');
 missing.push('OCT28_ORIGINAL_INTEGRATED_PREFLIGHT');
 return {session:TARGET,seedMarketCount:seed.plan.symbols.length,
  seedObservedPass:seed.mask.observedPassCount,oldOct27ReferenceAudit:recent,
  weeklyRefresh:{status:weekly.status,asOf:weekly.asOf,selected:weekly.chartCount,
    currentPassCount:weekly.passCount,weeklyPopulation:weekly.refreshSymbols},
  previousMinutes:prev,launcher:settings,
  pending:[...new Set(missing)],shadowAtOpen:'NOT_YET_AUTHORIZED',
  marketDataPassDoesNotImplyReview:true,
  didNotOpenExcel:true,modelScored:false,orderTransmission:false};
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){
 try{
  const r=inspect(process.argv.slice(2));
  console.log('NO11_OCT28_DOCTOR_SEED_G1='+r.seedMarketCount+'|PASS='+r.seedObservedPass);
  for(const [key,value] of Object.entries(r.oldOct27ReferenceAudit.counts||{}))
    console.log('NO11_OCT28_PREVIOUS_REFERENCE_'+key.toUpperCase()+'='+value+'/47');
  console.log('NO11_OCT28_DOCTOR_FRESH_G1='+r.weeklyRefresh.status);
  console.log('NO11_OCT28_DOCTOR_CURRENT_G1_PASS='+r.weeklyRefresh.currentPassCount);
  console.log('NO11_OCT28_DOCTOR_CHART50='+r.weeklyRefresh.selected);
  console.log('NO11_OCT28_DOCTOR_PREVIOUS_1M='+r.previousMinutes.status);
  console.log('NO11_OCT28_DOCTOR_CLASSIC_CONFIG='+r.launcher.status);
  for(const name of r.pending)console.log('NO11_OCT28_BLOCKER='+name);
  console.log('NO11_OCT28_FULL_SHADOW=NOT_YET_AUTHORIZED');
  console.log('NO11_OCT28_DATA_FILES_MODIFIED=False');
  console.log('ORDER_TRANSMISSION=False');
 }catch(e){
  const message=/^NO11_OCT28_DOCTOR_[A-Z0-9_]+$/.test(e?.message)?
   e.message:'NO11_OCT28_DOCTOR_PRIVATE_SOURCE_OR_PIN_FAILURE';
  console.log('NO11_OCT28_DOCTOR=BLOCKED|'+message);
  console.log('ORDER_TRANSMISSION=False');process.exitCode=2;
 }
}
