import fs from 'node:fs';
import path from 'node:path';
import {buildP25ExitV1DiagnosticEvidence,P25_EXIT_V1_DIAGNOSTIC_POLICY} from '../predict/daytrade/phase57-p25-data-driven-exit-diagnostics.js';

function arg(name,fallback=null){const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;}
function writeAtomic(file,value){fs.mkdirSync(path.dirname(file),{recursive:true});const tmp=`${file}.tmp-${process.pid}`;fs.writeFileSync(tmp,JSON.stringify(value,null,2)+'\n');fs.renameSync(tmp,file);}

const input=arg('--input'),output=arg('--output','data/p25-exit-diagnostics/v1.json');
if(!input){console.error('usage: node scripts/analyze_p25_data_driven_exit_v1.mjs --input <paired-json> [--output <json>]');process.exit(2);}
try{
  const source=JSON.parse(fs.readFileSync(input,'utf8'));
  if(source?.methodology?.resultBasedRetuning!==false||source?.result?.methodology?.currentProspectiveOutcomeUsedForFitting!==false)throw new Error('diagnostic source methodology guard failed');
  if(source?.safety?.freshHoldoutConsumed!==false||source?.safety?.executionAllowed!==false||source?.safety?.liveTradingAllowed!==false)throw new Error('diagnostic source safety guard failed');
  const evidence=buildP25ExitV1DiagnosticEvidence(source?.result?.pairs??[]);
  const payload={
    schemaVersion:1,createdAt:new Date().toISOString(),sourcePhase:source?.phase??source?.result?.phase??null,
    sourceLineageManifestHeadSha256:source?.result?.lineageManifestHeadSha256??null,
    sourceAnalogPoolCount:source?.result?.analogPoolCount??null,
    sourcePairedCount:source?.result?.summary?.pairedCount??null,
    methodology:P25_EXIT_V1_DIAGNOSTIC_POLICY,
    evidence,
    safety:{researchOnly:true,executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,freshHoldoutConsumed:false},
  };
  writeAtomic(output,payload);
  console.log(JSON.stringify({status:evidence.status,output,counts:evidence.counts,activeExitDelta:evidence.activeExitDelta,dataDrivenPath:evidence.dataDrivenPath,activeExitPath:evidence.activeExitPath},null,2));
}catch(error){console.error(JSON.stringify({status:'BLOCKED_P25_EXIT_V1_DIAGNOSTICS',error:String(error?.message??error)},null,2));process.exit(1);}
