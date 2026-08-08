import { writeFile } from 'node:fs/promises';
import { evaluateChartAccuracy } from '../chart/phase56-accuracy-baseline.js';

const symbols = ['7203.T','6758.T','9984.T','8306.T','8035.T'];
const range = '5y';
const interval = '1d';

async function fetchCandles(symbol) {
  const url = `https://query2.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?range=${range}&interval=${interval}&events=div%2Csplits`;
  const res = await fetch(url, { headers: { 'User-Agent': 'Mozilla/5.0 (compatible; ArkTerminal/3.0)', Accept: 'application/json' } });
  if (!res.ok) throw new Error(`${symbol}: Yahoo HTTP ${res.status}`);
  const payload = await res.json();
  const result = payload?.chart?.result?.[0];
  if (!result) throw new Error(`${symbol}: no chart result`);
  const q = result.indicators?.quote?.[0] ?? {};
  const adj = result.indicators?.adjclose?.[0]?.adjclose ?? [];
  return (result.timestamp ?? []).map((time, i) => {
    const o = Number(q.open?.[i]), h = Number(q.high?.[i]), l = Number(q.low?.[i]), c = Number(q.close?.[i]), a = Number(adj?.[i]);
    if (![o,h,l,c].every(Number.isFinite) || c <= 0) return null;
    const factor = Number.isFinite(a) && a > 0 ? a / c : 1;
    return { time:Number(time), open:o*factor, high:h*factor, low:l*factor, close:c*factor, volume:Number(q.volume?.[i]) || 0 };
  }).filter(Boolean);
}

const results = [];
for (const symbol of symbols) {
  try {
    const candles = await fetchCandles(symbol);
    const baseline = evaluateChartAccuracy({ candles, lookback:80, horizons:[1,3,5,10,20], minimumSignals:30 });
    results.push({ symbol, candles:candles.length, ...baseline });
  } catch (error) {
    results.push({ symbol, error:String(error?.message ?? error) });
  }
}

function aggregate(horizon) {
  const usable = results.filter(r => !r.error).map(r => r.byHorizon.find(x => x.horizon===horizon)).filter(Boolean).filter(x => x.samples>0);
  const samples = usable.reduce((s,x)=>s+x.samples,0);
  const hitRate = samples ? usable.reduce((s,x)=>s+x.hitRate*x.samples,0)/samples : null;
  const meanAlignedReturn = samples ? usable.reduce((s,x)=>s+x.meanAlignedReturn*x.samples,0)/samples : null;
  return { horizon, samples, hitRate, meanAlignedReturn };
}
const aggregateByHorizon = [1,3,5,10,20].map(aggregate);
const report = { generatedAt:new Date().toISOString(), source:'Yahoo Finance public chart endpoint', range, interval, symbols, aggregateByHorizon, results };
await writeFile('phase56-real-baseline.json', JSON.stringify(report,null,2));
console.log('PHASE56_REAL_BASELINE_START');
console.log(JSON.stringify(report));
console.log('PHASE56_REAL_BASELINE_END');
