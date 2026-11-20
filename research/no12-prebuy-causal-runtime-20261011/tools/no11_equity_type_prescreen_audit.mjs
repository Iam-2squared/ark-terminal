/**
 * Post-G1 / pre-Chart50 security-product eligibility audit. NO orders, NO
 * executable chart plan and NO independently reviewed securities master.
 *
 * Strictly pinned actual 429-D100 daily refresh -> G1 ranking -> original
 * Chart50 -> captured previous 1m rows. Produces only a PRIVATE proposed
 * replacement list with 5 JPX-confirmed ETF/ETN exclusions, plus a worklist
 * that explicitly leaves every remaining symbol NOT_REVIEWED.
 *
 * A futures-linked ETF/ETN is not a common share even for a cash-only BUY.
 * Source: https://www.jpx.co.jp/news/1070/20200424-01.html (4 oil codes)
 *         https://www.jpx.co.jp/equities/products/etfs/issues/01.html
 * The exclusion set is intentionally NOT a complete eligibility verifier.
 */
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {verifyWeeklyShadowScope} from './no11_verified_weekly_shadow_scope.mjs';
import {loadCaptures} from './no11_rss_daily_trend_census.mjs';
import {rankVerifiedG1PassForChartBudget,validateNo11Chart50Plan}
  from '../runtime/no11_rss_chart_50_prescreen.mjs';

