import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {gzipSync} from 'node:zlib';

import {acquireFreshSession} from './lib/phase57-selector-jquants-fresh-session.mjs';

const allocation=JSON.parse(fs.readFileSync(new URL('../predict/research/phase57-selector-jquants-fresh120-allocation.json',import.meta.url),'utf8'));
const SAFETY=allocation.safety;
const sha256=value=>createHash('sha256').update(value).digest('hex');

function allocatedRows(){
  return [
    ...allocation.development.map(sessionDate=>({sessionDate,fold:'DEVELOPMENT'})),
    ...allocation.purgeDevelopmentValidation.map(sessionDate=>({sessionDate,fold:'PURGE'})),
    ...allocation.validation.map(sessionDate=>({sessionDate,fold:'VALIDATION'})),
    ...allocation.purgeValidationOos.map(sessionDate=>({sessionDate,fold:'PURGE'})),
    ...allocation.untouchedOos.map(sessionDate=>({sessionDate,fold:'UNTOUCHED_OOS'})),
  ].sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate));
}

export async function acquireShard({apiKey,shardIndex,shardCount,acquire=acquireFreshSession}={}){
  if(allocation.status!=='FRESH_120_ALLOCATION_FROZEN')throw new Error('Fresh-120 allocation is not frozen');
  if(!Number.isInteger(shardIndex)||!Number.isInteger(shardCount)||shardIndex<0||shardCount<1||shardIndex>=shardCount)throw new Error('invalid shard coordinates');
  const assigned=allocatedRows().filter((_,index)=>index%shardCount===shardIndex);
  const sessionAudits=[],developmentSamples=[],developmentDiagnostics=[];
  for(const [index,item] of assigned.entries()){
    console.error(`FRESH_SHARD_PROGRESS shard=${shardIndex} session=${index+1}/${assigned.length} date=${item.sessionDate} fold=${item.fold}`);
    const result=await acquire({apiKey,date:item.sessionDate,fold:item.fold});
    if(result.structuralAudit.status!=='SESSION_STRUCTURAL_AUDIT_PASS')throw new Error(`structural audit failed for ${item.sessionDate}`);
    sessionAudits.push(result.structuralAudit);
    if(item.fold==='DEVELOPMENT'){
      developmentSamples.push(...result.developmentSamples);
      developmentDiagnostics.push({sessionDate:item.sessionDate,...result.developmentDiagnostics});
    }else if(result.developmentSamples.length||result.developmentDiagnostics!==null){
      throw new Error(`${item.fold} emitted a Development research payload`);
    }
  }
  const core={schemaVersion:1,phase:'57.selector-minimal-hybrid.fresh-acquisition-shard',status:'FRESH_SHARD_ACQUISITION_PASS',
    datasetId:allocation.datasetId,shardIndex,shardCount,assignedSessionCount:assigned.length,
    developmentSessionCount:assigned.filter(row=>row.fold==='DEVELOPMENT').length,
    validationSessionCount:assigned.filter(row=>row.fold==='VALIDATION').length,
    untouchedOosSessionCount:assigned.filter(row=>row.fold==='UNTOUCHED_OOS').length,
    developmentSampleCount:developmentSamples.length,sessionAudits,developmentDiagnostics,
    validationFeaturesGenerated:false,validationLabelsGenerated:false,
    untouchedOosFeaturesGenerated:false,untouchedOosLabelsGenerated:false,untouchedOosScoresGenerated:false,
    rawPersisted:false,secretPersisted:false,safety:SAFETY};
  return Object.freeze({...core,shardSha256:sha256(JSON.stringify(core)),developmentSamples:Object.freeze(developmentSamples)});
}

async function main(){
  const shardIndex=Number(process.env.SHARD_INDEX),shardCount=Number(process.env.SHARD_COUNT);
  const result=await acquireShard({apiKey:process.env.JQUANTS_API_KEY,shardIndex,shardCount});
  const directory=`artifacts/phase57-jquants-fresh-shard-${shardIndex}`;
  fs.mkdirSync(directory,{recursive:true,mode:0o700});
  const samples=result.developmentSamples;
  const audit={...result};delete audit.developmentSamples;
  const auditBytes=JSON.stringify(audit,null,2)+'\n';
  const sampleBytes=samples.map(row=>JSON.stringify(row)).join('\n')+(samples.length?'\n':'');
  fs.writeFileSync(`${directory}/audit.json`,auditBytes,{mode:0o600});
  fs.writeFileSync(`${directory}/audit.sha256`,`${sha256(auditBytes)}  audit.json\n`,{mode:0o600});
  fs.writeFileSync(`${directory}/development-samples.ndjson.gz`,gzipSync(sampleBytes),{mode:0o600});
  fs.writeFileSync(`${directory}/development-samples.sha256`,`${sha256(sampleBytes)}  development-samples.ndjson\n`,{mode:0o600});
  console.log('JQUANTS_FRESH_SHARD_REPORT '+JSON.stringify({status:audit.status,shardIndex,assignedSessionCount:audit.assignedSessionCount,
    developmentSampleCount:audit.developmentSampleCount,shardSha256:audit.shardSha256,rawPersisted:false,secretPersisted:false,
    validationReleased:false,untouchedOosReleased:false,safety:SAFETY}));
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main().catch(error=>{
  const safe=String(error?.message??error).replace(/[A-Za-z0-9_-]{24,}/g,'[REDACTED]');
  console.error(`JQUANTS_FRESH_SHARD_FAIL ${safe}`);process.exitCode=1;
});

export const Phase57FreshShardInternals=Object.freeze({allocatedRows});
