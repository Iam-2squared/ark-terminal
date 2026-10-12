import fs from 'node:fs';
import path from 'node:path';
import {loadFormalL0PartitionFromCache} from '../predict/long-only/phase57-long-only-l0-cache.js';
import {buildLongOnlyL0OpportunityCensus} from '../predict/long-only/phase57-long-only-l0-opportunity-census.js';

const arg=name=>{const index=process.argv.indexOf(name);return index<0?null:process.argv[index+1];};
const cacheRoot=arg('--cache-root'),partition=arg('--partition')??'DEVELOPMENT_A',output=arg('--output');
if(!cacheRoot||!output)throw new Error('usage: --cache-root <private-cache> --partition DEVELOPMENT_A --output <census.json>');
const plan=JSON.parse(fs.readFileSync(new URL('../predict/long-only/phase57-long-only-data-plan.json',import.meta.url),'utf8'));
const allocation=JSON.parse(fs.readFileSync(new URL('../predict/long-only/phase57-long-only-session-allocation-v3.json',import.meta.url),'utf8'));
const input=loadFormalL0PartitionFromCache({cacheRoot,partition,plan,allocation});
const result=buildLongOnlyL0OpportunityCensus(input);
fs.mkdirSync(path.dirname(output),{recursive:true});
fs.writeFileSync(output,`${JSON.stringify(result,null,2)}\n`,{flag:'wx'});
console.log(JSON.stringify({status:result.status,partition,sessionCount:result.lineage.sessionCount,rowCount:result.lineage.rowCount,sourceSha256:result.lineage.sourceSha256,output},null,2));
