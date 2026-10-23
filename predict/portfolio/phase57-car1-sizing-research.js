export const PHASE57_CAR1_SAFETY=Object.freeze({
  phase:'57.car1.capital-allocation-sizing',
  mode:'READ_ONLY_CAUSAL_SIZING_RESEARCH',
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
  winnerSelectionAllowed:false,
});

export const PHASE57_CAR1_PROFILES=Object.freeze([
  Object.freeze({id:'EQUAL_NOTIONAL',riskMetric:null}),
  Object.freeze({id:'INVERSE_ATR',riskMetric:'ATR_PCT'}),
  Object.freeze({id:'INVERSE_REALIZED_VOL',riskMetric:'REALIZED_VOL'}),
]);

export const PHASE57_CAR1_POLICY=Object.freeze({
  priorityRule:'ENTRY_TIMESTAMP_ASC_SYMBOL_ASC',
  entrySet:'FROZEN_UNCHANGED',
  exitSet:'FROZEN_UNCHANGED',
  costAssumption:'INHERIT_LANE_C_BASELINE',
  lotSize:100,
  atrLookbackBars:14,
  realizedVolLookbackBars:14,
  futureBarsAllowed:false,
  currentBarAllowed:true,
  futureOutcomeVisible:false,
  parameterSearchAllowed:false,
  automaticPromotionAllowed:false,
});

const finite=value=>Number.isFinite(Number(value));
const iso=value=>{
  const ms=Date.parse(String(value??''));
  if(!Number.isFinite(ms))throw new Error(`invalid timestamp: ${value??'MISSING'}`);
  return new Date(ms).toISOString();
};

function normalizeBar(raw){
  const timestamp=iso(raw?.timestamp??raw?.time);
  const open=Number(raw?.open),high=Number(raw?.high),low=Number(raw?.low),close=Number(raw?.close);
  if(![open,high,low,close].every(value=>Number.isFinite(value)&&value>0))throw new Error(`invalid OHLC at ${timestamp}`);
  if(high<Math.max(open,close)||low>Math.min(open,close)||high<low)throw new Error(`invalid OHLC ordering at ${timestamp}`);
  return Object.freeze({timestamp,open,high,low,close});
}

export function buildCausalRiskSnapshot({bars,entryTimestamp,atrLookbackBars=PHASE57_CAR1_POLICY.atrLookbackBars,realizedVolLookbackBars=PHASE57_CAR1_POLICY.realizedVolLookbackBars}={}){
  const cutoff=iso(entryTimestamp);
  const ordered=(Array.isArray(bars)?bars:[]).map(normalizeBar).sort((a,b)=>a.timestamp.localeCompare(b.timestamp));
  if(new Set(ordered.map(row=>row.timestamp)).size!==ordered.length)throw new Error('duplicate bars');
  if(ordered.some(row=>row.timestamp>cutoff))throw new Error('future bar supplied to CAR-1 risk snapshot');
  const usable=ordered.filter(row=>row.timestamp<=cutoff);
  const needed=Math.max(Number(atrLookbackBars)+1,Number(realizedVolLookbackBars)+1);
  if(usable.length<needed)throw new Error(`insufficient causal history: need ${needed}, got ${usable.length}`);

  const atrWindow=usable.slice(-(Number(atrLookbackBars)+1));
  const trueRanges=[];
  for(let i=1;i<atrWindow.length;i++){
    const row=atrWindow[i],prev=atrWindow[i-1];
    trueRanges.push(Math.max(row.high-row.low,Math.abs(row.high-prev.close),Math.abs(row.low-prev.close)));
  }
  const atr=trueRanges.reduce((sum,value)=>sum+value,0)/trueRanges.length;
  const lastClose=usable.at(-1).close;
  const atrPct=atr/lastClose;

  const volWindow=usable.slice(-(Number(realizedVolLookbackBars)+1));
  const returns=[];
  for(let i=1;i<volWindow.length;i++)returns.push(Math.log(volWindow[i].close/volWindow[i-1].close));
  const mean=returns.reduce((sum,value)=>sum+value,0)/returns.length;
  const variance=returns.length>1?returns.reduce((sum,value)=>sum+(value-mean)**2,0)/(returns.length-1):0;
  const realizedVol=Math.sqrt(variance);

  if(!finite(atrPct)||atrPct<=0)throw new Error('non-positive causal ATR percent');
  if(!finite(realizedVol)||realizedVol<=0)throw new Error('non-positive causal realized volatility');

  return Object.freeze({
    asOfTimestamp:cutoff,
    barsUsed:usable.length,
    lastClose,
    atr,
    atrPct,
    realizedVol,
    futureOutcomeUsed:false,
    futureBarUsed:false,
  });
}

export function rawSizingScore({profileId,riskSnapshot}={}){
  if(profileId==='EQUAL_NOTIONAL')return 1;
  if(!riskSnapshot||riskSnapshot.futureBarUsed!==false||riskSnapshot.futureOutcomeUsed!==false)throw new Error('causal risk snapshot required');
  if(profileId==='INVERSE_ATR')return 1/Number(riskSnapshot.atrPct);
  if(profileId==='INVERSE_REALIZED_VOL')return 1/Number(riskSnapshot.realizedVol);
  throw new Error(`unknown CAR-1 profile: ${profileId}`);
}

export function normalizeSizingWeights({profileId,candidates}={}){
  const rows=(Array.isArray(candidates)?candidates:[]).map(row=>({
    key:String(row?.key??''),
    score:rawSizingScore({profileId,riskSnapshot:row?.riskSnapshot}),
  }));
  if(rows.length===0)return Object.freeze([]);
  if(rows.some(row=>!row.key||!finite(row.score)||row.score<=0))throw new Error('invalid CAR-1 sizing candidate');
  const total=rows.reduce((sum,row)=>sum+row.score,0);
  return Object.freeze(rows.map(row=>Object.freeze({key:row.key,weight:row.score/total})));
}
