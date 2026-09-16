import fs from 'node:fs';
import path from 'node:path';

const root=path.resolve(process.cwd(),'.github/workflows');
const KEEP_AUTO=new Set([
  'phase57-realtime-live.yml',
  'phase57-lane-y-raw-capture.yml',
]);
const ARCHIVE_BRANCH_PATTERNS=[
  /automation\/p25-/,
  /automation\/p57-us-free-5m-data/,
  /automation\/home-paper-equity-data/,
  /automation\/screener-data/,
];
const MARKER='# Archived 2026-09-16: historical persistence is manual-only; durable branch history is retained.';

function topLevelOnRange(lines){
  const start=lines.findIndex(line=>/^on:\s*$/.test(line));
  if(start<0)return null;
  let end=lines.length;
  for(let i=start+1;i<lines.length;i++){
    const line=lines[i];
    if(/^[A-Za-z0-9_.-]+:\s*(?:#.*)?$/.test(line)){
      end=i;
      break;
    }
  }
  return {start,end};
}

function hasAutomaticTrigger(block){
  return /(^|\n)\s{2}(?:schedule|workflow_run|push):/.test(block);
}

const changed=[];
const examined=[];
for(const name of fs.readdirSync(root).filter(x=>x.endsWith('.yml')||x.endsWith('.yaml')).sort()){
  if(KEEP_AUTO.has(name))continue;
  const file=path.join(root,name);
  const source=fs.readFileSync(file,'utf8');
  if(!ARCHIVE_BRANCH_PATTERNS.some(re=>re.test(source)))continue;
  const lines=source.split(/\r?\n/);
  const range=topLevelOnRange(lines);
  if(!range)throw new Error(`missing top-level on block: ${name}`);
  const block=lines.slice(range.start,range.end).join('\n');
  examined.push(name);
  if(!hasAutomaticTrigger(block))continue;
  const before=range.start>0&&lines[range.start-1]===MARKER?range.start-1:range.start;
  lines.splice(before,range.end-before,MARKER,'on:','  workflow_dispatch:');
  fs.writeFileSync(file,lines.join('\n'),'utf8');
  changed.push(name);
}

console.log(`ARCHIVE_PERSISTENCE_EXAMINED=${examined.length}`);
console.log(`ARCHIVE_PERSISTENCE_CHANGED=${changed.length}`);
for(const name of changed)console.log(`ARCHIVED ${name}`);

if(process.argv.includes('--check')){
  const offenders=[];
  for(const name of fs.readdirSync(root).filter(x=>x.endsWith('.yml')||x.endsWith('.yaml')).sort()){
    if(KEEP_AUTO.has(name))continue;
    const source=fs.readFileSync(path.join(root,name),'utf8');
    if(!ARCHIVE_BRANCH_PATTERNS.some(re=>re.test(source)))continue;
    const lines=source.split(/\r?\n/);
    const range=topLevelOnRange(lines);
    if(!range)continue;
    const block=lines.slice(range.start,range.end).join('\n');
    if(hasAutomaticTrigger(block))offenders.push(name);
  }
  if(offenders.length)throw new Error(`automatic archived persistence remains: ${offenders.join(', ')}`);
  console.log('ARCHIVE_PERSISTENCE_CHECK=PASS');
}
