import fs from 'node:fs';
import path from 'node:path';

const root=path.resolve('.github/workflows');
const KEEP_AUTOMATIC=new Set(['phase57-realtime-live.yml','phase57-lane-y-raw-capture.yml']);
const LEGACY_BRANCH=/automation\/(?:p25-[A-Za-z0-9._/-]+|p57-us-free-5m-data|home-paper-equity-data|screener-data)/;
const P25_DISPATCH=/gh\s+workflow\s+run\s+['"]?phase57-p25-/;
const MARKER='# Archived 2026-09-16: legacy persistence automatic triggers retired; manual history retained.';

function onRange(lines){
  const start=lines.findIndex(x=>/^on:\s*$/.test(x));
  if(start<0)return null;
  let end=lines.length;
  for(let i=start+1;i<lines.length;i++) if(/^[A-Za-z0-9_.-]+:\s*(?:#.*)?$/.test(lines[i])){end=i;break;}
  return {start,end};
}
function eventRanges(lines,range){
  const starts=[];
  for(let i=range.start+1;i<range.end;i++){
    const m=lines[i].match(/^  ([A-Za-z0-9_.-]+):(?:\s*(.*))?$/);
    if(m)starts.push({i,name:m[1]});
  }
  return starts.map((x,n)=>({...x,end:n+1<starts.length?starts[n+1].i:range.end}));
}
function manualDispatch(lines,range){
  const r=eventRanges(lines,range).find(x=>x.name==='workflow_dispatch');
  return r?lines.slice(r.i,r.end):['  workflow_dispatch:'];
}
function isLegacyWriter(source){
  if(!LEGACY_BRANCH.test(source))return false;
  const canWrite=/contents:\s*write/.test(source);
  const mutatesRepo=/\bgit\s+push\b/.test(source)||/\bgh\s+api\b[\s\S]{0,500}(?:--method\s+(?:PUT|POST)|-X\s+(?:PUT|POST)|-f\s+branch=)/.test(source);
  return canWrite&&mutatesRepo;
}
function isLegacyDispatcher(source){
  return /actions:\s*write/.test(source)&&P25_DISPATCH.test(source);
}
function rewriteManualOnly(file,source){
  const lines=source.split(/\r?\n/), range=onRange(lines);
  if(!range)throw new Error(`missing on block: ${file}`);
  const dispatch=manualDispatch(lines,range);
  const before=range.start>0&&lines[range.start-1]===MARKER?range.start-1:range.start;
  lines.splice(before,range.end-before,MARKER,'on:',...dispatch);
  return lines.join('\n');
}
function rewritePhase52(source){
  const lines=source.split(/\r?\n/), range=onRange(lines);
  if(!range)throw new Error('missing Phase52 on block');
  const keep=new Set(['pull_request','workflow_dispatch']);
  const events=eventRanges(lines,range);
  const body=[];
  for(const r of events) if(keep.has(r.name)) body.push(...lines.slice(r.i,r.end));
  lines.splice(range.start,range.end-range.start,'on:',...body);
  return lines.join('\n');
}

const archived=[];
for(const name of fs.readdirSync(root).filter(x=>/\.ya?ml$/.test(x)).sort()){
  if(KEEP_AUTOMATIC.has(name))continue;
  const file=path.join(root,name), source=fs.readFileSync(file,'utf8');
  if(!isLegacyWriter(source)&&!isLegacyDispatcher(source))continue;
  const next=rewriteManualOnly(name,source);
  if(next!==source){fs.writeFileSync(file,next,'utf8');archived.push(name);}
}

const phase52=path.join(root,'phase52-daily-persistence.yml');
if(fs.existsSync(phase52)){
  const source=fs.readFileSync(phase52,'utf8'), next=rewritePhase52(source);
  if(next!==source){fs.writeFileSync(phase52,next,'utf8');archived.push('phase52-daily-persistence.yml');}
}

console.log(`LEGACY_PERSISTENCE_ARCHIVED=${archived.length}`);
for(const x of archived)console.log(`ARCHIVED ${x}`);

if(process.argv.includes('--check')){
  const offenders=[];
  for(const name of fs.readdirSync(root).filter(x=>/\.ya?ml$/.test(x)).sort()){
    if(KEEP_AUTOMATIC.has(name))continue;
    const source=fs.readFileSync(path.join(root,name),'utf8');
    if(!isLegacyWriter(source)&&!isLegacyDispatcher(source))continue;
    const lines=source.split(/\r?\n/), range=onRange(lines); if(!range)continue;
    const events=eventRanges(lines,range).map(x=>x.name);
    if(events.some(x=>x!=='workflow_dispatch'))offenders.push(`${name}:${events.join(',')}`);
  }
  const p52=fs.readFileSync(phase52,'utf8').split(/\r?\n/); const p52r=onRange(p52);
  const p52events=eventRanges(p52,p52r).map(x=>x.name);
  if(p52events.some(x=>!['pull_request','workflow_dispatch'].includes(x)))offenders.push(`phase52-daily-persistence.yml:${p52events.join(',')}`);
  for(const keep of KEEP_AUTOMATIC){
    const src=fs.readFileSync(path.join(root,keep),'utf8');
    if(!/schedule:/.test(src))offenders.push(`${keep}:automatic-schedule-missing`);
  }
  if(offenders.length)throw new Error(`archive policy failure: ${offenders.join(' | ')}`);
  console.log('LEGACY_PERSISTENCE_ARCHIVE_CHECK=PASS');
}
