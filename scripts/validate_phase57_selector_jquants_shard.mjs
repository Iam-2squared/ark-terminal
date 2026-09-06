import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {gzipSync} from 'node:zlib';

import {evaluateFreshValidationSession} from './lib/phase57-selector-jquants-fresh-session.mjs';

const allocation=JSON.parse(fs.readFileSync(new URL('../predict/research/phase57-selector-jquants-fresh120-allocation.json',import.meta.url),'utf8'));
const sha256=value=>createHash('sha256').update(value).digest('hex');

function findFiles(root,name){const found=[];for(const entry of fs.readdirSync(root,{withFileTypes:true})){const target=path.join(root,entry.name);if(entry.isDirectory())found.push(...findFiles(target,name));else if(entry.name===name)found.push(target);}return found.sort();}

export async function validateShard({apiKey,inputRoot,shardIndex,shardCount,evaluate=evaluateFreshValidationSession}={}){
  const modelFiles=findFiles(inputRoot,'model.json'),freezeFiles=findFiles(inputRoot,'freeze.json'),auditFiles=findFiles(inputRoot,'audit.json');
  if(modelFiles.length!==1||freezeFiles.length!==1||auditFiles.length!==6)throw new Error('Validation inputs are incomplete');
  const model=JSON.parse(fs.readFileSync(modelFiles[0],'utf8')),freeze=JSON.parse(fs.readFileSync(freezeFiles[0],'utf8'));
  if(freeze.status!=='MINIMAL_HYBRID_FROZEN_BEFORE_VALIDATION'||freeze.modelDigest!==model.modelDigest)throw new Error('Hybrid was not frozen before Validation');
  const audits=auditFiles.flatMap(file=>JSON.parse(fs.readFileSync(file,'utf8')).sessionAudits);
  const byDate=new Map(audits.map(row=>[row.sessionDate,row]));
  const dates=allocation.validation.filter((_,index)=>index%shardCount===shardIndex),records=[],points=[],sessionReports=[];
  for(const [index,date] of dates.entries()){
    console.error(`VALIDATION_SHARD_PROGRESS shard=${shardIndex} session=${index+1}/${dates.length} date=${date}`);
    const result=await evaluate({apiKey,date,expectedAudit:byDate.get(date),model});
    records.push(...result.records);points.push(...result.points);
    sessionReports.push({sessionDate:date,status:result.status,recordCount:result.records.length,decisionCount:result.points.length,structuralHashesVerified:result.structuralHashesVerified});
  }
  return {status:'FROZEN_HYBRID_VALIDATION_SHARD_COMPLETE',shardIndex,shardCount,dates,modelDigest:model.modelDigest,freezeSha256:freeze.freezeSha256,
    records,points,sessionReports,validationReleased:true,untouchedOosReleased:false,untouchedOosPayloadRequested:false,safety:allocation.safety};
}

async function main(){
  const shardIndex=Number(process.env.SHARD_INDEX),shardCount=Number(process.env.SHARD_COUNT);
  const result=await validateShard({apiKey:process.env.JQUANTS_API_KEY,inputRoot:process.env.INPUT_ROOT||'artifacts/phase57-validation-input',shardIndex,shardCount});
  const directory=`artifacts/phase57-jquants-validation-shard-${shardIndex}`;fs.mkdirSync(directory,{recursive:true,mode:0o700});
  const records=result.records,points=result.points,report={...result};delete report.records;delete report.points;
  const writeGzip=(name,rows)=>{const text=rows.map(row=>JSON.stringify(row)).join('\n')+(rows.length?'\n':'');fs.writeFileSync(`${directory}/${name}.ndjson.gz`,gzipSync(text),{mode:0o600});fs.writeFileSync(`${directory}/${name}.sha256`,`${sha256(text)}  ${name}.ndjson\n`,{mode:0o600});};
  writeGzip('validation-records',records);writeGzip('validation-points',points);
  const bytes=JSON.stringify(report,null,2)+'\n';fs.writeFileSync(`${directory}/validation-shard.json`,bytes,{mode:0o600});fs.writeFileSync(`${directory}/validation-shard.sha256`,`${sha256(bytes)}  validation-shard.json\n`,{mode:0o600});
  console.log('PHASE57_VALIDATION_SHARD_REPORT '+JSON.stringify({status:report.status,shardIndex,sessionCount:report.dates.length,recordCount:records.length,decisionCount:points.length,modelDigest:report.modelDigest,untouchedOosReleased:false,safety:report.safety}));
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main().catch(error=>{console.error(`PHASE57_VALIDATION_SHARD_FAIL ${String(error?.message??error)}`);process.exitCode=1;});

export const Phase57ValidationShardInternals=Object.freeze({findFiles});
