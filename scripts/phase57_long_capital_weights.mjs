// Reuse the pinned V3 equal/rank arithmetic only. Never call its old Entry builder.
import fs from 'node:fs';
import {allocateV3} from './lib/phase57-capital-allocation-v3-entrytime.mjs';
const rows=JSON.parse(fs.readFileSync(0,'utf8'));
const keys=['eventId','timestamp','symbol','score'];
const sets=new Map();
for(const r of rows){
  if(Object.keys(r).sort().join()!==[...keys].sort().join())throw Error('NON_CAUSAL_ENVELOPE');
  if(!Number.isFinite(r.score)||r.score<2||r.score>4)throw Error('FROZEN_SCORE_RANGE');
  if(!sets.has(r.timestamp))sets.set(r.timestamp,[]);
  sets.get(r.timestamp).push(r);
}
const output={EQUAL_MAX3:{},LONG_RANK_MAX3:{}};
for(const set of sets.values()){
  set.sort((a,b)=>b.score-a.score||a.symbol.localeCompare(b.symbol)||a.eventId.localeCompare(b.eventId));
  if(new Set(set.map(x=>x.symbol)).size!==set.length)throw Error('DUPLICATE_SYMBOL_SET');
  for(const [arm,policy] of [['EQUAL_MAX3','V3_0_EQUAL'],['LONG_RANK_MAX3','V3_A_RANK']]){
    const weights=allocateV3({candidates:set},policy);
    set.forEach((r,i)=>output[arm][r.eventId]=weights[i].weight);
  }
}
process.stdout.write(JSON.stringify(output));
