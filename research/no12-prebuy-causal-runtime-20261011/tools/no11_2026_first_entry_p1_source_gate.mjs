#!/usr/bin/env node
/** Stage 4: OFFLINE private State9 as-of → original Frozen P1_Q70 input gate. */
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {
 STAGE4_SCHEMA,FROZEN_ENTRY_BLOB,MASTER_SHA,REQUIRED_GATES,
 gitBlob,sha256,checkFrozenP1Contract,checkPrivateAsOfArchive
} from '../runtime/no11_first_entry_p1_asof_gate.mjs';

const fail=s=>{throw Error(s)};
const requireValue=(ok,s)=>{if(!ok)fail(s)};
const REL='research/persistent-watchlist-uptrend-first-entry-20261003-v2/CORRECTED_LINEAGE_FAST_FREEZE_20261003/P1_Q70_ENTRY_CONTRACT.json';
function readSafe(file,max){
 requireValue(path.isAbsolute(file),'NO11_P1_ABSOLUTE_PATH_REQUIRED');
 const st=fs.lstatSync(file);
 requireValue(st.isFile()&&!st.isSymbolicLink()&&st.size>0&&st.size<=max,
   'NO11_P1_UNSAFE_FILE');
 return fs.readFileSync(file);
}
export async function run({repo,reportPath,masterPath,outDir}){
 requireValue([repo,reportPath,masterPath,outDir].every(path.isAbsolute),
   'NO11_P1_REQUIRED_ABSOLUTE_PATHS');
 const st=fs.lstatSync(outDir);
 requireValue(st.isDirectory()&&!st.isSymbolicLink(),
   'NO11_P1_OUTPUT_DIR_INVALID');
 const frozenRaw=readSafe(path.join(repo,REL),100000);
 requireValue(gitBlob(frozenRaw)===FROZEN_ENTRY_BLOB,
   'NO11_P1_FROZEN_GIT_BLOB_CHANGED');
 const contract=checkFrozenP1Contract(JSON.parse(frozenRaw.toString('utf8')));
 const masterRaw=readSafe(masterPath,250000);
 requireValue(sha256(masterRaw)===MASTER_SHA,'NO11_P1_ORIGINAL_MASTER_SHA_CHANGED');
 const symbols=masterRaw.toString('utf8').replace(/^\uFEFF/,'').trimEnd().split(/\r?\n/);
 const raw=readSafe(reportPath,250000);
 const report=JSON.parse(raw.toString('utf8'));
 const archive=path.join(outDir,report.privateState9AsOfGzipFilename||'');
 requireValue(path.dirname(path.resolve(archive))===path.resolve(outDir),
   'NO11_P1_ASOF_PATH_ESCAPE');
 const coverage=await checkPrivateAsOfArchive({report,archive,masterOrder:symbols});
 const result={
  schemaId:STAGE4_SCHEMA,
  status:'STATE9_ASOF_SOURCE_VERIFIED_FIRST_ENTRY_P1_Q70_NATIVE_BLOCKED',
  stage3ReceiptSha256:sha256(raw),
  privateState9AsOfGzipSha256:report.privateState9AsOfGzipSha256,
  frozenFirstEntry:contract,
  researchState9AsOfCoverage:coverage,
  unresolvedNativeInputCertifications:REQUIRED_GATES,
  actualBrokerFirstSeenCertified:false,
  originalSelectorWatchEventsReproduced:false,
  originalP1FeatureRowsReproduced:0,
  originalP1ScoresComputed:0,
  originalBuyIntentsProduced:0,
  frozen2025ResearchH235UsedFor2026Trading:false,
  originalFrozenFilesModified:false,
  modelTrainingPerformed:false,
  automaticModelPromotion:false,
  productionReady:false,orderTransmission:false
 };
 const payload=Buffer.from(JSON.stringify(result,null,2)+'\n');
 const digest=sha256(payload);
 const target=path.join(outDir,'no11-2026-first-entry-p1-source-gate-'+digest.slice(0,16)+'.json');
 if(fs.existsSync(target)){
  requireValue(readSafe(target,100000).equals(payload),
    'NO11_P1_EXISTING_REPORT_CHANGED');
 }else fs.writeFileSync(target,payload,{flag:'wx',mode:0o600});
 console.log('NO11_FIRST_ENTRY_P1_STAGE4=PASS_SOURCE_AUDIT_NATIVE_BLOCKED');
 console.log('NO11_FIRST_ENTRY_STATE9_ASOF_SYMBOLS='+coverage.state9ResearchSymbols);
 console.log('NO11_FIRST_ENTRY_STATE9_ASOF_TICKS='+coverage.scheduledState9Ticks);
 console.log('NO11_FIRST_ENTRY_ORIGINAL_P1_SCORE_ROWS=0');
 console.log('NO11_FIRST_ENTRY_STAGE4_REPORT='+target);
 console.log('NO11_PRODUCTION_READY=False');
 console.log('ORDER_TRANSMISSION=False');
 return result;
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const args=process.argv.slice(2);
 try{
  requireValue(args.length===8&&args[0]==='--repo'&&
    args[2]==='--state9-report'&&args[4]==='--original-symbols'&&
    args[6]==='--output-dir','NO11_P1_USAGE_INVALID');
  await run({repo:args[1],reportPath:args[3],masterPath:args[5],outDir:args[7]});
 }catch(e){
  const safe=typeof e.message==='string'&&/^NO11_P1_[A-Z0-9_]+$/.test(e.message)
    ?e.message:'NO11_P1_UNEXPECTED_OR_UNVERIFIED_SOURCE';
  console.error('NO11_FIRST_ENTRY_P1_STAGE4=BLOCKED:'+safe);
  console.error('NO11_PRODUCTION_READY=False');
  console.error('ORDER_TRANSMISSION=False');
  process.exitCode=2;
 }
}