export const AUDIT_SCHEMA='ARK_NO11_PROVISIONAL_EQUITY_TYPE_PRESCREEN_V1';
export const JPX_CONFIRMED_EXCLUDED=Object.freeze([
  '1671.T','1690.T','1699.T','2014.T','2038.T'
]);
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const sha=b=>createHash('sha256').update(b).digest('hex');
const fail=code=>{throw Error('NO11_EQUITY_TYPE_'+code)};
const need=(ok,code)=>{if(!ok)fail(code)};
function real(p,kind='file'){
  need(typeof p==='string'&&path.isAbsolute(p),'ABSOLUTE_PRIVATE_PATH_REQUIRED');
  const full=path.resolve(p);
  need(full!==ROOT&&!full.startsWith(ROOT+path.sep),'REPO_SOURCE_NOT_PRIVATE');
  let cursor=full;
  while(true){
    const st=fs.lstatSync(cursor);
    need(!st.isSymbolicLink(),'SYMLINK_REJECTED');
    const parent=path.dirname(cursor);
    if(parent===cursor)break;
    cursor=parent;
  }
  const st=fs.lstatSync(full);
  need(kind==='dir'?st.isDirectory():st.isFile(),'INPUT_TYPE_INVALID');
  if(kind==='file')need(st.size>0&&st.size<=20_000_000,'INPUT_SIZE_INVALID');
  return full;
}
function json(p){
  const bytes=fs.readFileSync(real(p));
  return {value:JSON.parse(bytes.toString('utf8').replace(/^\uFEFF/,'')),bytes};
}
function protectedSources(chart){
  return [...new Set(chart.protectedChartSymbols)];
}
export function computeEquityTypePreview({chartPlan,mask,ranked,stage,sourceDigest}){
  need(chartPlan&&typeof chartPlan==='object'&&mask&&Array.isArray(ranked)
       &&stage&&typeof stage==='object','INPUT_CONTRACT');
  const selected=validateNo11Chart50Plan({
    chartPlan,mask,sessionDate:chartPlan.sessionDate});
  need(stage.schemaId==='ARK_NO11_PREVIOUS_ARCHIVE_STAGE_V1'&&
       stage.sessionDate===chartPlan.sessionDate&&
       stage.previousSession===chartPlan.asOfSession&&
       stage.chartPlanSha256===chartPlan.planSha256&&
       Array.isArray(stage.selectedSymbols)&&
       JSON.stringify(stage.selectedSymbols)===JSON.stringify(selected)&&
       stage.productionReady===false&&stage.orderTransmission===false,
       'PREVIOUS_ARCHIVE_IDENTITY_OR_MODE');
  const original=new Set(mask.observedPassSymbols);
  const blocked=new Set(JPX_CONFIRMED_EXCLUDED);
  need(ranked.length===original.size&&new Set(ranked.map(x=>x.symbol)).size===original.size&&
    ranked.every(x=>original.has(x.symbol)&&Number.isFinite(x.minMarginPct)&&x.minMarginPct>0&&
      Number.isFinite(x.meanMarginPct)&&x.meanMarginPct>0),
    'PINNED_G1_RANKING_REQUIRED');
  const sort=(a,b)=>b.minMarginPct-a.minMarginPct||
    b.meanMarginPct-a.meanMarginPct||a.symbol.localeCompare(b.symbol);
  const ranks=[...ranked].sort(sort);
  const pinned=protectedSources(chartPlan),protectedSet=new Set(pinned);
  const expectedOriginal=ranks.filter(x=>!protectedSet.has(x.symbol))
    .slice(0,chartPlan.scanChartSymbols.length).map(x=>x.symbol);
  need(JSON.stringify(expectedOriginal)===JSON.stringify(chartPlan.scanChartSymbols),
    'ORIGINAL_CHART_RANKING_MISMATCH');
  const available=stage.symbols||{},omitted=stage.omittedSymbols||{};
  need(typeof available==='object'&&available!==null&&!Array.isArray(available)&&
       typeof omitted==='object'&&omitted!==null&&!Array.isArray(omitted)&&
       Object.keys(available).length+Object.keys(omitted).length===selected.length&&
       selected.every(s=>(Object.hasOwn(available,s)!==Object.hasOwn(omitted,s)))&&
       !Object.keys(available).some(s=>!selected.includes(s))&&
       !Object.keys(omitted).some(s=>!selected.includes(s)),
       'PREVIOUS_ARCHIVE_COVERAGE');
  const excludedOriginal=selected.filter(s=>blocked.has(s));
  const blockedPinned=pinned.filter(s=>blocked.has(s));
  // Existing protected slots remain physically pinned for possible EXIT
  // monitoring, never interpreted as permission to BUY.
  const alternativeScan=ranks.filter(x=>!blocked.has(x.symbol)&&
    !protectedSet.has(x.symbol))
    .slice(0,chartPlan.scanChartSymbols.length).map(x=>x.symbol);
  const alternativeSelected=[...pinned.filter(s=>original.has(s)&&!blocked.has(s)),
    ...alternativeScan];
  const replacement=alternativeSelected.filter(s=>!selected.includes(s));
  const missingPrevious=alternativeSelected.filter(s=>!Object.hasOwn(available,s));
  const remainingUnreviewed=ranks.filter(x=>!blocked.has(x.symbol)).map(x=>x.symbol);
  need(replacement.every(s=>!blocked.has(s))&&
       alternativeSelected.every(s=>original.has(s)&&!blocked.has(s))&&
       new Set(alternativeSelected).size===alternativeSelected.length&&
       alternativeSelected.length<=chartPlan.arkChartsUsed,
       'PROPOSAL_CONTAINS_EXCLUDED_OR_DUPLICATE');
  need(typeof sourceDigest==='string'&&/^[a-f0-9]{64}$/.test(sourceDigest),'SOURCE_DIGEST');
  return Object.freeze({
    schemaId:AUDIT_SCHEMA,
    status:'PROVISIONAL_REVIEW_REQUIRED_NOT_A_TRADING_PLAN',
    sessionDate:chartPlan.sessionDate,previousSession:chartPlan.asOfSession,
    sourceChartPlanSha256:chartPlan.planSha256,
    sourceStageSha256:sourceDigest,
    originalG1PassCount:ranks.length,
    originalSelectedCount:selected.length,
    knownExcludedFromOriginal:excludedOriginal,
    knownExcludedPinnedForExitOnly:blockedPinned,
    knownExcludedFromG1:ranks.filter(x=>blocked.has(x.symbol)).map(x=>x.symbol),
    provisionalReplacementCandidates:replacement,
    provisionalSelectedAfterKnownExclusions:alternativeSelected,
    provisionalSelectedCount:alternativeSelected.length,
    replacementPriorArchiveMissing:missingPrevious,
    unknownEligibilitySymbols:remainingUnreviewed,
    unreviewedG1Count:remainingUnreviewed.length,
    originalChartPlanUnmodified:true,
    previousArchiveUnmodified:true,
    actualCommonEquityIndependentlyReviewed:false,
    corporateActionsCleared:false,
    priceBasisVerified:false,
    executableChartPlanProduced:false,
    permitsBuy:false,
    productionReady:false,
    orderTransmission:false
  });
}
function csvEncode(value){return '"'+String(value).replace(/"/g,'""')+'"'}
function reviewCsv(report,originalSelected){
  const selected=new Set(originalSelected);
  const blocked=new Set(report.knownExcludedFromG1);
  const rows=[['Symbol','Status','OriginalChartSelected','ProvisionalAfterKnownExclusion',
    'InstrumentReview','CorporateActionReview','PriceBasisReview','OfficialSource']];
  const after=new Set(report.provisionalSelectedAfterKnownExclusions);
  for(const symbol of [...blocked,...report.unknownEligibilitySymbols].sort()){
    rows.push([symbol,blocked.has(symbol)?'JPX_CONFIRMED_NON_COMMON_EQUITY':'NOT_REVIEWED',
      selected.has(symbol)?'YES':'NO',after.has(symbol)?'PROVISIONAL_ONLY':'NO',
      blocked.has(symbol)?'ETF_OR_ETN':'NOT_REVIEWED',
      'NOT_REVIEWED','NOT_REVIEWED',
      blocked.has(symbol)?'https://www.jpx.co.jp/news/1070/20200424-01.html':'']);
  }
  return rows.map(cols=>cols.map(csvEncode).join(',')).join('\r\n')+'\r\n';
}
function immutableOutput(dest,bytes){
  const file=path.resolve(dest);
  need(!file.startsWith(ROOT+path.sep)&&file!==ROOT,'OUTPUT_MUST_BE_PRIVATE');
  if(fs.existsSync(file)){
    need(fs.lstatSync(file).isFile()&&!fs.lstatSync(file).isSymbolicLink()&&
      fs.readFileSync(file).equals(bytes),'EXISTING_OUTPUT_CHANGED');
    return;
  }
  fs.writeFileSync(file,bytes,{flag:'wx',mode:0o600});
}
export function readOnlyAudit({seedDir,dailyRun,maskFile,chartFile,stageFile,outputRoot}){
  const output=real(outputRoot,'dir');
  const verified=verifyWeeklyShadowScope({
    runDir:dailyRun,seedDir,maskFile,chartFile,
    sessionDate:json(chartFile).value.chartPlan.sessionDate});
  const run=real(dailyRun,'dir');
  const daily=json(path.join(run,'plan.json')).value;
  const captures=loadCaptures(run,daily);
  const mask=json(maskFile).value,chart=json(chartFile).value;
  const stage=json(stageFile);
  need(chart.chartPlan.planSha256===json(chartFile).value.chartPlan.planSha256&&
    verified.selectedCount===chart.chartPlan.selectorInputSymbols.length,
    'ORIGINAL_SCOPE_MISMATCH');
  const ranked=rankVerifiedG1PassForChartBudget(daily,captures,mask);
  const report=computeEquityTypePreview({
    chartPlan:chart.chartPlan,mask,ranked,stage:stage.value,
    sourceDigest:sha(stage.bytes)});
  // Hash-addressed, local-only. This is not an executable Chart50 plan.
  const bytes=Buffer.from(JSON.stringify(report,null,2)+'\n','utf8');
  const stem=sha(bytes).slice(0,16);
  const result=path.join(output,'equity-type-provisional-'+stem+'.json');
  const worklist=path.join(output,'review-G1-PENDING-'+stem+'.csv');
  immutableOutput(result,bytes);
  immutableOutput(worklist,Buffer.from(reviewCsv(report,chart.chartPlan.selectorInputSymbols),'utf8'));
  return {...report,reportFile:result,worklistFile:worklist};
}
function args(argv){
  const keys=['--seed-dir','--daily-run','--mask','--chart','--previous-stage','--output-root'];
  need(argv.length===keys.length*2,'USAGE');
  const got={};
  for(let i=0;i<argv.length;i+=2){
    need(keys.includes(argv[i])&&!Object.hasOwn(got,argv[i])&&argv[i+1],'ARGUMENT');
    got[argv[i]]=argv[i+1];
  }
  need(keys.every(k=>got[k]),'USAGE');
  return got;
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){
  try{
    const o=args(process.argv.slice(2));
    const r=readOnlyAudit({seedDir:o['--seed-dir'],dailyRun:o['--daily-run'],
      maskFile:o['--mask'],chartFile:o['--chart'],
      stageFile:o['--previous-stage'],outputRoot:o['--output-root']});
    console.log('NO11_EQUITY_TYPE_PRESCREEN=PASS_AUDIT_ONLY');
    console.log('NO11_EQUITY_TYPE_G1_PASS='+r.originalG1PassCount);
    console.log('NO11_EQUITY_TYPE_ORIGINAL_CHART='+r.originalSelectedCount);
    console.log('NO11_EQUITY_TYPE_JPX_KNOWN_EXCLUDED='+r.knownExcludedFromOriginal.length);
    console.log('NO11_EQUITY_TYPE_PROVISIONAL_SELECTED='+r.provisionalSelectedCount);
    console.log('NO11_EQUITY_TYPE_EXTRA_PREVIOUS_MISSING='+r.replacementPriorArchiveMissing.length);
    console.log('NO11_EQUITY_TYPE_UNKNOWN_G1='+r.unreviewedG1Count);
    console.log('NO11_EQUITY_TYPE_REPORT='+r.reportFile);
    console.log('NO11_EQUITY_TYPE_WORKLIST='+r.worklistFile);
    console.log('NO11_EQUITY_TYPE_PREVIEW_IS_NOT_TRADEABLE=True');
    console.log('EXCEL_TOUCHED=False');
    console.log('ORDER_TRANSMISSION=False');
  }catch(e){
    const reason=String(e?.message||'');
    console.log('NO11_EQUITY_TYPE_PRESCREEN=BLOCKED|'+(
      /^NO11_(EQUITY_TYPE|WEEKLY_SHADOW|WEEKLY|DAYPASS|DAILY|CHART50)_[A-Z0-9_]+$/.test(reason)?
      reason:'NO11_EQUITY_TYPE_PRIVATE_SOURCE_OR_RUNTIME_FAILURE'));
    console.log('ORDER_TRANSMISSION=False');process.exitCode=2;
  }
}
