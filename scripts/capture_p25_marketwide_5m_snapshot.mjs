import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const SAFETY=Object.freeze({executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,freshHoldoutConsumed:false});
function arg(name,fallback=null){const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;}
function sha(value){return crypto.createHash('sha256').update(value).digest('hex');}
function bucket5m(iso){const d=new Date(iso);if(!Number.isFinite(d.getTime()))throw new Error('invalid --as-of');d.setUTCSeconds(0,0);d.setUTCMinutes(Math.floor(d.getUTCMinutes()/5)*5);return d.toISOString();}
function loadJson(file){return JSON.parse(fs.readFileSync(file,'utf8'));}
function canonicalRows(payload){
  const rows=Array.isArray(payload)?payload:(Array.isArray(payload?.entries)?payload.entries:(Array.isArray(payload?.records)?payload.records:[]));
  const seen=new Set();
  return rows.map(row=>({symbol:String(row?.symbol??'').trim(),price:Number(row?.currentPrice??row?.price??row?.lastPrice),volume:Number(row?.volume??0),changePct:Number(row?.dailyChangePercent??row?.changePct??0),turnover:Number(row?.turnover??0),sector:String(row?.sector??'')}))
    .filter(row=>row.symbol&&Number.isFinite(row.price)&&row.price>0&&Number.isFinite(row.volume)&&row.volume>0&&!seen.has(row.symbol)&&(seen.add(row.symbol),true))
    .sort((a,b)=>a.symbol.localeCompare(b.symbol));
}
const input=arg('--input');const output=arg('--output','data/p25-marketwide-5m-snapshots.ndjson');const asOf=arg('--as-of',new Date().toISOString());
if(!input){console.error('usage: node scripts/capture_p25_marketwide_5m_snapshot.mjs --input <point-in-time-market-json> [--as-of ISO] [--output NDJSON]');process.exit(2);}
try{
  const rows=canonicalRows(loadJson(input));
  if(rows.length<3000)throw new Error(`market-wide snapshot requires >=3000 valid JPX rows, got ${rows.length}`);
  const bucket=bucket5m(asOf);const stateHash=sha(JSON.stringify(rows));
  fs.mkdirSync(path.dirname(output),{recursive:true});
  const existing=fs.existsSync(output)?fs.readFileSync(output,'utf8').split(/\r?\n/).filter(Boolean).map(JSON.parse):[];
  const duplicate=existing.some(r=>r.bucket===bucket&&r.stateHash===stateHash);
  if(!duplicate){
    const record={schemaVersion:1,phase:'57.p25.marketwide-5m-fresh-capture',bucket,observedAt:new Date(asOf).toISOString(),symbolCount:rows.length,stateHash,rows,methodology:{cadenceMinutes:5,pointInTimeOnly:true,deduplicated:true,minimumMarketwideSymbols:3000,winnerSelectionAllowed:false,formalOos:false,promotionEligible:false},safety:SAFETY};
    fs.appendFileSync(output,JSON.stringify(record)+'\n','utf8');
  }
  console.log(JSON.stringify({status:'OK',bucket,symbolCount:rows.length,stateHash,appended:!duplicate,output,safety:SAFETY},null,2));
}catch(error){console.error(JSON.stringify({status:'BLOCKED_MARKETWIDE_5M_CAPTURE',error:String(error?.message??error),safety:SAFETY},null,2));process.exit(1);}
