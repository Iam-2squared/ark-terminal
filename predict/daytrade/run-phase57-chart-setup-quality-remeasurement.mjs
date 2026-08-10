import fs from 'node:fs';
import { EXPANDED_UNIVERSE } from './phase57-expanded-universe.js';
import { PHASE57_CHART_PERCEPTION_SAFETY } from './phase57-chart-perception-2.js';
import { buildSessionAwareMultiTimeframePerception } from './phase57-chart-perception-session-aware.js';
import { classifyHumanStyleSetup, deriveSameSessionOutcome } from './phase57-chart-perception-measurement.js';
import { scoreHumanStyleSetupQuality } from './phase57-chart-setup-quality.js';

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const symbols = process.env.PHASE57_SYMBOLS
  ? process.env.PHASE57_SYMBOLS.split(',').map(v => v.trim()).filter(Boolean)
  : EXPANDED_UNIVERSE.slice(0, 3);
const minHistoryBars = Number(process.env.PHASE57_MIN_HISTORY_BARS ?? 1600);
const stepBars = Number(process.env.PHASE57_STEP_BARS ?? 3);
const JST = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Tokyo', year:'numeric', month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit', hourCycle:'h23' });

function parts(ts) {
  const p = Object.fromEntries(JST.formatToParts(new Date(ts)).map(x => [x.type, x.value]));
  return { date:`${p.year}-${p.month}-${p.day}`, hm:`${p.hour}:${p.minute}` };
}
function normalize(rows=[]) {
  return rows.map(r => ({ timestamp:new Date(r.timestamp).toISOString(), open:Number(r.open), high:Number(r.high), low:Number(r.low), close:Number(r.close), volume:Number(r.volume??0) }))
    .filter(r => [r.open,r.high,r.low,r.close].every(Number.isFinite) && r.high>=r.low)
    .sort((a,b)=>a.timestamp.localeCompare(b.timestamp));
}
function qualityBand(score) {
  const s = Number(score);
  if (!Number.isFinite(s)) return 'UNSCORED';
  if (s < 0.40) return 'Q1_LOW';
  if (s < 0.55) return 'Q2';
  if (s < 0.70) return 'Q3';
  return 'Q4_HIGH';
}
async function fetchJson(urls, symbol) {
  let last;
  for (const url of urls) {
    for (let attempt=1; attempt<=4; attempt+=1) {
      try {
        const controller = new AbortController();
        const timer = setTimeout(()=>controller.abort(), 30000);
        const response = await fetch(url, { headers:{'User-Agent':'Mozilla/5.0 ArkTerminalResearch/1.0',Accept:'application/json'}, signal:controller.signal });
        clearTimeout(timer);
        if (!response.ok) throw new Error(`${symbol} Yahoo HTTP ${response.status}`);
        return await response.json();
      } catch (error) { last=error; if (attempt<4) await sleep(attempt*1000); }
    }
  }
  throw last;
}
function parseYahoo(json, symbol) {
  const result = json?.chart?.result?.[0];
  if (!result) throw new Error(`${symbol} missing Yahoo chart result`);
  const q = result.indicators?.quote?.[0] ?? {};
  const out=[];
  for (let i=0; i<(result.timestamp??[]).length; i+=1) {
    const ts=Number(result.timestamp[i])*1000;
    const p=parts(ts);
    if (!((p.hm>='09:00'&&p.hm<'11:30')||(p.hm>='12:30'&&p.hm<'15:30'))) continue;
    const vals=[q.open?.[i],q.high?.[i],q.low?.[i],q.close?.[i]];
    if (vals.some(v=>v==null || !Number.isFinite(Number(v)))) continue;
    out.push({ timestamp:new Date(ts).toISOString(), open:Number(q.open[i]), high:Number(q.high[i]), low:Number(q.low[i]), close:Number(q.close[i]), volume:Number(q.volume?.[i]??0) });
  }
  return normalize(out);
}
async function fetchBars(symbol) {
  const end=Math.floor(Date.now()/1000), start=end-58*86400;
  const query=`period1=${start}&period2=${end}&interval=5m&includePrePost=false&events=div%2Csplits`;
  const urls=[1,2].map(host=>`https://query${host}.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?${query}`);
  return parseYahoo(await fetchJson(urls,symbol),symbol);
}
function summarize(rows,key) {
  const valid=rows.filter(r=>r[key]);
  const mean=vals=>vals.length?vals.reduce((a,b)=>a+Number(b),0)/vals.length:null;
  return { count:valid.length, hitRate:valid.length?valid.filter(r=>r[key].hit).length/valid.length:null, averageDirectionalReturnPct:valid.length?mean(valid.map(r=>r[key].directionalReturnPct)):null, averageMfePct:valid.length?mean(valid.map(r=>r[key].mfePct)):null, averageMaePct:valid.length?mean(valid.map(r=>r[key].maePct)):null };
}
function group(rows,keyFn) {
  const m=new Map();
  for (const row of rows) { const key=keyFn(row); if(!m.has(key))m.set(key,[]); m.get(key).push(row); }
  return Object.fromEntries([...m].map(([k,v])=>[k,{signalCount:v.length,outcome30m:summarize(v,'outcome30m'),outcome60m:summarize(v,'outcome60m')} ]));
}

