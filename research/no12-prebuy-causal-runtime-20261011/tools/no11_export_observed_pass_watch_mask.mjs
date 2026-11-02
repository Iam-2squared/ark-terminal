/** Export only the confirmed observed PASS symbols from the existing PC cache.
 * Never run RSS/Excel or inspect account/workbook values. Private output only. */
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {codeIdentity,loadCaptures,immutable} from './no11_rss_daily_trend_census.mjs';
import {makeObservedPassWatchMask} from '../runtime/no11_observed_pass_watch_gate.mjs';
const here=path.dirname(fileURLToPath(import.meta.url));
const repo=path.resolve(here,'../../..');
const hash=x=>createHash('sha256').update(x).digest('hex');
export function exportObservedPassMask(args){
  if(args.length!==2||args[0]!=='--run'||!path.isAbsolute(args[1]))
    throw Error('NO11_DAYPASS_RUN_REQUIRED');
  const run=path.resolve(args[1]);
  if(run===repo||run.startsWith(repo+path.sep))
    throw Error('NO11_DAYPASS_PRIVATE_ROOT_REQUIRED');
  const stat=fs.lstatSync(run);
  if(!stat.isDirectory()||stat.isSymbolicLink())
    throw Error('NO11_DAYPASS_RUN_INVALID');
  const file=path.join(run,'plan.json'),st=fs.lstatSync(file);
  if(!st.isFile()||st.isSymbolicLink()||st.size>4_000_000)
    throw Error('NO11_DAYPASS_PLAN_INVALID');
  const plan=JSON.parse(fs.readFileSync(file,'utf8').replace(/^\uFEFF/,''));
  const {planId,...body}=plan;
  if(hash(JSON.stringify(body))!==planId||plan.codeSha256!==codeIdentity())
    throw Error('NO11_DAYPASS_PIN_MISMATCH');
  const captures=loadCaptures(run,plan);
  const mask=makeObservedPassWatchMask(plan,captures);
  const sourceDir=path.join(run,'sources');
  const sources=fs.readdirSync(sourceDir).filter(s=>s.endsWith('.json')).sort();
  mask.sourceManifestSha256=hash(JSON.stringify(sources));
  const payload=Buffer.from(JSON.stringify(mask)+'\n');
  const out=path.join(run,'no11-observed-pass-watch-'+hash(payload).slice(0,16)+'.json');
  immutable(out,mask);
  // The PASS symbol list itself stays private: only counts + path are printed.
  console.log('NO11_DAILY_PASS_WATCH_OBSERVED='+mask.observedPassCount);
  console.log('NO11_DAILY_PASS_UNKNOWN_SKIPPED='+mask.dataStillUnknown);
  console.log('NO11_DAILY_PASS_WATCH_FILE='+out);
  console.log('NO11_ORIGINAL_SELECTOR_LIVE_CONNECTED=False');
  console.log('ORDER_TRANSMISSION=False');
  return {mask,file:out};
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){
  try{exportObservedPassMask(process.argv.slice(2));}
  catch(err){
    console.error(/^NO11_DAYPASS_/.test(err.message)?err.message:'NO11_DAYPASS_LOCAL_IO_FAILURE');
    process.exitCode=2;
  }
}
