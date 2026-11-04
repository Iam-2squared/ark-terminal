/**
 * Reconstruct the ACTUAL Windows CRLF codeIdentity used by the 2026-10-26 RSS
 * original capture from five immutable Git files at commit f959767c.
 *
 * Read-only. Does NOT change any capture, plan, ledger or trading permission.
 * A matching Git revision is necessary but insufficient for trading; the
 * downstream original full-4328 + Friday-429 receipt checks must also pass.
 */
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';

const HISTORICAL_ID='e84a2ec53b0fdf41a8f65b678e2e82562a4fda1054d8fbe42cba856e2d42513d';
const FILES=[
  ['tools/no11_rss_daily_trend_census.mjs','6e236da5508c6cc3e07f8b7b50fe5a59c74614f6','65e89975eb2d6bc0ee7f150281b7621d558860bd812ecb061eca85c4407c2b84'],
  ['runtime/no11_rss_daily_trend_census.mjs','9c052abfe941c8f9727ab024b4f0504a01daeb60','575c32c9777a5429bd5af2955815ccdab4b7c15600826d696213b99c2ebc194d'],
  ['runtime/no11_existing_selector_trend_prefilter.mjs','1814678b7ed01f72e7270148104a7e612169a27a','020128134f0d99e55e0a1a6146b674473a4e4226976fba6768aa5fde6a36a849'],
  ['runtime/jpx_cash_calendar_2026_2027.mjs','147897940596e38674ffe949f9d1a5f4b3be17b2','8598328c6d6fc35bf486699e556859b07fdd30244eca3c661cbe3433115d6207'],
  ['windows/Run-No11RssDailyTrendCensusReadOnly.ps1','acedf14ce7e5bc1ca39906227e2cb0abb0343592','1de58adcbd0a3eb1e8627797bff867493c16a52c2d71f68353241527bc21648e']
];
const sha256=b=>createHash('sha256').update(b).digest('hex');
const sha1=b=>createHash('sha1').update(b).digest('hex');
const gitBlob=b=>sha1(Buffer.concat([Buffer.from('blob '+b.length+'\0','ascii'),b]));
const fail=s=>{throw Error('NO11_OCT26_WIN_ATTEST_'+s)};
const need=(ok,s)=>{if(!ok)fail(s)};
function readRegular(filename,limit=4_000_000){
  need(path.isAbsolute(filename),'ABSOLUTE_PATH');
  const stat=fs.lstatSync(filename);
  need(stat.isFile()&&!stat.isSymbolicLink()&&stat.size>0&&stat.size<=limit,'FILE_UNSAFE');
  return fs.readFileSync(filename);
}
function archivedIdentity(downloadRoot){
  const values=FILES.map(([name,expectedGit,expectedCrLf])=>{
    const raw=readRegular(path.join(downloadRoot,name));
    need(gitBlob(raw)===expectedGit,'ARCHIVED_GIT_BLOB_CHANGED');
    need(!raw.includes(13)&&!raw.subarray(0,3).equals(Buffer.from([0xef,0xbb,0xbf])),
         'ARCHIVED_LINE_ENDING_UNEXPECTED');
    const win=Buffer.from(raw.toString('utf8').replace(/\n/g,'\r\n'),'utf8');
    need(sha256(win)===expectedCrLf,'ARCHIVED_WINDOWS_CHECKOUT_HASH_CHANGED');
    return [name,sha256(win)];
  });
  const identity=sha256(Buffer.from(JSON.stringify(values),'utf8'));
  need(identity===HISTORICAL_ID,'HISTORICAL_REVISION_ID_CHANGED');
  return identity;
}
function plan(filename){
  const b=JSON.parse(readRegular(filename).toString('utf8').replace(/^\uFEFF/,''));
  need(b&&typeof b==='object'&&!Array.isArray(b),'PLAN_OBJECT');
  const {planId,...body}=b;
  need(typeof planId==='string'&&sha256(Buffer.from(JSON.stringify(body),'utf8'))===planId,
       'PLAN_ID_OR_BODY_CHANGED');
  return b;
}
export async function attest(engine,oct26Plan,fridayRun,downloads){
  need(path.isAbsolute(engine)&&path.isAbsolute(fridayRun)&&
       path.isAbsolute(downloads),'ABSOLUTE_INPUTS_REQUIRED');
  const historical=archivedIdentity(downloads);
  const original=plan(oct26Plan);
  const runtime=await import(pathToFileURL(
    path.join(engine,'runtime/no11_rss_daily_trend_census.mjs')).href);
  need(original.schemaId===runtime.DAILY_PLAN_SCHEMA&&
       original.asOfSession==='2026-10-26'&&
       original.sourceSymbolsSha256===runtime.ORIGINAL_SYMBOLS_SHA256&&
       original.codeSha256===historical&&
       original.productionReady===false&&original.orderTransmission===false&&
       Array.isArray(original.symbols)&&original.symbols.length===4328&&
       new Set(original.symbols).size===4328&&
       original.symbols.every(s=>typeof s==='string'&&/^[0-9A-Z]{4}\.T$/.test(s)),
       'ORIGINAL_PLAN_SCOPE_OR_IDENTITY_CHANGED');
  const friday=plan(path.join(fridayRun,'plan.json'));
  need(friday.asOfSession==='2026-10-30'&&
       friday.symbols?.length===429&&
       friday.weeklySource?.originalPlanId===original.planId&&
       friday.initialLiveCandidateScope===
          'FRIDAY_RSS_429_LOCKED_POOL_ONLY_NOT_FULL_MARKET'&&
       friday.productionReady===false&&friday.orderTransmission===false,
       'FRIDAY_PLAN_OR_LINEAGE_CHANGED');
  const {codeIdentity}=await import(pathToFileURL(
    path.join(engine,'tools/no11_rss_daily_trend_census.mjs')).href);
  const current=codeIdentity();
  need(friday.codeSha256===historical||friday.codeSha256===current,
       'FRIDAY_CODE_REVISION_UNRECOGNIZED');
  return {status:'VERIFIED_2026_10_26_WINDOWS_CHECKOUT',
    historicalCodeSha256:historical,
    originalPlanIdSha256Verified:true,
    originalSymbols:4328,
    fridayPlanIdSha256Verified:true,
    fridaySymbols:429,
    fridayCodeIsHistorical:friday.codeSha256===historical,
    currentCodeIdentityDifferent:current!==historical,
    productionReady:false,orderTransmission:false};
}
function selftest(){
  need(sha256(Buffer.from('abc'))===
       'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad',
       'SHA256_SELFTEST');
  need(sha256(Buffer.from(JSON.stringify(
       FILES.map(([name,,win])=>[name,win]))))===HISTORICAL_ID,
       'ARCHIVED_IDENTITY_SELFTEST');
  console.log('NO11_OCT26_WIN_ATTEST_SELFTEST=PASS');
  console.log('ORDER_TRANSMISSION=False');
}
if(process.argv[1]&&pathToFileURL(path.resolve(process.argv[1])).href===import.meta.url){
  if(process.argv[2]==='--self-test'){selftest();}
  else{
    try{
      need(process.argv.length===6,'ARGUMENT_COUNT');
      const evidence=await attest(...process.argv.slice(2));
      console.log(JSON.stringify(evidence));
    }catch(e){
      const code=/^NO11_OCT26_WIN_ATTEST_[A-Z0-9_]+$/.test(e.message)?
        e.message:'NO11_OCT26_WIN_ATTEST_UNVERIFIED_RUNTIME';
      console.error(code);
      console.error('ORDER_TRANSMISSION=False');
      process.exitCode=2;
    }
  }
}
