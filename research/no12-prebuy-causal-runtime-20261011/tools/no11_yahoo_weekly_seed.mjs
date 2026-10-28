/**
 * Optional research-only Yahoo weekly source builder and verifier.
 * Does not scrape; reads local immutable yfinance output explicitly captured
 * by the separate opt-in helper. Source provenance is NEVER re-labeled RSS.
 * Unofficial price basis remains uncertified; independent security/corporate
 * action review and original integrated Shadow preflight still mandatory.
 */
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {verifyWeeklyPool} from './no11_weekly_g1_refresh.mjs';
import {requiredDailySessions,ORIGINAL_SYMBOLS_SHA256,validInstant,jstNow}
  from '../runtime/no11_rss_daily_trend_census.mjs';
import {classifyDailySmaStructure}
  from '../runtime/no11_existing_selector_trend_prefilter.mjs';
import {isJpxCashTradingDay} from '../runtime/jpx_cash_calendar_2026_2027.mjs';
import {OBSERVED_PASS_GATE_ID} from '../runtime/no11_observed_pass_watch_gate.mjs';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
export const YAHOO_SEED_SCHEMA='ARK_NO11_YAHOO_WEEKLY_SOURCE_PLAN_V1';
export const YAHOO_OBSERVATION_SCHEMA='ARK_NO11_YAHOO_WEEKLY_HISTORY_OBSERVATION_V1';
export const YAHOO_SOURCE='YFINANCE_UNOFFICIAL_PERSONAL_RESEARCH_DAILY';
const SYMBOL=/^[0-9A-Z]{4}\.T$/;
const PRICE=/^(?:0|[1-9]\d*)(?:\.\d+)?$/;
const hash=x=>createHash('sha256').update(x).digest('hex');
const fail=s=>{throw Error('NO11_YAHOO_SEED_'+s)};
const need=(x,s)=>{if(!x)fail(s)};
function privatePath(value,dir=false){
 need(typeof value==='string'&&path.isAbsolute(value),'ABSOLUTE_PRIVATE_PATH');
 const full=path.resolve(value);
 need(full!==ROOT&&!full.startsWith(ROOT+path.sep),'SOURCE_IN_REPOSITORY');
 let p=full;
 while(true){
  if(fs.existsSync(p))need(!fs.lstatSync(p).isSymbolicLink(),'SOURCE_SYMLINK');
  const parent=path.dirname(p);if(parent===p)break;p=parent;
 }
 const stat=fs.statSync(full);
 need((dir?stat.isDirectory():stat.isFile())&&
   (dir||stat.size>0&&stat.size<8_000_000),'SOURCE_TYPE_OR_SIZE');
 return full;
}
function read(filename){
 const full=privatePath(filename);
 const bytes=fs.readFileSync(full);
 return {value:JSON.parse(bytes.toString('utf8').replace(/^\uFEFF/,'')),bytes};
}
function immutable(filename,data){
 const bytes=Buffer.from(JSON.stringify(data)+'\n');
 if(fs.existsSync(filename)){
  need(fs.readFileSync(filename).equals(bytes),'IMMUTABLE_SOURCE_CHANGED');
 }else fs.writeFileSync(filename,bytes,{flag:'wx'});
 return hash(bytes);
}
function timestamp(s){
 return validInstant(s)&&Number.isFinite(Date.parse(s))?Date.parse(s):NaN;
}
export function assessYahooSymbol(payload,expected,asOf){
 // The G1 rule is the ORIGINAL 5/15/25/75 daily SMA arithmetic. There
 // is no "adjusted close" substitution, guessed decimal or future-day row.
 need(payload?.schemaId===YAHOO_OBSERVATION_SCHEMA&&
  payload.sourceProvider===YAHOO_SOURCE&&payload.asOfSession===asOf&&
  payload.sourceInterval==='1d'&&payload.autoAdjustRequested===false&&
  payload.usesYahooCloseNotAdjClose===true&&
  payload.corporateActionPriceBasisCertified===false&&
  payload.splitAdjustmentCertified===false&&
  payload.originalVendorDecimalCertified===false&&
  payload.productionReady===false&&payload.orderTransmission===false&&
  Number.isFinite(timestamp(payload.requestedAtJst))&&
  Number.isFinite(timestamp(payload.receivedAtJst))&&
  timestamp(payload.receivedAtJst)>=timestamp(payload.requestedAtJst)&&
  timestamp(payload.requestedAtJst)>=Date.parse(asOf+'T19:00:00+09:00')&&
  Array.isArray(payload.rows)&&payload.rows.length<=180&&
  ['OBSERVED','UNAVAILABLE'].includes(payload.status),
  'YAHOO_UNOFFICIAL_SOURCE_CONTRACT_INVALID');
 if(payload.status==='UNAVAILABLE'){
  need(payload.rows.length===0,'UNAVAILABLE_WITH_DATA');
  return {status:'UNKNOWN',reason:'YAHOO_SOURCE_UNAVAILABLE'};
 }
 need(payload.rows.length>0,'OBSERVED_WITHOUT_DATA');
 const wanted=new Set(expected),values=new Map();
 for(const row of payload.rows){
  need(row&&typeof row.session==='string'&&
   isJpxCashTradingDay(row.session)&&row.session<=asOf&&
   typeof row.close==='string'&&PRICE.test(row.close)&&
   Number.isFinite(Number(row.close))&&Number(row.close)>0,
   'YAHOO_DAILY_PRICE_INVALID');
  if(!wanted.has(row.session))continue;
  need(!values.has(row.session),'DUPLICATE_DAILY_SESSION');
  values.set(row.session,row.close);
 }
 if(values.size!==expected.length)return {status:'UNKNOWN',reason:'REQUIRED_76_SESSIONS_UNAVAILABLE'};
 return classifyDailySmaStructure(expected.map(d=>values.get(d)));
}
function namesAndAssessment(folder,symbols,asOf){
 const expected=requiredDailySessions(asOf),dir=privatePath(path.join(folder,'sources'),true);
 const names=fs.readdirSync(dir).sort();
 need(names.length===symbols.length,'SOURCE_FILES_NOT_FULL_4328');
 const expectedSet=new Set(symbols),seen=new Set(),status=new Map();
 for(const name of names){
  const match=name.match(/^([0-9A-Z]{4})_T-([a-f0-9]{64})\.json$/);
  need(match,'SOURCE_FILENAME');
  const symbol=match[1]+'.T';
  need(expectedSet.has(symbol)&&!seen.has(symbol),'FOREIGN_OR_DUPLICATE_SYMBOL');
  seen.add(symbol);
  const file=read(path.join(dir,name));
  need(hash(file.bytes)===match[2]&&file.value.symbol===symbol,'SOURCE_HASH_OR_SYMBOL');
  status.set(symbol,assessYahooSymbol(file.value,expected,asOf));
 }
 need(seen.size===symbols.length,'UNOBSERVED_SYMBOLS');
 const counts={PASS:0,WAIT:0,REJECT:0,UNKNOWN:0},passed=[];
 for(const symbol of symbols){
  const result=status.get(symbol);
  counts[result.status]++;
  if(result.status==='PASS')passed.push(symbol);
 }
 need(passed.length>=1&&passed.length<=500,'G1_PASS_OUTSIDE_MARKET_500');
 need(counts.UNKNOWN<=Math.floor(symbols.length/10),'YAHOO_UNKNOWN_COVERAGE_EXCEEDS_10_PERCENT');
 return {expected,counts,passed,manifest:hash(JSON.stringify(names))};
}
export function assessYahooUniverse({asOf,symbols,payloads}){
 need(typeof asOf==='string'&&Array.isArray(symbols)&&
  symbols.length===payloads.length,'SYNTHETIC_TEST_INPUT_INVALID');
 const expected=requiredDailySessions(asOf),counts={PASS:0,WAIT:0,REJECT:0,UNKNOWN:0},passed=[];
 for(let i=0;i<symbols.length;i++){
  need(SYMBOL.test(symbols[i])&&payloads[i].symbol===symbols[i],'SYMBOL_MISMATCH');
  const status=assessYahooSymbol(payloads[i],expected,asOf).status;
  counts[status]++;
  if(status==='PASS')passed.push(symbols[i]);
 }
 return {counts,passed};
}
function planBody(weekly,asOf,observation){
 return {
  schemaId:YAHOO_SEED_SCHEMA,sourceProvider:YAHOO_SOURCE,
  asOfSession:asOf,createdAtJst:jstNow(),expectedSessions:observation.expected,
  originalRssSeedRun:weekly.run,originalRssPlanId:weekly.plan.planId,
  originalFullUniverseCount:weekly.plan.symbols.length,
  sourceSymbolsSha256:ORIGINAL_SYMBOLS_SHA256,
  sourceFilesManifestSha256:observation.manifest,
  symbols:[...weekly.plan.symbols],
  sourceMethod:'OPT_IN_UNOFFICIAL_PERSONAL_RESEARCH_DAILY_HISTORY',
  closeColumn:'Close',autoAdjustRequested:false,
  yahooSplitAdjustmentCertified:false,priceBasisCertified:false,
  corporateActionsCertified:false,originalVendorDecimalCertified:false,
  originalFrozenG1RulesModified:false,productionReady:false,orderTransmission:false
 };
}
function derivedMask(plan,scan){
 return {
  schemaId:OBSERVED_PASS_GATE_ID,asOfSession:plan.asOfSession,planId:plan.planId,
  source:'YAHOO_UNOFFICIAL_WEEKLY_G1_PROVISIONAL_NOT_RSS',
  sourceProvider:YAHOO_SOURCE,
  sourceManifestSha256:scan.manifest,
  observedPassSymbols:scan.passed,observedPassCount:scan.passed.length,
  originalFullUniverseCount:plan.symbols.length,
  unknownCount:scan.counts.UNKNOWN,weeklyStatusCounts:scan.counts,
  strictNoUnknownFallback:true,originalIntradayTop5SchedulePreserved:true,
  originalSelectorMarketBreadthResolved:false,minuteVaResolved:false,
  priceBasisCertified:false,corporateActionsCertified:false,
  originalSelectorExecuted:false,shadowOnly:true,
  productionReady:false,orderTransmission:false
 };
}
function seedRoot(folder){
 const seed=privatePath(folder,true);
 const m=path.basename(seed).match(/^yahoo-weekly-(20\d{2}-\d{2}-\d{2})-([0-9a-f]{16})$/);
 need(m,'YAHOO_SEED_FOLDER_INVALID');
 need(new Date(m[1]+'T00:00:00Z').getUTCDay()===5&&
  isJpxCashTradingDay(m[1]),'YAHOO_FRIDAY_CASH_DATE_REQUIRED');
 return {seed,asOf:m[1],originalPrefix:m[2]};
}
function validatePlan(plan,weekly,asOf,folder,manifest){
 const {planId,...body}=plan;
 need(plan.schemaId===YAHOO_SEED_SCHEMA&&
  plan.sourceProvider===YAHOO_SOURCE&&plan.asOfSession===asOf&&
  plan.originalRssSeedRun===weekly.run&&
  plan.originalRssPlanId===weekly.plan.planId&&
  plan.originalFullUniverseCount===4328&&
  plan.sourceSymbolsSha256===ORIGINAL_SYMBOLS_SHA256&&
  plan.sourceFilesManifestSha256===manifest&&
  JSON.stringify(plan.symbols)===JSON.stringify(weekly.plan.symbols)&&
  JSON.stringify(plan.expectedSessions)===JSON.stringify(requiredDailySessions(asOf))&&
  plan.closeColumn==='Close'&&plan.autoAdjustRequested===false&&
  plan.yahooSplitAdjustmentCertified===false&&
  plan.priceBasisCertified===false&&plan.corporateActionsCertified===false&&
  plan.originalVendorDecimalCertified===false&&
  plan.originalFrozenG1RulesModified===false&&
  plan.productionReady===false&&plan.orderTransmission===false&&
  planId===hash(JSON.stringify(body))&&
  timestamp(plan.createdAtJst)>=Date.parse(asOf+'T19:00:00+09:00')&&
  timestamp(plan.createdAtJst)<=Date.now(),
  'YAHOO_WEEKLY_PLAN_PROVENANCE_INVALID');
}
export function buildYahooWeeklySeed(folder,originalRun){
 const {seed,asOf,originalPrefix}=seedRoot(folder);
 const weekly=verifyWeeklyPool(privatePath(originalRun,true));
 need(weekly.plan.planId.startsWith(originalPrefix),'ORIGINAL_PLAN_PIN_MISMATCH');
 const scan=namesAndAssessment(seed,weekly.plan.symbols,asOf);
 const planFile=path.join(seed,'plan.json');
 const plan=fs.existsSync(planFile)?read(planFile).value:
  (()=>{const body=planBody(weekly,asOf,scan);
    const plan={planId:hash(JSON.stringify(body)),...body};
    immutable(planFile,plan);return plan})();
 validatePlan(plan,weekly,asOf,seed,scan.manifest);
 const mask=derivedMask(plan,scan);
 const bytes=Buffer.from(JSON.stringify(mask)+'\n');
 const maskFile=path.join(seed,'yahoo-weekly-pass-'+hash(bytes).slice(0,16)+'.json');
 immutable(maskFile,mask);
 return {run:seed,plan,mask,maskFile,counts:scan.counts};
}
export function verifyYahooWeeklySeed(folder){
 const {seed,asOf,originalPrefix}=seedRoot(folder);
 const plan=read(path.join(seed,'plan.json')).value;
 const weekly=verifyWeeklyPool(privatePath(plan.originalRssSeedRun,true));
 need(weekly.plan.planId.startsWith(originalPrefix),'ORIGINAL_PLAN_PIN_MISMATCH');
 const scan=namesAndAssessment(seed,weekly.plan.symbols,asOf);
 validatePlan(plan,weekly,asOf,seed,scan.manifest);
 const derived=derivedMask(plan,scan);
 const masks=fs.readdirSync(seed).filter(n=>/^yahoo-weekly-pass-[a-f0-9]{16}\.json$/.test(n));
 need(masks.length===1,'WEEKLY_MASK_MISSING_OR_AMBIGUOUS');
 const saved=read(path.join(seed,masks[0]));
 need(hash(saved.bytes).startsWith(masks[0].slice(18,34))&&
  JSON.stringify(saved.value)===JSON.stringify(derived),
  'WEEKLY_MASK_NOT_DERIVED_FROM_YAHOO_SOURCE');
 return {run:seed,plan,mask:derived,sourceProvider:YAHOO_SOURCE};
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){
 try{
  const args=process.argv.slice(2);
  need(args[0]==='build'&&args.length===5&&args[1]==='--source-run'&&
   args[3]==='--original-rss-seed','USAGE');
  const r=buildYahooWeeklySeed(args[2],args[4]);
  console.log('NO11_YAHOO_WEEKLY_SEED=PASS_PROVISIONAL_NOT_TRADE_CERTIFIED');
  console.log('NO11_YAHOO_WEEKLY_ASOF='+r.plan.asOfSession);
  console.log('NO11_YAHOO_WEEKLY_G1_PASS='+r.mask.observedPassCount);
  console.log('NO11_YAHOO_WEEKLY_UNKNOWN='+r.counts.UNKNOWN);
  console.log('NO11_YAHOO_WEEKLY_SOURCE_RUN='+r.run);
  console.log('NO11_YAHOO_WEEKLY_MASK='+r.maskFile);
  console.log('NO11_YAHOO_WEEKLY_CORPORATE_ACTION_REVIEW=NOT_PERFORMED');
  console.log('ORDER_TRANSMISSION=False');
 }catch(e){
  console.log('NO11_YAHOO_WEEKLY_SEED=BLOCKED|'+
   (/^NO11_(?:YAHOO_SEED|WEEKLY|DAILY|DAYPASS)_[A-Z0-9_]+$/.test(e?.message)?
     e.message:'NO11_YAHOO_SEED_PRIVATE_SOURCE_OR_PROVENANCE_FAILED'));
  console.log('ORDER_TRANSMISSION=False');process.exitCode=2;
 }
}
