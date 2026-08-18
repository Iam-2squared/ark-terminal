export const PHASE57_P25_2_SAFETY=Object.freeze({
  phase:'57.p25.2.trade-frequency-oos-expansion',
  mode:'READ_ONLY_PRECOMMITTED_OOS_COMPARISON',
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
  freshHoldoutConsumed:false,
});

export const PHASE57_P25_2_VARIANTS=Object.freeze([
  Object.freeze({id:'FIXED_5',kind:'FIXED',count:5}),
  Object.freeze({id:'OLD_FIXED_30',kind:'FIXED',count:30}),
  Object.freeze({id:'DYNAMIC_30',kind:'DYNAMIC',count:30}),
  Object.freeze({id:'DYNAMIC_40',kind:'DYNAMIC',count:40}),
  Object.freeze({id:'DYNAMIC_50',kind:'DYNAMIC',count:50}),
]);

export const PHASE57_P25_2_POLICY=Object.freeze({
  phase57Default:'FIXED_HORIZON_BASELINE',
  entryThresholdRelaxationAllowed:false,
  outerOosUniverseSizeSelectionAllowed:false,
  postHocWinnerFilteringAllowed:false,
  currentOosThresholdSearchAllowed:false,
  commonTemporalWindowRequired:true,
  sameTimeCorrelationAuditRequired:true,
  sessionEqualWeightPortfolioRequired:true,
  preserveBadOosResults:true,
});

const finite=value=>value!==null&&value!==undefined&&value!==''&&Number.isFinite(Number(value));
const mean=xs=>xs.length?xs.reduce((s,x)=>s+x,0)/xs.length:null;
const round=(value,digits=6)=>Number.isFinite(value)?Number(value.toFixed(digits)):value;

function normalizeEntry(row,index){
  if(!row||row.entryAccepted!==true)return null;
  const symbol=String(row.symbol??'').trim().toUpperCase();
  const sessionDate=String(row.sessionDate??'').trim();
  const entryTimestamp=String(row.entryTimestamp??row.featureCutoff??'').trim();
  if(!symbol||!sessionDate||!entryTimestamp)return null;
  const sector=String(row.sector??'UNKNOWN').trim()||'UNKNOWN';
  const netReturnPct=finite(row.netReturnPct)?Number(row.netReturnPct):null;
  const alignedReturnPct=finite(row.alignedReturnPct)?Number(row.alignedReturnPct):
    finite(row.grossReturnPct)?Number(row.grossReturnPct):netReturnPct;
  return Object.freeze({
    index,
    symbol,
    sector,
    sessionDate,
    entryTimestamp,
    timeBucket:String(row.timeBucket??'UNKNOWN'),
    regime:String(row.regime??'UNKNOWN'),
    hit:typeof row.hit==='boolean'?row.hit:null,
    netReturnPct,
    alignedReturnPct,
  });
}

function compoundSummary(returns){
  const rs=returns.filter(Number.isFinite);
  let equity=1,peak=1,maxDrawdownPct=0,grossProfit=0,grossLoss=0;
  for(const r of rs){
    equity*=1+r/100;
    peak=Math.max(peak,equity);
    maxDrawdownPct=Math.max(maxDrawdownPct,(peak-equity)/peak*100);
    if(r>0)grossProfit+=r;
    else if(r<0)grossLoss-=r;
  }
  return Object.freeze({
    n:rs.length,
    afterCostNetPct:round((equity-1)*100),
    finalEquity:round(equity),
    meanNetReturnPct:round(mean(rs)),
    profitFactor:grossLoss>0?round(grossProfit/grossLoss):(grossProfit>0?Infinity:null),
    winRate:rs.length?round(rs.filter(x=>x>0).length/rs.length):null,
    maxDrawdownPct:round(maxDrawdownPct),
  });
}

function concentration(entries,key){
  if(!entries.length)return Object.freeze({largestShare:null,hhi:null,counts:Object.freeze({})});
  const counts=new Map();
  for(const row of entries){const k=String(row[key]??'UNKNOWN');counts.set(k,(counts.get(k)??0)+1);}
  const shares=[...counts.values()].map(n=>n/entries.length);
  return Object.freeze({
    largestShare:round(Math.max(...shares)),
    hhi:round(shares.reduce((s,x)=>s+x*x,0)),
    counts:Object.freeze(Object.fromEntries([...counts].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0])))),
  });
}

