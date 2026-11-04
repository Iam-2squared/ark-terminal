/**
 * Verify a historical Oct26 full-universe source by reconstructing the EXACT
 * original five-file daily census codeIdentity from an immutable Git blob.
 *
 * Read-only: no private source changes, no Excel, no orders, no brokerage.
 * This is NOT generic acceptance of a mismatched code pin.
 */
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';

const sha = b => createHash('sha256').update(b).digest('hex');
const gitBlob = b => createHash('sha1')
  .update(Buffer.from('blob '+b.length+'\0','ascii')).update(b).digest('hex');
const FILES=[
  'tools/no11_rss_daily_trend_census.mjs',
  'runtime/no11_rss_daily_trend_census.mjs',
  'runtime/no11_existing_selector_trend_prefilter.mjs',
  'runtime/jpx_cash_calendar_2026_2027.mjs',
  'windows/Run-No11RssDailyTrendCensusReadOnly.ps1'
];
const OLD_WINDOWS_SOURCE_BLOB='b0c3dfa9aba38d07859826f8f787abc7b56f19b9';
function need(ok, code){if(!ok)throw Error('NO11_OCT26_'+code)}
function normalFile(file) {
  const st=fs.lstatSync(file);
  need(st.isFile()&&!st.isSymbolicLink()&&st.size>0&&st.size<4_000_000,
       'INPUT_FILE_UNSAFE');
  return fs.readFileSync(file);
}
export function identity(root, oldBytes=null){
  const list=FILES.map((name,i)=>[name,sha(
    i===FILES.length-1&&oldBytes!==null?oldBytes:
      normalFile(path.join(root,name)))]);
  return sha(Buffer.from(JSON.stringify(list),'utf8'));
}
export async function audit(engine, planFile, legacyFile){
  need(path.isAbsolute(engine)&&path.isAbsolute(planFile)&&
       path.isAbsolute(legacyFile),'ABSOLUTE_PATH_REQUIRED');
  const body=JSON.parse(normalFile(planFile).toString('utf8').replace(/^\uFEFF/,''));
  need(body&&typeof body==='object'&&!Array.isArray(body),'PLAN_OBJECT');
  const {planId,...planBody}=body;
  need(planId===sha(Buffer.from(JSON.stringify(planBody),'utf8')),
       'PLAN_BYTES_OR_HASH_CHANGED');
  const {DAILY_PLAN_SCHEMA,ORIGINAL_SYMBOLS_SHA256}=await import(
    pathToFileURL(path.join(engine,'runtime/no11_rss_daily_trend_census.mjs')).href);
  need(body.schemaId===DAILY_PLAN_SCHEMA&&body.asOfSession==='2026-10-26'&&
       body.sourceSymbolsSha256===ORIGINAL_SYMBOLS_SHA256&&
       Array.isArray(body.symbols)&&body.symbols.length===4328&&
       new Set(body.symbols).size===4328&&
       body.symbols.every(x=>typeof x==='string'&&/^[0-9A-Z]{4}\.T$/.test(x))&&
       body.productionReady===false&&body.orderTransmission===false,
       'OCT26_ORIGINAL_SCOPE_CHANGED');
  const oldBytes=normalFile(legacyFile);
  need(gitBlob(oldBytes)===OLD_WINDOWS_SOURCE_BLOB,
       'HISTORICAL_GIT_BLOB_CHANGED');
  const current=identity(engine);
  const historical=identity(engine,oldBytes);
  const {codeIdentity}=await import(pathToFileURL(
    path.join(engine,'tools/no11_rss_daily_trend_census.mjs')).href);
  need(current===codeIdentity(),'CURRENT_CODE_IDENTITY_INCONSISTENT');
  need(body.codeSha256===historical&&historical!==current,
       'ORIGINAL_CAPTURE_REVISION_NOT_VERIFIED');
  return {
    schemaId:'ARK_NO11_OCT26_ORIGINAL_SOURCE_CODE_ATTESTATION_V1',
    status:'HISTORIC_2026_10_26_PROVEN',
    historicalCodeSha256:historical,
    currentCodeDifferent:true,
    planIdMatches:true,
    originalSymbols:4328,
    historicalWindowsBlobVerified:true,
    productionReady:false,
    orderTransmission:false
  };
}
if(process.argv[1]&&pathToFileURL(path.resolve(process.argv[1])).href===import.meta.url){
  if(process.argv[2]==='--self-test'){
    need(sha(Buffer.from('abc'))===
      'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad',
      'SELFTEST_HASH');
    console.log('NO11_OCT26_ATTESTATION_SELFTEST=PASS');
    console.log('ORDER_TRANSMISSION=False');
  }else{
    try{
      need(process.argv.length===5,'ARGUMENT_COUNT');
      console.log(JSON.stringify(await audit(...process.argv.slice(2))));
    }catch(e){
      const code=/^NO11_OCT26_[A-Z0-9_]+$/.test(String(e.message))?
        e.message:'NO11_OCT26_UNVERIFIED_LOCAL_SOURCE';
      console.error(code);
      console.error('ORDER_TRANSMISSION=False');
      process.exitCode=2;
    }
  }
}
