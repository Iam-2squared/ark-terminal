// Read only pinned Development checkpoints; evaluator outcomes never affect ranks.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {pathToFileURL} from 'node:url';
import {normalizeAndAggregateMinuteRows} from '../predict/long-only/phase57-long-only-integrated-dataset.js';
const sha=b=>createHash('sha256').update(b).digest('hex');
const read=f=>JSON.parse(fs.readFileSync(f));
const minute=t=>{const s=new Date(Date.parse(t)+32400000).toISOString();return Number(s.slice(11,13))*60+Number(s.slice(14,16));};
export function scoreWindow(map,start,h,date){
 const close=date<'2024-11-05'?900:930;
 if(start+h>close||start>=690&&start<750||start<690&&start+h>690)return null;
 const rows=[];
 for(let m=start;m<start+h;m+=5){const b=map.get(m);if(!b)return null;
  if(![b.open,b.high,b.low,b.close].every(x=>Number.isFinite(x)&&x>0)||b.low>Math.min(b.open,b.close)||b.high<Math.max(b.open,b.close)||minute(b.availableAtJst)!==m+5)throw Error('INVALID_BAR');rows.push(b);}
 if(!rows.length)return null;
 const price=rows[0].open,gross=100*(rows.at(-1).close/price-1),MFE=Math.max(0,...rows.map(b=>100*(b.high/price-1))),MAE=Math.min(0,...rows.map(b=>100*(b.low/price-1)));
 return {gross,MFE,MAE};
}
export function main(cache,context,out){
 if(!cache||!context||!out||fs.existsSync(out))throw Error('NEW_OUTPUT_REQUIRED');
 const meta=read(path.join(context,'context.json'));
 const prior=JSON.parse(gunzipSync(fs.readFileSync('docs/evidence/phase57-msh-entry-long-v2-development/paths.json.gz')));
 const alloc=read('predict/long-only/phase57-long-only-session-allocation-v3.json');
 fs.mkdirSync(out,{recursive:true});const hs=[15,30,60,90,120],fds=new Map();
 for(const h of hs){const fd=fs.openSync(path.join(out,`score-${h}.tsv`),'wx',0o600);fds.set(h,fd);fs.writeSync(fd,'sessionDate\tdecisionTimeJst\tscoreDecile\tsavedV1Score\tgross\tMFE\tMAE\n');}
 try{for(const item of meta.files){
  const date=item.sessionDate,saved=prior.sources.find(s=>s.sessionDate===date);
  if(!saved||!Object.entries(alloc.partitions).some(([k,v])=>k.startsWith('DEVELOPMENT_')&&v.includes(date)))throw Error('SEALED_SCOPE');
  const f=path.join(cache,'phase57-long-only/raw/jquants-v2',date,'minute-pages.json');
  if(sha(fs.readFileSync(f))!==saved.rawPagesSHA)throw Error('RAW_SHA');
  const pages=read(f);for(const p of pages)if(sha(p.responseText)!==p.responseSha256)throw Error('PAGE_SHA');
  const raw=pages.flatMap(p=>JSON.parse(p.responseText).data??[]);if(raw.some(r=>(r.Date??r.date)!==date))throw Error('DATE_SCOPE');
  const normalized=normalizeAndAggregateMinuteRows(raw);if(sha(JSON.stringify(normalized.bars))!==saved.normalizedSHA)throw Error('NORMALIZED_SHA');
  const maps=new Map();for(const b of normalized.bars){if(!maps.has(b.symbol))maps.set(b.symbol,new Map());const m=minute(b.barStartJst);if(maps.get(b.symbol).has(m))throw Error('DUPLICATE_BAR');maps.get(b.symbol).set(m,b);}
  const file=path.join(context,item.path);if(sha(fs.readFileSync(file))!==item.sha256)throw Error('CONTEXT_SHA');
  const lines=fs.readFileSync(file,'utf8').trim().split('\n'),header=lines.shift().split('\t');const buffers=Object.fromEntries(hs.map(h=>[h,[]]));
  for(const line of lines){const r=Object.fromEntries(line.split('\t').map((v,i)=>[header[i],v]));if(r.sessionDate!==date)throw Error('CONTEXT_DATE');
   const start=Number(r.decisionTimeJst.slice(0,2))*60+Number(r.decisionTimeJst.slice(3,5));
   for(const h of hs){const result=scoreWindow(maps.get(r.symbol)??new Map(),start,h,date);if(result)buffers[h].push([date,r.decisionTimeJst,r.scoreDecile,r.savedV1Score,result.gross,result.MFE,result.MAE].join('\t'));}}
  for(const h of hs)if(buffers[h].length)fs.writeSync(fds.get(h),buffers[h].join('\n')+'\n');
  console.log(JSON.stringify({status:'FROZEN_SCORE_PATHS_PROJECTED',sessionDate:date,eligibleRows:lines.length,providerRequests:0}));
 }}finally{for(const fd of fds.values())fs.closeSync(fd);}
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href)main(...process.argv.slice(2));
