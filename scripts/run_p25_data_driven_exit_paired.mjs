import fs from 'node:fs';
import path from 'node:path';
import {runP25DataDrivenExitMultisession,P25_DATA_DRIVEN_PAIRED_SAFETY} from '../predict/daytrade/phase57-p25-data-driven-exit-multisession.js';

function arg(name,fallback=null){const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;}
function readJson(file,label){try{return JSON.parse(fs.readFileSync(file,'utf8'));}catch(error){throw new Error(`${label} JSON read failed: ${error?.message??error}`);}}
function writeAtomic(file,value){fs.mkdirSync(path.dirname(file),{recursive:true});const tmp=`${file}.tmp-${process.pid}`;fs.writeFileSync(tmp,JSON.stringify(value,null,2)+'\n');fs.renameSync(tmp,file);}

const historyPath=arg('--history-pack'),captureDir=arg('--capture-dir'),integrityPath=arg('--integrity-ledger'),lineagePath=arg('--lineage-manifest'),sessionDate=arg('--session-date'),outputPath=arg('--output','data/p25-data-driven-exit/paired.json');
if(!historyPath||!captureDir||!integrityPath||!lineagePath){console.error('usage: node scripts/run_p25_data_driven_exit_paired.mjs --history-pack <json> --capture-dir <dir> --integrity-ledger <json> --lineage-manifest <json> [--session-date YYYY-MM-DD] [--output <json>]');process.exit(2);}
try{
  const captureArtifacts=fs.readdirSync(captureDir).filter(x=>x.endsWith('.json')).sort().map(name=>({artifact:readJson(path.join(captureDir,name),`capture ${name}`),artifactPath:name}));
  const result=runP25DataDrivenExitMultisession({historyPack:readJson(historyPath,'history pack'),captureArtifacts,sessionIntegrityLedger:readJson(integrityPath,'integrity ledger'),lineageManifest:readJson(lineagePath,'lineage manifest'),sessionDates:sessionDate?[sessionDate]:null});
  const payload={schemaVersion:1,phase:result.phase,status:result.status,createdAt:new Date().toISOString(),result,methodology:{exactDynamic50Only:true,fixedBaselineUntouched:true,resultBasedRetuning:false,freshHoldoutConsumed:false},safety:P25_DATA_DRIVEN_PAIRED_SAFETY};
  writeAtomic(outputPath,payload);
  console.log(JSON.stringify({status:payload.status,output:outputPath,pairedCount:result.summary.pairedCount,fixed:result.summary.fixed,dataDriven:result.summary.dataDriven,delta:result.summary.delta,safety:P25_DATA_DRIVEN_PAIRED_SAFETY},null,2));
}catch(error){console.error(JSON.stringify({status:'BLOCKED_P25_DATA_DRIVEN_EXIT_PAIRED',error:String(error?.message??error),safety:P25_DATA_DRIVEN_PAIRED_SAFETY},null,2));process.exit(1);}
