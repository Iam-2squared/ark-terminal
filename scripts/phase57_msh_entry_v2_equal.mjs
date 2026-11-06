// Score-free adapter. Reuse frozen Equal arithmetic without the old v1 E[L] gate.
import fs from 'node:fs';
import {allocateV3} from './lib/phase57-capital-allocation-v3-entrytime.mjs';
const rows=JSON.parse(fs.readFileSync(0,'utf8'));
const allowed=['eventId','timestamp','symbol'];
const sets=new Map(),ids=new Set(),output={};
for(const row of rows){
  if(Object.keys(row).sort().join()!==[...allowed].sort().join())throw Error('NON_CAUSAL_ALLOCATION_ENVELOPE');
  if(ids.has(row.eventId)||!Number.isFinite(Date.parse(row.timestamp))||typeof row.symbol!=='string')throw Error('INVALID_ALLOCATION_IDENTITY');
  ids.add(row.eventId);
  if(!sets.has(row.timestamp))sets.set(row.timestamp,[]);
  sets.get(row.timestamp).push(row);
}
for(const set of sets.values()){
  set.sort((a,b)=>a.symbol.localeCompare(b.symbol)||a.eventId.localeCompare(b.eventId));
  if(new Set(set.map(r=>r.symbol)).size!==set.length)throw Error('DUPLICATE_SYMBOL_SET');
  const weights=allocateV3({candidates:set},'V3_0_EQUAL');
  set.forEach((r,i)=>output[r.eventId]=weights[i].weight);
}
process.stdout.write(JSON.stringify(output));
