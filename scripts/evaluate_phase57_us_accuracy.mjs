import fs from 'node:fs';
import path from 'node:path';
import {PHASE57_US_CROSS_MARKET_POLICY as P,PHASE57_US_CROSS_MARKET_POLICY_SHA256 as H,assertPhase57UsCrossMarketSafety} from '../predict/daytrade/phase57-us-cross-market-policy.js';

const arg=(n,f=null)=>{const i=process.argv.indexOf(n);return i>=0&&i+1<process.argv.length?process.argv[i+1]:f;};
const input=arg('--input'),output=arg('--output','tmp/us-accuracy.json');
if(!input)throw new Error('usage: --input trades.json [--output file]');
assertPhase57UsCrossMarketSafety();
const raw=JSON.parse(fs.readFileSync(input,'utf8'));
const trades=Array.isArray(raw)?raw:raw.trades;
if(!Array.isArray(trades))throw new Error('input must be trades array or {trades:[...]}');
const allowed=new Set(P.lanes);
const byLane=new Map(P.lanes.map(x=>[x,[]]));
for(const t of trades){
  const lane=String(t.lane??'');
  if(!allowed.has(lane))continue;
  const r=Number(t.returnPct);
  if(!Number.isFinite(r))throw new Error(`invalid returnPct in ${lane}`);
  byLane.get(lane).push(r);
}
const median=a=>{if(!a.length)return null;const s=[...a].sort((x,y)=>x-y),m=Math.floor(s.length/2);return s.length%2?s[m]:(s[m-1]+s[m])/2;};
const metrics=a=>{
  if(!a.length)return {n:0,netReturnPct:null,meanReturnPctPerTrade:null,medianReturnPctPerTrade:null,winRatePct:null,profitFactor:null,maxDrawdownPct:null};
  let equity=1,peak=1,maxDd=0,grossWin=0,grossLoss=0,wins=0;
  for(const r of a){equity*=1+r/100;if(equity>peak)peak=equity;maxDd=Math.max(maxDd,(peak-equity)/peak*100);if(r>0){grossWin+=r;wins++;}else if(r<0)grossLoss+=-r;}
  const mean=a.reduce((s,x)=>s+x,0)/a.length;
  return {n:a.length,netReturnPct:(equity-1)*100,meanReturnPctPerTrade:mean,medianReturnPctPerTrade:median(a),winRatePct:wins/a.length*100,profitFactor:grossLoss===0?(grossWin>0?null:0):grossWin/grossLoss,maxDrawdownPct:maxDd};
};
const lanes=Object.fromEntries([...byLane].map(([lane,a])=>[lane,metrics(a)]));
const payload={schemaVersion:1,phase:'57.us-cross-market.accuracy',status:'US_ACCURACY_EVALUATED',policySha256:H,market:'US',returnUnit:'PERCENT',currencyConversion:false,capitalAllocation:false,lanes};
fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(payload,null,2)+'\n');
console.log(JSON.stringify(payload,null,2));
