import fs from 'node:fs';
import path from 'node:path';
const arg=(n,f=null)=>{const i=process.argv.indexOf(n);return i>=0&&i+1<process.argv.length?process.argv[i+1]:f;};
const inputDir=arg('--input-dir');const partialDir=arg('--partial-dir');const output=arg('--output');
if(!inputDir||!partialDir||!output)throw new Error('usage: --input-dir <dir> --partial-dir <dir> --output <json>');
const sym=v=>String(v??'').trim().toUpperCase();const uniq=xs=>[...new Set(xs.map(sym).filter(Boolean))].sort();
const freeze=JSON.parse(fs.readFileSync(path.join(partialDir,'freeze.json'),'utf8'));
const measurements=fs.readFileSync(path.join(partialDir,'partial-measurements.ndjson'),'utf8').split(/\r?\n/).filter(Boolean).map(line=>JSON.parse(line));
const expected=uniq([...Object.values(freeze.variants??{}).flat(),...measurements.flatMap(x=>(x.selected??[]).map(r=>r.symbol))]);
const files=fs.readdirSync(inputDir).filter(x=>x.endsWith('.json')).sort();if(!files.length)throw new Error('no bar shard files');
const sessionBarsBySymbol={},barAudit=[],failures=[],seen=new Set(),shards=[];
for(const file of files){const p=JSON.parse(fs.readFileSync(path.join(inputDir,file),'utf8'));if(p.status!=='P25_INCOMPLETE_ABCD_BAR_SHARD_READY'||p.sessionDate!==freeze.sessionDate)throw new Error(`invalid bar shard ${file}`);shards.push({file,shardIndex:p.shardIndex,shardCount:p.shardCount,requested:p.requestedSymbols.length});for(const s of p.requestedSymbols){if(seen.has(s))throw new Error(`duplicate requested symbol across shards ${s}`);seen.add(s);}for(const [s,bars] of Object.entries(p.sessionBarsBySymbol??{})){if(sessionBarsBySymbol[s])throw new Error(`duplicate usable symbol ${s}`);sessionBarsBySymbol[s]=bars;}barAudit.push(...(p.barAudit??[]));failures.push(...(p.failures??[]));}
const missingShardCoverage=expected.filter(s=>!seen.has(s));if(missingShardCoverage.length)throw new Error(`bar shard partition incomplete: ${missingShardCoverage.slice(0,12).join(',')}`);
const unavailableSymbols=expected.filter(s=>!sessionBarsBySymbol[s]).sort();const failureSymbols=uniq(failures.map(x=>x.symbol));if(JSON.stringify(unavailableSymbols)!==JSON.stringify(failureSymbols))throw new Error('bar failure coverage mismatch');
barAudit.sort((a,b)=>a.symbol.localeCompare(b.symbol));failures.sort((a,b)=>String(a.symbol).localeCompare(String(b.symbol)));
const safety={executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,freshHoldoutConsumed:false};
const payload={schemaVersion:1,phase:'57.p25.incomplete-abcd-bars-combined',status:'P25_INCOMPLETE_ABCD_BARS_COMBINED',sessionDate:freeze.sessionDate,expectedSymbols:expected,requestedSymbolCount:expected.length,usableSymbolCount:Object.keys(sessionBarsBySymbol).length,unavailableSymbolCount:unavailableSymbols.length,unavailableSymbols,sessionBarsBySymbol,barAudit,failures,shards,methodology:{exactUnionOfShardOutputs:true,noBackfillInterpolationOrReplacement:true,incompleteCoverageRetainedExplicitly:true},safety};
fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(payload,null,2)+'\n');console.log(JSON.stringify({status:payload.status,requested:payload.requestedSymbolCount,usable:payload.usableSymbolCount,unavailable:payload.unavailableSymbols},null,2));
