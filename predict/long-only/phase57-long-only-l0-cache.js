import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {assembleLongOnlyL0Rows,TIMESTAMP_CONTRACT} from './phase57-long-only-integrated-dataset.js';

const sha=value=>createHash('sha256').update(value).digest('hex');
const developmentPartitions=new Set(['DEVELOPMENT_A','DEVELOPMENT_B']);

function readVerifiedPages({sessionDir,kind,expected}){
  const file=path.join(sessionDir,`${kind}-pages.json`);
  if(!fs.existsSync(file))throw new Error(`missing immutable cache object: ${file}`);
  const pages=JSON.parse(fs.readFileSync(file,'utf8'));
  if(!Array.isArray(pages)||pages.length!==expected?.pageCount)throw new Error(`immutable cache page count mismatch: ${file}`);
  for(const page of pages){
    if(typeof page?.responseText!=='string'||sha(page.responseText)!==page.responseSha256)throw new Error(`immutable cache page hash mismatch: ${file}`);
  }
  const aggregateSha256=sha(JSON.stringify(pages.map(page=>page.responseSha256)));
  if(aggregateSha256!==expected.aggregateSha256)throw new Error(`immutable cache aggregate hash mismatch: ${file}`);
  return {rows:pages.flatMap(page=>JSON.parse(page.responseText).data??[]),aggregateSha256};
}

export function loadFormalL0PartitionFromCache({cacheRoot,partition,plan,allocation}={}){
  if(!developmentPartitions.has(partition))throw new Error('Formal L0 cache loader may open Development A/B only');
  const sessions=allocation?.partitions?.[partition];
  if(!Array.isArray(sessions)||!sessions.length)throw new Error('partition is absent from frozen allocation');
  const base=path.resolve(String(cacheRoot??''),'phase57-long-only','raw','jquants-v2');
  const dailyRows=[],masterRows=[],source=[];
  for(const sessionDate of sessions){
    const sessionDir=path.join(base,sessionDate),manifestPath=path.join(sessionDir,'l0-manifest.json');
    if(!fs.existsSync(manifestPath))throw new Error(`missing L0 manifest: ${sessionDate}`);
    const manifest=JSON.parse(fs.readFileSync(manifestPath,'utf8'));
    if(manifest.sessionDate!==sessionDate||manifest.partition!==partition)throw new Error(`L0 manifest identity mismatch: ${sessionDate}`);
    const daily=readVerifiedPages({sessionDir,kind:'daily',expected:manifest.daily});
    const master=readVerifiedPages({sessionDir,kind:'master',expected:manifest.master});
    dailyRows.push(...daily.rows);masterRows.push(...master.rows);
    source.push({sessionDate,manifestSha256:manifest.manifestSha256,dailySha256:daily.aggregateSha256,masterSha256:master.aggregateSha256});
  }

  let warmupDailyRows=[];
  if(partition==='DEVELOPMENT_A'){
    const sessionDate=plan?.l0Contract?.causalWarmup?.sessionDate,sessionDir=path.join(base,sessionDate),manifestPath=path.join(sessionDir,'l0-warmup-manifest.json');
    if(!fs.existsSync(manifestPath))throw new Error(`missing causal warmup manifest: ${sessionDate}`);
    const manifest=JSON.parse(fs.readFileSync(manifestPath,'utf8'));
    if(manifest.sessionDate!==sessionDate||manifest.evaluationPartition!==false)throw new Error('causal warmup manifest identity mismatch');
    const daily=readVerifiedPages({sessionDir,kind:'daily',expected:manifest.daily});
    warmupDailyRows=daily.rows;
    source.unshift({sessionDate,evaluationPartition:false,manifestSha256:manifest.manifestSha256,dailySha256:daily.aggregateSha256});
  }else{
    const allSessions=Object.values(allocation.partitions).flat(),firstIndex=allSessions.indexOf(sessions[0]),priorSession=allSessions[firstIndex-1];
    if(firstIndex<1||!priorSession)throw new Error('Development B causal predecessor is unavailable');
    const sessionDir=path.join(base,priorSession),manifest=JSON.parse(fs.readFileSync(path.join(sessionDir,'l0-manifest.json'),'utf8'));
    const daily=readVerifiedPages({sessionDir,kind:'daily',expected:manifest.daily});
    warmupDailyRows=daily.rows;
    source.unshift({sessionDate:priorSession,evaluationPartition:false,manifestSha256:manifest.manifestSha256,dailySha256:daily.aggregateSha256});
  }

  const prepared=assembleLongOnlyL0Rows({dailyRows,masterRows,warmupDailyRows});
  const resultSessions=new Set(prepared.rows.map(row=>row.sessionDate));
  if(resultSessions.size!==sessions.length||sessions.some(session=>!resultSessions.has(session)))throw new Error('Formal L0 admission lost one or more evaluation sessions');
  const sourceSha256=sha(JSON.stringify(source));
  return Object.freeze({schemaVersion:1,partition,rows:prepared.rows,admissionAudit:prepared.audit,sourceManifest:Object.freeze({sourceIdentity:'J_QUANTS_V2_DAILY_PLUS_DATED_MASTER_PRIVATE_IMMUTABLE_CACHE',sourceSha256,timestampContract:TIMESTAMP_CONTRACT,sourceSessions:Object.freeze(source)})});
}

export default {loadFormalL0PartitionFromCache};
