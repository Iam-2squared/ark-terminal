import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {PHASE57_US_CROSS_MARKET_SAFETY,assertPhase57UsCrossMarketSafety} from '../predict/daytrade/phase57-us-cross-market-policy.js';

const arg=(n,f=null)=>{const i=process.argv.indexOf(n);return i>=0&&i+1<process.argv.length?process.argv[i+1]:f;};
const output=arg('--output','tmp/us-free-reference.json');
const sourceUrl='https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqtraded.txt';
const exchangeMap=Object.freeze({Q:'NASDAQ',N:'NYSE',A:'NYSE_AMERICAN',P:'NYSE_ARCA'});
const digest=x=>crypto.createHash('sha256').update(JSON.stringify(x)).digest('hex');

assertPhase57UsCrossMarketSafety();
const r=await fetch(sourceUrl,{headers:{'User-Agent':'ark-terminal-phase57-research'}});
if(!r.ok)throw new Error(`US free reference HTTP ${r.status}`);
const text=await r.text();
const lines=text.split(/\r?\n/).filter(Boolean);
if(lines.length<500)throw new Error(`US free reference unexpectedly small: ${lines.length}`);
const header=lines[0].split('|');
const idx=Object.fromEntries(header.map((x,i)=>[x.trim(),i]));
for(const k of ['Nasdaq Traded','Symbol','Security Name','Listing Exchange','ETF','Test Issue'])if(!(k in idx))throw new Error(`US free reference missing column ${k}`);
const rejectName=/(warrant|rights?|preferred|preference|units?|depositary|bond|notes?|fund|trust|etf)/i;
const rows=[];const rejected={};const reject=k=>{rejected[k]=(rejected[k]??0)+1;};
for(const line of lines.slice(1)){
  if(line.startsWith('File Creation Time'))continue;
  const c=line.split('|');
  if(c[idx['Nasdaq Traded']]!=='Y'){reject('NOT_NASDAQ_TRADED');continue;}
  if(c[idx['ETF']]==='Y'){reject('ETF');continue;}
  if(c[idx['Test Issue']]==='Y'){reject('TEST_ISSUE');continue;}
  const symbol=String(c[idx['Symbol']]??'').trim().toUpperCase();
  if(!symbol||symbol.length>12||/[^A-Z0-9.\-]/.test(symbol)){reject('SYMBOL');continue;}
  const exchangeCode=String(c[idx['Listing Exchange']]??'').trim().toUpperCase();
  const exchange=exchangeMap[exchangeCode];
  if(!exchange){reject('EXCHANGE');continue;}
  const name=String(c[idx['Security Name']]??'').trim();
  if(rejectName.test(name)){reject('NON_COMMON_LIKE_NAME');continue;}
  rows.push({symbol,exchange,exchangeCode,name,provider:'NASDAQ_TRADER_REFERENCE'});
}
rows.sort((a,b)=>a.symbol.localeCompare(b.symbol));
const dedup=[];const seen=new Set();for(const x of rows){if(seen.has(x.symbol))continue;seen.add(x.symbol);dedup.push(x);}
if(dedup.length<1500)throw new Error(`US free collection universe fail-closed: only ${dedup.length} symbols`);
const payload={
  schemaVersion:1,phase:'57.us-cross-market.free-reference',status:'US_FREE_COLLECTION_UNIVERSE',
  createdAt:new Date().toISOString(),sourceUrl,inputLines:lines.length,eligibleCount:dedup.length,rejected,
  universe:dedup,rawDigest:digest(dedup),
  classification:{rawCollectionOnly:true,formalFreshEligible:false,jpxOosSubstitute:false,securityTypeFilterApproximate:true},
  methodology:{outcomeUsed:false,missingSymbolsNeverFabricated:true},safety:PHASE57_US_CROSS_MARKET_SAFETY,
};
fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(payload,null,2)+'\n');
console.log(JSON.stringify({status:payload.status,eligibleCount:payload.eligibleCount,rejected,output},null,2));
