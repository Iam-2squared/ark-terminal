#!/usr/bin/env node
import fs from 'node:fs';

const args = process.argv.slice(2);
const get = (k) => {
  const i = args.indexOf(k);
  return i >= 0 ? args[i + 1] : null;
};
const snapshotPath = get('--snapshot');
const outputPath = get('--output');
if (!snapshotPath || !outputPath) {
  console.error('usage: node scripts/evaluate_phase57_us_postclose_selection.mjs --snapshot <json> --output <json>');
  process.exit(2);
}

const snapshot = JSON.parse(fs.readFileSync(snapshotPath, 'utf8'));
if (snapshot.status !== 'US_SAMPLED_5M_DIAGNOSTIC_MEASURED') throw new Error(`unexpected snapshot status ${snapshot.status}`);
if (snapshot.sampledDiagnostic !== true && snapshot.sampleDiagnostic !== true) throw new Error('snapshot is not sampled diagnostic evidence');
if (snapshot.marketwide !== false) throw new Error('marketwide evidence required to remain false for this evaluator');
if (!Array.isArray(snapshot.selected) || snapshot.selected.length === 0) throw new Error('selected candidates missing');

const sessionDate = snapshot.sessionDate;
const observedAtMs = Date.parse(snapshot.observedAt);
if (!Number.isFinite(observedAtMs)) throw new Error('invalid observedAt');

const safety = {
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  transmitted: false,
  freshHoldoutConsumed: false
};

const etParts = (ms) => Object.fromEntries(new Intl.DateTimeFormat('en-CA', {
  timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23'
}).formatToParts(new Date(ms)).map(x => [x.type, x.value]));
const etDate = (ms) => { const p = etParts(ms); return `${p.year}-${p.month}-${p.day}`; };
const etHm = (ms) => { const p = etParts(ms); return `${p.hour}:${p.minute}`; };

async function fetchChart(symbol) {
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?range=1d&interval=5m&includePrePost=false&events=div%2Csplits`;
  const r = await fetch(url, { headers: { 'user-agent': 'Mozilla/5.0 Ark-Terminal-Research' } });
  if (!r.ok) throw new Error(`${symbol} HTTP ${r.status}`);
  const j = await r.json();
  const result = j?.chart?.result?.[0];
  if (!result) throw new Error(`${symbol} chart missing`);
  const ts = result.timestamp || [];
  const q = result.indicators?.quote?.[0] || {};
  const adj = result.indicators?.adjclose?.[0]?.adjclose || [];
  const rows = [];
  for (let i = 0; i < ts.length; i++) {
    const ms = ts[i] * 1000;
    if (etDate(ms) !== sessionDate) continue;
    const hm = etHm(ms);
    if (hm < '09:30' || hm >= '16:00') continue;
    const close = Number.isFinite(q.close?.[i]) ? q.close[i] : adj[i];
    if (!Number.isFinite(close) || close <= 0) continue;
    rows.push({ ms, hm, close });
  }
  return rows;
}

async function mapLimit(items, limit, fn) {
  const out = new Array(items.length);
  let next = 0;
  async function worker() {
    while (true) {
      const i = next++;
      if (i >= items.length) return;
      try { out[i] = await fn(items[i], i); }
      catch (e) { out[i] = { error: String(e?.message || e), symbol: items[i]?.symbol }; }
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, () => worker()));
  return out;
}

const candidates = snapshot.selected.map((x, i) => ({
  symbol: x.symbol,
  rank: i + 1,
  snapshotPrice: Number(x.currentPrice),
  opportunityScore: Number(x.usOpportunityScore)
})).filter(x => x.symbol && Number.isFinite(x.snapshotPrice) && x.snapshotPrice > 0);

const evaluated = await mapLimit(candidates, 6, async (c) => {
  const rows = await fetchChart(c.symbol);
  if (!rows.length) throw new Error(`${c.symbol} no regular-session rows`);
  const entry = rows.find(r => r.ms >= observedAtMs - 6 * 60_000) || rows.find(r => r.ms >= observedAtMs) || rows[0];
  const close = rows[rows.length - 1];
  if (!entry || !close || close.ms <= entry.ms) throw new Error(`${c.symbol} insufficient post-snapshot rows`);
  const returnPct = (close.close / c.snapshotPrice - 1) * 100;
  return {
    symbol: c.symbol,
    rank: c.rank,
    opportunityScore: c.opportunityScore,
    snapshotPrice: c.snapshotPrice,
    firstAvailable5mClose: entry.close,
    firstAvailable5mHmEt: entry.hm,
    sessionClose: close.close,
    sessionCloseHmEt: close.hm,
    returnPct
  };
});

function summarize(rows) {
  const good = rows.filter(x => x && !x.error && Number.isFinite(x.returnPct));
  const vals = good.map(x => x.returnPct).sort((a,b) => a-b);
  const n = vals.length;
  const mean = n ? vals.reduce((a,b)=>a+b,0)/n : null;
  const median = n ? (n % 2 ? vals[(n-1)/2] : (vals[n/2-1]+vals[n/2])/2) : null;
  const wins = vals.filter(x => x > 0);
  const losses = vals.filter(x => x < 0);
  const grossWin = wins.reduce((a,b)=>a+b,0);
  const grossLoss = losses.reduce((a,b)=>a+Math.abs(b),0);
  return {
    n,
    requested: rows.length,
    dataCoveragePct: rows.length ? n / rows.length * 100 : 0,
    equalWeightReturnPct: mean,
    meanReturnPctPerCandidate: mean,
    medianReturnPctPerCandidate: median,
    winRatePct: n ? wins.length / n * 100 : null,
    profitFactor: grossLoss > 0 ? grossWin / grossLoss : null,
    bestReturnPct: n ? vals[n-1] : null,
    worstReturnPct: n ? vals[0] : null
  };
}

const v1Rows = evaluated;
const v2N = Math.min(Number(snapshot.selectedV2Symbols) || 30, evaluated.length);
const v2Rows = evaluated.slice(0, v2N);
const errors = evaluated.filter(x => x?.error).map(x => ({ symbol: x.symbol, error: x.error }));

const output = {
  schemaVersion: 1,
  phase: '57.us-cross-market.postclose-selection',
  status: 'US_SAMPLED_POSTCLOSE_SELECTION_DIAGNOSTIC_MEASURED',
  sessionDate,
  sourceSnapshotObservedAt: snapshot.observedAt,
  evidenceClass: 'SAMPLED_POSTCLOSE_DIAGNOSTIC',
  researchOnly: true,
  sampledDiagnostic: true,
  marketwide: false,
  fullFresh: false,
  formalOos: false,
  promotionEligible: false,
  methodology: {
    measurement: 'SNAPSHOT_CURRENT_PRICE_TO_REGULAR_SESSION_FINAL_5M_CLOSE',
    currencyConversion: false,
    capitalAllocationSimulation: false,
    noOutcomeRetuning: true,
    note: 'Measures selection follow-through only. This is not EXIT v3/v4 evaluation and is not a JPX formal OOS substitute.'
  },
  results: {
    dynamicV1Top50: summarize(v1Rows),
    dynamicV2Top30: summarize(v2Rows)
  },
  rows: evaluated.filter(x => x && !x.error),
  errors,
  safety
};

fs.mkdirSync(new URL('.', `file://${outputPath}`).pathname, { recursive: true });
fs.writeFileSync(outputPath, JSON.stringify(output, null, 2));
console.log(JSON.stringify({ status: output.status, sessionDate, v1: output.results.dynamicV1Top50, v2: output.results.dynamicV2Top30, errors: errors.length }));
