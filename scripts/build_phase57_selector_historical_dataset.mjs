import fs from 'node:fs';
import path from 'node:path';
import {buildPhase57SelectorHistoricalDatasetFromShards} from './lib/phase57-selector-dataset-builder.mjs';

function arg(name,fallback=null){const index=process.argv.indexOf(name);return index>=0&&index+1<process.argv.length?process.argv[index+1]:fallback;}
function walk(directory){
  const out=[];
  for(const entry of fs.readdirSync(directory,{withFileTypes:true})){
    const value=path.join(directory,entry.name);
    if(entry.isDirectory())out.push(...walk(value));
    else if(entry.isFile()&&entry.name.endsWith('.json'))out.push(value);
  }
  return out;
}
const shardDirectory=arg('--shard-dir');
const output=arg('--output','artifacts/phase57-selector-historical-dataset.json');
const minimumSymbolsPerSession=Number(arg('--min-symbols-per-session','200'));
if(!shardDirectory)throw new Error('usage: --shard-dir <directory> [--output file] [--min-symbols-per-session N]');
const files=walk(shardDirectory).sort();
const shards=[];
for(const file of files){
  let value;
  try{value=JSON.parse(fs.readFileSync(file,'utf8'));}catch{continue;}
  if(value?.phase==='57.selector-v3.yahoo-5m-shard')shards.push(value);
}
if(!shards.length)throw new Error('no Selector Yahoo 5m shard JSON files found');
const dataset=buildPhase57SelectorHistoricalDatasetFromShards(shards,{minimumSymbolsPerSession});
fs.mkdirSync(path.dirname(output),{recursive:true});
fs.writeFileSync(output,JSON.stringify(dataset,null,2)+'\n');
console.log(JSON.stringify({
  status:'SELECTOR_HISTORICAL_DATASET_READY',output,datasetId:dataset.manifest.datasetId,
  shards:shards.length,symbols:dataset.symbols.length,sessions:dataset.sessions.length,
  evidenceClassification:dataset.manifest.evidenceClassification,
  universeStatus:dataset.manifest.universeStatus,
},null,2));

