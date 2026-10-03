import crypto from 'node:crypto';

export const PHASE57_EXIT_V4_LARGE_SCALE_SAFETY=Object.freeze({
  phase:'57.exit-v4.large-scale',
  mode:'READ_ONLY_HISTORICAL_RECONSTRUCTION',
  researchOnly:true,
  executionAllowed:false,
  brokerWriteAllowed:false,
  excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,
  paperTradingAllowed:false,
  automaticPromotionAllowed:false,
  productionUpdateAllowed:false,
  transmitted:false,
});

export const PHASE57_EXIT_V4_LARGE_SCALE_CONTRACT=Object.freeze({
  frozenPolicy:'P25_EXIT_V4_POLICY',
  evaluationRole:'HISTORICAL_RECONSTRUCTION_STRESS_DIAGNOSTIC',
  formalOosEvidence:false,
  prospectiveEvidence:false,
  currentUniverseSurvivorshipBias:true,
  outcomeBasedUniverseSelection:false,
  analogPoolRefitAllowed:false,
  entryRetuningAllowed:false,
  exitRetuningAllowed:false,
  fixedEntryHmJst:'10:30',
  contextBars:12,
  momentumLookbackBars:6,
  maximumFutureBars:24,
  roundTripCostPct:0.05,
  pilot:Object.freeze({size:50,quotas:Object.freeze({'プライム':24,'スタンダード':16,'グロース':10})}),
  expansion:Object.freeze({size:500,quotas:Object.freeze({'プライム':240,'スタンダード':160,'グロース':100})}),
});

const sha=value=>crypto.createHash('sha256').update(typeof value==='string'?value:JSON.stringify(value)).digest('hex');
const normalizeSymbol=value=>String(value??'').trim().toUpperCase();

function rank(seed,item){
  return sha(`${seed}\n${item.market}\n${item.symbol}`);
}

function normalizeUniverse(universe=[]){
  const rows=(Array.isArray(universe)?universe:universe?.entries??[]).map(row=>({
    symbol:normalizeSymbol(row?.symbol),
    code:String(row?.code??'').trim(),
    name:String(row?.name??'').trim(),
    market:String(row?.market??'').trim(),
    sector:String(row?.sector??'未分類').trim()||'未分類',
  })).filter(row=>row.symbol&&row.market);
  const unique=new Map();
  for(const row of rows){
    if(unique.has(row.symbol))throw new Error(`duplicate universe symbol: ${row.symbol}`);
    unique.set(row.symbol,row);
  }
  return [...unique.values()].sort((a,b)=>a.symbol.localeCompare(b.symbol));
}

export function buildFrozenExitV4Universe({universe,seed='phase57-exit-v4-large-scale-v1'}={}){
  const source=normalizeUniverse(universe);
  const select=spec=>{
    const selected=[];
    for(const [market,count] of Object.entries(spec.quotas)){
      const candidates=source.filter(row=>row.market===market).map(row=>({...row,selectionRankSha256:rank(seed,row)}))
        .sort((a,b)=>a.selectionRankSha256.localeCompare(b.selectionRankSha256)||a.symbol.localeCompare(b.symbol));
      if(candidates.length<count)throw new Error(`universe has only ${candidates.length} ${market} rows; ${count} required`);
      selected.push(...candidates.slice(0,count));
    }
    selected.sort((a,b)=>a.selectionRankSha256.localeCompare(b.selectionRankSha256)||a.symbol.localeCompare(b.symbol));
    if(selected.length!==spec.size||new Set(selected.map(x=>x.symbol)).size!==spec.size)throw new Error(`invalid frozen selection size: ${selected.length}`);
    return Object.freeze(selected.map(Object.freeze));
  };
  const pilot=select(PHASE57_EXIT_V4_LARGE_SCALE_CONTRACT.pilot);
  const expansion=select(PHASE57_EXIT_V4_LARGE_SCALE_CONTRACT.expansion);
  const manifest={
    schemaVersion:1,
    phase:'57.exit-v4.large-scale',
    status:'FROZEN_UNIVERSE_READY',
    seed,
    sourceUniverseRowCount:source.length,
    sourceUniverseSha256:sha(source),
    pilot,
    expansion,
    methodology:PHASE57_EXIT_V4_LARGE_SCALE_CONTRACT,
    safety:PHASE57_EXIT_V4_LARGE_SCALE_SAFETY,
  };
  return Object.freeze({...manifest,manifestSha256:sha(manifest)});
}

const JST=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tokyo',hour:'2-digit',minute:'2-digit',hourCycle:'h23'});
function hmJst(timestamp){
  const parts=Object.fromEntries(JST.formatToParts(new Date(timestamp)).map(x=>[x.type,x.value]));
  return `${parts.hour}:${parts.minute}`;
}
function normalizeBars(rows=[]){
  return rows.map(row=>({timestamp:new Date(Date.parse(row.timestamp??row.time)).toISOString(),open:Number(row.open),high:Number(row.high),low:Number(row.low),close:Number(row.close),volume:Number(row.volume??0)}))
    .filter(row=>[row.open,row.high,row.low,row.close,row.volume].every(Number.isFinite)&&row.close>0)
    .sort((a,b)=>a.timestamp.localeCompare(b.timestamp));
}

