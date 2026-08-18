import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {collectP252Routine5mSession,PHASE57_P25_2J_SAFETY} from '../predict/daytrade/phase57-p25-2j-routine-nonrss-5m-source.js';

function arg(name,fallback=null){const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;}
function sha(bytes){return crypto.createHash('sha256').update(bytes).digest('hex');}
function jstToday(){
  const parts=Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date()).map(x=>[x.type,x.value]));
  return `${parts.year}-${parts.month}-${parts.day}`;
}
function parseUniverseFile(file){
  const bytes=fs.readFileSync(file),text=bytes.toString('utf8').trim();
  if(!text)return {records:[],sha256:sha(bytes)};
  let records;
  try{
    const parsed=JSON.parse(text);
    records=Array.isArray(parsed)?parsed:(Array.isArray(parsed?.records)?parsed.records:[parsed]);
  }catch{
    records=text.split(/\r?\n/).filter(Boolean).map((line,index)=>{
      try{return JSON.parse(line);}catch(error){throw new Error(`universe NDJSON line ${index+1} invalid: ${error?.message??error}`);}
    });
  }
  return {records,sha256:sha(bytes)};
}

const universePath=arg('--universe-file');
const sessionDate=arg('--session-date',jstToday());
const outputPath=arg('--output',`data/p25-day-5m-${sessionDate}.json`);
if(!universePath){
  console.error('usage: node scripts/capture_p25_routine_5m.mjs --universe-file <json-or-ndjson> [--session-date YYYY-MM-DD] [--output <json>]');
  process.exit(2);
}

try{
  if(!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate))throw new Error('--session-date must be YYYY-MM-DD');
  const universe=parseUniverseFile(universePath);
  const matches=universe.records.filter(record=>record?.ready===true&&String(record?.sessionDate??'')===sessionDate);
  if(matches.length!==1)throw new Error(`expected exactly one ready frozen universe record for ${sessionDate}, found ${matches.length}`);
  const universeRecord=matches[0];
  const collection=await collectP252Routine5mSession({universeRecord});
  const payload={
    schemaVersion:1,
    phase:'57.p25.2j.routine-nonrss-5m-source-cli',
    status:collection.status,
    createdAt:new Date().toISOString(),
    expectedSessionDates:[sessionDate],
    sessions:collection.ready?[{
      sessionDate,
      universeRecord,
      sessionBarsBySymbol:collection.sessionBarsBySymbol,
      sourceProvenance:{
        ...collection.sourceProvenance,
        universeFileSha256:universe.sha256,
      },
    }]:[],
    collection:{
      ready:collection.ready,
      sessionDate:collection.sessionDate,
      targetSymbolCount:collection.targetSymbolCount,
      collectedSymbolCount:collection.collectedSymbolCount,
      failedSymbolCount:collection.failedSymbolCount,
      failures:collection.failures,
      sourceBySymbol:collection.sourceBySymbol,
      sourceProvenance:collection.sourceProvenance,
    },
    methodology:{
      routineDailyMarketSpeedRequired:false,
      excelRequired:false,
      boardOrTickUsed:false,
      fullFrozenTargetUnionRequired:true,
      failedSymbolBlocksSession:true,
      marketSpeedVerificationSeparate:true,
      freshHoldoutConsumed:false,
    },
    safety:PHASE57_P25_2J_SAFETY,
  };
  fs.mkdirSync(path.dirname(outputPath),{recursive:true});
  const tmp=`${outputPath}.tmp-${process.pid}`;
  fs.writeFileSync(tmp,JSON.stringify(payload,null,2)+'\n','utf8');
  fs.renameSync(tmp,outputPath);
  const outputSha256=sha(fs.readFileSync(outputPath));
  console.log(JSON.stringify({status:payload.status,output:outputPath,outputSha256,sessionDate,ready:collection.ready,targetSymbolCount:collection.targetSymbolCount,collectedSymbolCount:collection.collectedSymbolCount,failedSymbolCount:collection.failedSymbolCount,dailyMarketSpeedRequired:false,safety:PHASE57_P25_2J_SAFETY},null,2));
  if(!collection.ready)process.exitCode=1;
}catch(error){
  console.error(JSON.stringify({status:'BLOCKED_P25_ROUTINE_5M_CAPTURE',error:String(error?.message??error),sessionDate,safety:PHASE57_P25_2J_SAFETY},null,2));
  process.exit(1);
}