function groupedPerformance(entries,key){
  const groups=new Map();
  for(const row of entries){
    const k=String(row[key]??'UNKNOWN');
    if(!groups.has(k))groups.set(k,[]);
    groups.get(k).push(row);
  }
  return Object.freeze(Object.fromEntries([...groups].sort(([a],[b])=>a.localeCompare(b)).map(([k,rows])=>{
    const resolved=rows.filter(r=>Number.isFinite(r.netReturnPct));
    const perf=compoundSummary(resolved.map(r=>r.netReturnPct));
    return [k,Object.freeze({entries:rows.length,resolved:resolved.length,...perf})];
  })));
}

function pearson(xs,ys){
  if(xs.length!==ys.length||xs.length<3)return null;
  const mx=mean(xs),my=mean(ys);
  let num=0,dx=0,dy=0;
  for(let i=0;i<xs.length;i+=1){const a=xs[i]-mx,b=ys[i]-my;num+=a*b;dx+=a*a;dy+=b*b;}
  if(dx<=0||dy<=0)return null;
  return num/Math.sqrt(dx*dy);
}

function sameTimeAudit(entries){
  const clusters=new Map();
  for(const row of entries){
    if(!clusters.has(row.entryTimestamp))clusters.set(row.entryTimestamp,[]);
    clusters.get(row.entryTimestamp).push(row);
  }
  const clusterSizes=[...clusters.values()].map(xs=>xs.length);
  const multiSignalEntries=clusterSizes.filter(n=>n>1).reduce((s,n)=>s+n,0);
  let duplicateSameTimeSymbolRows=0;
  const pairSeries=new Map();
  for(const rows of clusters.values()){
    const bySymbol=new Map();
    for(const row of rows){
      if(bySymbol.has(row.symbol)){duplicateSameTimeSymbolRows+=1;continue;}
      if(Number.isFinite(row.alignedReturnPct))bySymbol.set(row.symbol,row.alignedReturnPct);
    }
    const symbols=[...bySymbol.keys()].sort();
    for(let i=0;i<symbols.length;i+=1){for(let j=i+1;j<symbols.length;j+=1){
      const a=symbols[i],b=symbols[j],key=`${a}|${b}`;
      if(!pairSeries.has(key))pairSeries.set(key,{a:[],b:[]});
      const series=pairSeries.get(key);series.a.push(bySymbol.get(a));series.b.push(bySymbol.get(b));
    }}
  }
  const pairwise=[];
  for(const [pair,series] of pairSeries){
    const correlation=pearson(series.a,series.b);
    if(correlation===null)continue;
    pairwise.push(Object.freeze({pair,overlaps:series.a.length,correlation:round(correlation)}));
  }
  pairwise.sort((a,b)=>b.overlaps-a.overlaps||b.correlation-a.correlation||a.pair.localeCompare(b.pair));
  const weights=pairwise.reduce((s,x)=>s+x.overlaps,0);
  const weightedMeanAbsCorrelation=weights?pairwise.reduce((s,x)=>s+Math.abs(x.correlation)*x.overlaps,0)/weights:null;
  return Object.freeze({
    clusterCount:clusters.size,
    largestClusterSize:clusterSizes.length?Math.max(...clusterSizes):0,
    multiSignalEntryShare:entries.length?round(multiSignalEntries/entries.length):null,
    conservativeEffectiveIndependentEntries:clusters.size,
    conservativeIndependenceRatio:entries.length?round(clusters.size/entries.length):null,
    duplicateSameTimeSymbolRows,
    pairCount:pairwise.length,
    weightedMeanAbsCorrelation:round(weightedMeanAbsCorrelation),
    maxAbsCorrelation:pairwise.length?round(Math.max(...pairwise.map(x=>Math.abs(x.correlation)))):null,
    pairwise:Object.freeze(pairwise),
  });
}

function sessionEqualWeightPortfolio(entries,evaluatedSessions){
  const grouped=new Map();
  for(const row of entries){
    if(!Number.isFinite(row.netReturnPct))continue;
    if(!grouped.has(row.sessionDate))grouped.set(row.sessionDate,[]);
    grouped.get(row.sessionDate).push(row.netReturnPct);
  }
  const sessions=[...new Set(evaluatedSessions)].sort();
  const returns=sessions.map(sessionDate=>({sessionDate,returnPct:mean(grouped.get(sessionDate)??[])??0}));
  const perf=compoundSummary(returns.map(x=>x.returnPct));
  return Object.freeze({...perf,sessions:Object.freeze(returns.map(x=>Object.freeze({sessionDate:x.sessionDate,returnPct:round(x.returnPct)})))});
}

