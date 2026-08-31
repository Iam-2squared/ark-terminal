import fs from 'node:fs';
import path from 'node:path';
import {PHASE57_US_CROSS_MARKET_POLICY,PHASE57_US_CROSS_MARKET_POLICY_SHA256,PHASE57_US_CROSS_MARKET_SAFETY,assertPhase57UsCrossMarketSafety} from '../predict/daytrade/phase57-us-cross-market-policy.js';

const arg=(n,f=null)=>{const i=process.argv.indexOf(n);return i>=0&&i+1<process.argv.length?process.argv[i+1]:f;};
const universePath=arg('--universe'),snapshotPath=arg('--snapshot'),output=arg('--output','tmp/us-marketwide-measurement.json');
if(!universePath||!snapshotPath)throw new Error('usage: --universe frozen.json --snapshot quotes.json --output file');
assertPhase57UsCrossMarketSafety();
const u=JSON.parse(fs.readFileSync(universePath,'utf8')),rows=JSON.parse(fs.readFileSync(snapshotPath,'utf8'));
if(u.status!=='US_UNIVERSE_FROZEN'||u.policySha256!==PHASE57_US_CROSS_MARKET_POLICY_SHA256)throw new Error('US universe contract mismatch');
if(!Array.isArray(rows))throw new Error('US snapshot must be array');
const allowed=new Set(u.universe.map(x=>x.symbol));
const valid=rows.filter(x=>allowed.has(String(x.symbol??'').toUpperCase())&&Number.isFinite(Number(x.currentPrice))&&Number(x.currentPrice)>0&&Number.isFinite(Number(x.volume))&&Number(x.volume)>=0);
if(valid.length<Math.min(500,Math.floor(u.eligibleCount*0.8)))throw new Error(`US marketwide snapshot incomplete ${valid.length}/${u.eligibleCount}`);
const score=x=>{
  const ch=Math.abs(Number(x.changePct??0)),vr=Math.max(0,Number(x.volumeRatio??1)),turn=Math.max(0,Number(x.dollarVolume??0));
  return 0.45*Math.min(1,ch/5)+0.30*Math.min(1,vr/3)+0.25*Math.min(1,Math.log10(1+turn)/9);
};
const ranked=valid.map(x=>({...x,usOpportunityScore:score(x)})).sort((a,b)=>b.usOpportunityScore-a.usOpportunityScore||String(a.symbol).localeCompare(String(b.symbol)));
const selected=ranked.slice(0,50),selectedV2=ranked.filter((x,i)=>i<80).sort((a,b)=>{
  const aq=Math.min(1,Number(a.volumeRatio??1)/3),bq=Math.min(1,Number(b.volumeRatio??1)/3);
  return (b.usOpportunityScore*0.65+bq*0.35)-(a.usOpportunityScore*0.65+aq*0.35);
}).slice(0,30);
const payload={schemaVersion:1,phase:'57.us-cross-market.marketwide-5m',status:'US_MARKETWIDE_5M_MEASURED',sessionDate:u.sessionDate,observedAt:new Date().toISOString(),inputSymbols:valid.length,selectedSymbols:selected.length,selectedV2Symbols:selectedV2.length,selected,selectedV2,classification:{crossMarketProspective:true,jpxOosSubstitute:false,formalOos:false,promotionEligible:false},methodology:{universeFrozenBeforeOpen:true,pointInTimeOnly:true,futureOutcomeUsed:false,missingSymbolsNeverFabricated:true},policySha256:PHASE57_US_CROSS_MARKET_POLICY_SHA256,safety:PHASE57_US_CROSS_MARKET_SAFETY};
fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(payload,null,2)+'\n');
console.log(JSON.stringify({status:payload.status,inputSymbols:payload.inputSymbols,v1:50,v2:30},null,2));
