import fs from 'node:fs';
import path from 'node:path';
import {PHASE57_US_CROSS_MARKET_POLICY,PHASE57_US_CROSS_MARKET_POLICY_SHA256,PHASE57_US_CROSS_MARKET_SAFETY,assertPhase57UsCrossMarketSafety} from '../predict/daytrade/phase57-us-cross-market-policy.js';

const arg=(n,f=null)=>{const i=process.argv.indexOf(n);return i>=0&&i+1<process.argv.length?process.argv[i+1]:f;};
const input=arg('--input'),output=arg('--output','tmp/us-universe.json'),sessionDate=arg('--session-date');
if(!input||!sessionDate)throw new Error('usage: --input listings.json --session-date YYYY-MM-DD [--output file]');
assertPhase57UsCrossMarketSafety();
const rows=JSON.parse(fs.readFileSync(input,'utf8'));
if(!Array.isArray(rows))throw new Error('US listings input must be an array');
const allowed=new Set(PHASE57_US_CROSS_MARKET_POLICY.exchanges);
const rejected={};const reject=r=>{rejected[r]=(rejected[r]??0)+1;};
const selected=[];
for(const x of rows){
  const symbol=String(x.symbol??'').trim().toUpperCase(),exchange=String(x.exchange??'').trim().toUpperCase();
  if(!symbol){reject('NO_SYMBOL');continue;}if(!allowed.has(exchange)){reject('EXCHANGE');continue;}
  if(x.active!==true){reject('INACTIVE');continue;}if(String(x.currency??'USD').toUpperCase()!=='USD'){reject('NON_USD');continue;}
  if(String(x.securityType??'COMMON_STOCK').toUpperCase()!=='COMMON_STOCK'){reject('NON_COMMON');continue;}
  const price=Number(x.price),dvol=Number(x.medianDollarVolume20d??x.medianDollarVolumeUsd??0);
  if(!Number.isFinite(price)||price<PHASE57_US_CROSS_MARKET_POLICY.universe.minimumPriceUsd){reject('PRICE');continue;}
  if(!Number.isFinite(dvol)||dvol<PHASE57_US_CROSS_MARKET_POLICY.universe.minimumMedianDollarVolumeUsd){reject('LIQUIDITY');continue;}
  selected.push({symbol,exchange,sector:String(x.sector??'UNKNOWN'),price,medianDollarVolume20d:dvol});
}
selected.sort((a,b)=>a.symbol.localeCompare(b.symbol));
if(selected.length<500)throw new Error(`US universe fail-closed: only ${selected.length} eligible symbols`);
const payload={schemaVersion:1,phase:'57.us-cross-market.universe-freeze',status:'US_UNIVERSE_FROZEN',sessionDate,createdAt:new Date().toISOString(),policySha256:PHASE57_US_CROSS_MARKET_POLICY_SHA256,inputCount:rows.length,eligibleCount:selected.length,rejected,universe:selected,methodology:{pointInTime:true,frozenBeforeRegularOpen:true,outcomeUsed:false},safety:PHASE57_US_CROSS_MARKET_SAFETY};
fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(payload,null,2)+'\n');
console.log(JSON.stringify({status:payload.status,sessionDate,inputCount:rows.length,eligibleCount:selected.length,rejected},null,2));
