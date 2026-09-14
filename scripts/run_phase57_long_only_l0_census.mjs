import fs from 'node:fs';
import path from 'node:path';
import {buildLongOnlyL0OpportunityCensus} from '../predict/long-only/phase57-long-only-l0-opportunity-census.js';

const arg=(name,fallback=null)=>{
  const index=process.argv.indexOf(name);
  return index>=0?process.argv[index+1]:fallback;
};
const input=arg('--input'),output=arg('--output');
if(!input||!output){
  console.error('usage: node scripts/run_phase57_long_only_l0_census.mjs --input <development.json> --output <census.json>');
  process.exit(2);
}

const payload=JSON.parse(fs.readFileSync(input,'utf8'));
const result=buildLongOnlyL0OpportunityCensus({
  rows:payload.rows,
  partition:payload.partition,
  sourceManifest:payload.sourceManifest,
});
fs.mkdirSync(path.dirname(output),{recursive:true});
fs.writeFileSync(output,`${JSON.stringify(result,null,2)}\n`);
console.log(JSON.stringify({status:result.status,partition:result.partition,lineage:result.lineage,output},null,2));