function daysToTarget(entries,evaluatedSessions,target=400){
  const counts=new Map();
  for(const row of entries)counts.set(row.sessionDate,(counts.get(row.sessionDate)??0)+1);
  let cumulative=0,observed=null;
  const sessions=[...new Set(evaluatedSessions)].sort();
  for(let i=0;i<sessions.length;i+=1){
    cumulative+=counts.get(sessions[i])??0;
    if(cumulative>=target){observed=i+1;break;}
  }
  const pace=sessions.length?entries.length/sessions.length:0;
  return Object.freeze({
    target,
    observedDays:observed,
    entriesPerTradingSession:round(pace),
    paceEstimatedDays:pace>0?round(target/pace,3):null,
  });
}

export function summarizeP252TradeFrequencyVariant({
  variant,
  trades=[],
  evaluatedSessions=[],
  eligibleDecisionCount=null,
}={}){
  const variantSpec=PHASE57_P25_2_VARIANTS.find(x=>x.id===variant);
  if(!variantSpec)throw new TypeError(`unknown P25.2 variant: ${variant}`);
  const input=Array.isArray(trades)?trades:[];
  const entries=input.map(normalizeEntry).filter(Boolean).sort((a,b)=>a.entryTimestamp.localeCompare(b.entryTimestamp)||a.symbol.localeCompare(b.symbol));
  const sessions=[...new Set((Array.isArray(evaluatedSessions)?evaluatedSessions:[]).map(String).filter(Boolean))];
  if(!sessions.length)sessions.push(...new Set(entries.map(x=>x.sessionDate)));
  sessions.sort();
  const resolved=entries.filter(x=>Number.isFinite(x.netReturnPct));
  const perf=compoundSummary(resolved.map(x=>x.netReturnPct));
  const hitRows=entries.filter(x=>typeof x.hit==='boolean');
  const coverage=finite(eligibleDecisionCount)&&Number(eligibleDecisionCount)>0?entries.length/Number(eligibleDecisionCount):null;
  return Object.freeze({
    phase:'57.p25.2.trade-frequency-oos-expansion',
    status:'PRECOMMITTED_VARIANT_MEASURED',
    variant:Object.freeze({...variantSpec}),
    inputRows:input.length,
    validFrozenEntries:entries.length,
    resolvedOutcomes:resolved.length,
    evaluatedTradingSessions:sessions.length,
    tradeFrequency:daysToTarget(entries,sessions,400),
    hitRate:hitRows.length?round(hitRows.filter(x=>x.hit).length/hitRows.length):null,
    tradeWinRate:perf.winRate,
    afterCostNetPct:perf.afterCostNetPct,
    profitFactor:perf.profitFactor,
    maxDrawdownPct:perf.maxDrawdownPct,
    meanNetReturnPct:perf.meanNetReturnPct,
    coverage:round(coverage),
    coverageDenominator:finite(eligibleDecisionCount)?Number(eligibleDecisionCount):null,
    symbolConcentration:concentration(entries,'symbol'),
    sectorConcentration:concentration(entries,'sector'),
    sameTimeCorrelation:sameTimeAudit(entries),
    sessionEqualWeightPortfolio:sessionEqualWeightPortfolio(entries,sessions),
    stability:Object.freeze({
      byTimeBucket:groupedPerformance(entries,'timeBucket'),
      byRegime:groupedPerformance(entries,'regime'),
    }),
    methodology:Object.freeze({
      phase57Default:'FIXED_HORIZON_BASELINE',
      entryThresholdRelaxed:false,
      universeSizeSelectedFromOuterOos:false,
      postHocWinnerFiltering:false,
      correlatedSignalsCountedAsIndependentForDiagnostics:false,
      badOosResultsPreserved:true,
    }),
    safety:PHASE57_P25_2_SAFETY,
  });
}

export default {
  summarizeP252TradeFrequencyVariant,
  PHASE57_P25_2_VARIANTS,
  PHASE57_P25_2_POLICY,
  PHASE57_P25_2_SAFETY,
};
