import fs from 'node:fs';
import path from 'node:path';
import {buildP252FrozenDaySessionLedger,PHASE57_P25_2E_SAFETY} from '../predict/daytrade/phase57-p25-2e-frozen-day-session-ledger.js';

function arg(name,fallback=null){
  const index=process.argv.indexOf(name);
  return index>=0&&index+1<process.argv.length?process.argv[index+1]:fallback;
}
function readJson(file,label){
  let text;
  try{text=fs.readFileSync(file,'utf8');}catch(error){throw new Error(`${label} read failed: ${error?.message??error}`);}
  try{return JSON.parse(text);}catch(error){throw new Error(`${label} JSON failed: ${error?.message??error}`);}
}
function readNdjson(file,label){
  let text;
  try{text=fs.readFileSync(file,'utf8');}catch(error){throw new Error(`${label} read failed: ${error?.message??error}`);}
  return text.split(/\r?\n/).map(x=>x.trim()).filter(Boolean).map((line,index)=>{
    try{return JSON.parse(line);}catch(error){throw new Error(`${label} NDJSON line ${index+1} failed: ${error?.message??error}`);}
  });
}
function jsonFiles(directory){
  const root=path.resolve(directory);
  if(!fs.existsSync(root))throw new Error(`phase57 directory not found: ${directory}`);
  const out=[];
  for(const entry of fs.readdirSync(root,{withFileTypes:true})){
    const full=path.join(root,entry.name);
    if(entry.isDirectory())out.push(...jsonFiles(full));
    else if(entry.isFile()&&entry.name.endsWith('.json'))out.push(full);
  }
  return out.sort();
}

const sessionDate=String(arg('--session-date','')).trim();
const universeTimeline=arg('--universe-timeline','data/p25-prospective-universe-timeline.ndjson');
const phase57Dir=arg('--phase57-dir');
const output=arg('--output',sessionDate?`artifacts/phase57-p25-2e-day-ledger-${sessionDate}.json`:null);
if(!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate)||!phase57Dir||!output){
  console.error('usage: node tools/phase57_p25_2e_build_day_ledger.mjs --session-date YYYY-MM-DD --phase57-dir <dir> [--universe-timeline <ndjson>] [--output <json>]');
  process.exit(2);
}

try{
  const records=readNdjson(universeTimeline,'P25 universe timeline');
  const matching=records.filter(x=>String(x?.sessionDate??'')===sessionDate&&x?.ready===true);
  if(matching.length!==1)throw new Error(`expected exactly one ready frozen universe for ${sessionDate}, found ${matching.length}`);
  const files=jsonFiles(phase57Dir);
  const results=files.map(file=>readJson(file,`Phase57 result ${file}`)).filter(x=>{
    const candidate=String(x?.provenance?.currentFeatureCutoff??x?.snapshot?.asOf??x?.phase57?.decision?.asOf??'');
    if(!candidate)return true;
    const ms=Date.parse(candidate);
    if(!Number.isFinite(ms))return true;
    const local=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(ms));
    return local===sessionDate;
  });
  const ledger=buildP252FrozenDaySessionLedger({universeRecord:matching[0],phase57Results:results});
  fs.mkdirSync(path.dirname(path.resolve(output)),{recursive:true});
  fs.writeFileSync(output,JSON.stringify(ledger,null,2)+'\n','utf8');
  console.log(JSON.stringify({
    status:ledger.status,
    sessionDate,
    output,
    inputFiles:files.length,
    acceptedDecisionCount:ledger.acceptedDecisionCount,
    completeFeatureCutoffCount:ledger.completeFeatureCutoffCount,
    comparisonEligibleFrozenSignalCount:ledger.comparisonEligibleFrozenSignalCount,
    eligibleDecisionCountsByVariant:ledger.eligibleDecisionCountsByVariant,
    safety:PHASE57_P25_2E_SAFETY,
  },null,2));
}catch(error){
  console.error(JSON.stringify({status:'BLOCKED_PHASE57_P25_2E_DAY_LEDGER',sessionDate,error:String(error?.message??error),safety:PHASE57_P25_2E_SAFETY},null,2));
  process.exit(1);
}