export function buildExitV4StressProbe({session,entryHmJst=PHASE57_EXIT_V4_LARGE_SCALE_CONTRACT.fixedEntryHmJst}={}){
  const bars=normalizeBars(session?.bars??session?.bars5m??[]);
  const entryIndex=bars.findIndex(bar=>hmJst(bar.timestamp)===entryHmJst);
  const contextCount=PHASE57_EXIT_V4_LARGE_SCALE_CONTRACT.contextBars;
  const lookback=PHASE57_EXIT_V4_LARGE_SCALE_CONTRACT.momentumLookbackBars;
  const futureCount=PHASE57_EXIT_V4_LARGE_SCALE_CONTRACT.maximumFutureBars;
  if(entryIndex<contextCount||entryIndex+futureCount>=bars.length)return Object.freeze({ready:false,status:'BLOCKED_INSUFFICIENT_PROBE_BARS',symbol:normalizeSymbol(session?.symbol),sessionDate:String(session?.sessionDate??''),entryIndex,barCount:bars.length});
  const entry=bars[entryIndex],prior=bars[entryIndex-lookback];
  const signalDirection=entry.close>=prior.close?'LONG':'SHORT';
  const contextBars=bars.slice(entryIndex-contextCount,entryIndex);
  const futureBars=bars.slice(entryIndex+1,entryIndex+1+futureCount);
  const row={
    probeId:`${normalizeSymbol(session?.symbol)}:${String(session?.sessionDate??'')}:${entryHmJst}`,
    symbol:normalizeSymbol(session?.symbol),
    sessionDate:String(session?.sessionDate??''),
    entryTimestamp:entry.timestamp,
    entryPrice:entry.close,
    signalDirection,
    contextBars:Object.freeze(contextBars),
    futureBars:Object.freeze(futureBars),
    entryAccepted:true,
    frozenBeforeOutcome:true,
    currentOutcomeUsed:false,
    selection:'DETERMINISTIC_CROSS_SECTIONAL_STRESS_PROBE',
    directionRule:'LONG when entry close >= close six observed bars earlier; otherwise SHORT',
  };
  return Object.freeze({ready:true,status:'V4_STRESS_PROBE_READY',row:Object.freeze(row),rowSha256:sha(row)});
}

export function assertExitV4PairedIdentity({probe,v4,fixed}={}){
  if(!probe?.probeId||!v4||!fixed)throw new Error('paired comparison requires probe, v4, and fixed records');
  const fields=['probeId','symbol','sessionDate','entryTimestamp','entryPrice','signalDirection','marketDataSha256','roundTripCostPct','allocationUnits'];
  for(const field of fields){
    const values=[probe?.[field],v4?.[field],fixed?.[field]];
    if(!values.every(value=>Object.is(value,values[0])))throw new Error(`paired identity mismatch: ${field}`);
  }
  return Object.freeze({ready:true,status:'V4_PAIRED_IDENTITY_CONFIRMED',fields:Object.freeze(fields)});
}

export function simulateFixedProbeExit({row,roundTripCostPct=PHASE57_EXIT_V4_LARGE_SCALE_CONTRACT.roundTripCostPct}={}){
  const future=normalizeBars(row?.futureBars??[]);
  if(!future.length)throw new Error('fixed probe EXIT requires futureBars');
  const sign=row?.signalDirection==='LONG'?1:-1,exit=future.at(-1),gross=(exit.close/Number(row.entryPrice)-1)*100*sign;
  const mfe=Math.max(0,...future.map(bar=>(Number(row.signalDirection==='LONG'?bar.high:bar.low)/Number(row.entryPrice)-1)*100*sign));
  const mae=Math.min(0,...future.map(bar=>(Number(row.signalDirection==='LONG'?bar.low:bar.high)/Number(row.entryPrice)-1)*100*sign));
  return Object.freeze({exitTimestamp:exit.timestamp,exitPrice:exit.close,exitReason:'FIXED_24_BAR_EXIT',barsHeld:future.length,grossReturnPct:gross,netReturnPct:gross-Number(roundTripCostPct),mfePct:mfe,maePct:mae,givebackPct:Math.max(0,mfe-gross),captureRatio:mfe>0?gross/mfe:null});
}

export function summarizeExitV4LargeScale(records=[]){
  const rows=Array.isArray(records)?records:[];
  const byVariant={};
  for(const variant of [...new Set(rows.map(x=>x.variant))].sort()){
    const xs=rows.filter(x=>x.variant===variant),returns=xs.map(x=>Number(x.netReturnPct)).filter(Number.isFinite);
    const wins=returns.filter(x=>x>0),losses=returns.filter(x=>x<0),grossProfit=wins.reduce((a,b)=>a+b,0),grossLoss=-losses.reduce((a,b)=>a+b,0);
    byVariant[variant]=Object.freeze({n:returns.length,netReturnPct:returns.reduce((a,b)=>a+b,0),averageTradePct:returns.length?returns.reduce((a,b)=>a+b,0)/returns.length:null,winRate:returns.length?wins.length/returns.length:null,profitFactor:grossLoss>0?grossProfit/grossLoss:null,averageBarsHeld:xs.length?xs.reduce((s,x)=>s+Number(x.barsHeld??0),0)/xs.length:null});
  }
  return Object.freeze({status:'V4_LARGE_SCALE_SUMMARY_READY',pairCount:new Set(rows.map(x=>x.probeId)).size,recordCount:rows.length,variants:Object.freeze(byVariant),methodology:PHASE57_EXIT_V4_LARGE_SCALE_CONTRACT,safety:PHASE57_EXIT_V4_LARGE_SCALE_SAFETY});
}

export default {buildFrozenExitV4Universe,buildExitV4StressProbe,assertExitV4PairedIdentity,simulateFixedProbeExit,summarizeExitV4LargeScale,PHASE57_EXIT_V4_LARGE_SCALE_CONTRACT,PHASE57_EXIT_V4_LARGE_SCALE_SAFETY};