const records=[];
const bySymbol={};
for (const symbol of symbols) {
  const bars=await fetchBars(symbol);
  let directional=0;
  for (let index=Math.max(24,minHistoryBars); index<bars.length-12; index+=Math.max(1,stepBars)) {
    const context=bars.slice(Math.max(0,index+1-2600),index+1);
    const perception=buildSessionAwareMultiTimeframePerception({bars5m:context});
    const setup=classifyHumanStyleSetup(perception);
    if (![1,-1].includes(Number(setup.directionSign))) continue;
    const future=bars.slice(index+1,index+13);
    const outcome30m=deriveSameSessionOutcome({entryBar:bars[index],futureBars:future,directionSign:setup.directionSign,horizonBars:6});
    const outcome60m=deriveSameSessionOutcome({entryBar:bars[index],futureBars:future,directionSign:setup.directionSign,horizonBars:12});
    if (!outcome30m && !outcome60m) continue;
    const quality=scoreHumanStyleSetupQuality(perception,setup);
    directional+=1;
    records.push({ symbol, featureCutoff:bars[index].timestamp, setup:setup.setup, direction:setup.directionSign===1?'UP':'DOWN', qualityScore:quality.score, qualityBand:qualityBand(quality.score), qualityComponents:quality.components, outcome30m, outcome60m });
  }
  bySymbol[symbol]={sourceBarCount:bars.length,directionalSetupCount:directional};
  console.log(JSON.stringify({symbol,sourceBarCount:bars.length,directionalSetupCount:directional}));
  await sleep(500);
}

const result={
  phase:'57.p23.10d-setup-quality-remeasurement',
  status:'SETUP_QUALITY_REMEASUREMENT_COMPLETE', symbols, symbolCount:symbols.length, totalDirectionalSetups:records.length,
  aggregate:{outcome30m:summarize(records,'outcome30m'),outcome60m:summarize(records,'outcome60m')},
  byQualityBand:group(records,r=>r.qualityBand),
  bySetupQualityBand:group(records,r=>`${r.setup}|${r.qualityBand}`),
  bySetup:group(records,r=>r.setup), bySymbol, records,
  methodology:{qualityScoreOutcomeTuned:false,qualityBandsPreRegisteredBeforeMeasurement:true,futureOutcomesEvaluationOnly:true,sessionAwareHigherTimeframes:true,sameSessionOutcomesOnly:true,developmentMeasurementOnly:true,finalUntouchedOos:false},
  edgeClaimAllowed:false,recommendationAllowed:false,transmitted:false,...PHASE57_CHART_PERCEPTION_SAFETY,
};
for (const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed']) if (result[key]!==false) throw new Error(`${key} must remain false`);
if (!records.length) throw new Error('no setup quality records produced');
fs.mkdirSync('artifacts',{recursive:true});
fs.writeFileSync('artifacts/phase57-p23-10d-setup-quality.json',JSON.stringify(result,null,2));
console.log(JSON.stringify({status:result.status,symbolCount:result.symbolCount,totalDirectionalSetups:result.totalDirectionalSetups,aggregate:result.aggregate,byQualityBand:result.byQualityBand},null,2));
