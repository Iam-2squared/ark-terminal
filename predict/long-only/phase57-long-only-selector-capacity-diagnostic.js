import {scoreL2Candidate} from './phase57-long-only-l2-selector-v1.js';

export const CAPACITY_TOP_NS=Object.freeze([1,3,5,10,20,30,50]);
export const OPPORTUNITY_THRESHOLDS_BPS=Object.freeze([50,100,150,200]);
export const SELECTOR_CAPACITY_DIAGNOSTIC_CONTRACT=Object.freeze({
  contractId:'PHASE57_LONG_ONLY_SELECTOR_CAPACITY_DIAGNOSTIC_V1',
  evaluationPartition:'DEVELOPMENT_D',
  target:'Y30_BPS',
  modelState:'CANDIDATE_V1_DIAGNOSTIC_FIXED_SCORE',
  fitPartition:'DEVELOPMENT_C',
  topNs:CAPACITY_TOP_NS,
  opportunityThresholdsBps:OPPORTUNITY_THRESHOLDS_BPS,
  retrainingAllowed:false,
  validationAllowed:false,
  oosAllowed:false,
});

const key=row=>`${row.sessionDate}|${row.symbol}|${row.decisionTimeJst}`;
const pointKey=row=>`${row.sessionDate}|${row.decisionTimeJst}`;
const finite=x=>Number.isFinite(Number(x));
const round=x=>Number.isFinite(x)?Number(x.toFixed(8)):x;
const mean=xs=>xs.length?xs.reduce((a,x)=>a+x,0)/xs.length:null;
const quantile=(xs,p)=>{if(!xs.length)return null;const a=[...xs].sort((x,y)=>x-y),i=(a.length-1)*p,lo=Math.floor(i),hi=Math.ceil(i);return a[lo]+(a[hi]-a[lo])*(i-lo);};
const std=xs=>{const m=mean(xs);return xs.length?Math.sqrt(mean(xs.map(x=>(x-m)**2))):null;};
const summarizeNumeric=xs=>({count:xs.length,mean:round(mean(xs)),median:round(quantile(xs,0.5)),p25:round(quantile(xs,0.25)),p75:round(quantile(xs,0.75)),min:round(quantile(xs,0)),max:round(quantile(xs,1))});

export function rankFrozenScore({featureRows=[],targetRows=[],artifact}={}){
  const targets=new Map(targetRows.map(row=>[key(row),row])),groups=new Map();
  for(const feature of featureRows){
    const target=targets.get(key(feature));
    if(!target||!finite(target.y30Bps))continue;
    const k=pointKey(feature);if(!groups.has(k))groups.set(k,[]);
    groups.get(k).push({feature,target,score:scoreL2Candidate(feature,artifact)});
  }
  const ranked=[];
  for(const rows of groups.values()){
    rows.sort((a,b)=>b.score-a.score||a.feature.symbol.localeCompare(b.feature.symbol));
    const n=rows.length;
    rows.forEach((row,index)=>ranked.push(Object.freeze({...row,rank:index+1,groupSize:n,scorePercentile:100*(n-index)/n})));
  }
  return Object.freeze(ranked);
}

function coreSummary(rows,allRows){
  const y=rows.map(x=>Number(x.target.y30Bps)),mfe=rows.map(x=>Number(x.target.futureMfe30Pct)).filter(finite),mae=rows.map(x=>Number(x.target.futureMae30Pct)).filter(finite);
  const sessions=[...new Set(rows.map(x=>x.feature.sessionDate))],sessionMeans=sessions.map(date=>mean(rows.filter(x=>x.feature.sessionDate===date).map(x=>Number(x.target.y30Bps))));
  const winners=rows.filter(x=>x.target.winner).length,totalWinners=allRows.filter(x=>x.target.winner).length;
  const opportunities=Object.fromEntries(OPPORTUNITY_THRESHOLDS_BPS.map(threshold=>{
    const total=allRows.filter(x=>Number(x.target.y30Bps)>=threshold).length,selected=rows.filter(x=>Number(x.target.y30Bps)>=threshold).length;
    return [`GE_${threshold}_BPS`,{total,selected,recallPct:round(total?100*selected/total:0),precisionPct:round(rows.length?100*selected/rows.length:0)}];
  }));
  const meanMfe=mean(mfe),meanMae=mean(mae);
  return Object.freeze({
    candidateCount:rows.length,decisionCount:new Set(rows.map(x=>pointKey(x.feature))).size,
    meanReturnBps:round(mean(y)),medianReturnBps:round(quantile(y,0.5)),positiveRatePct:round(rows.length?100*y.filter(v=>v>0).length/rows.length:0),
    meanFutureMfePct:round(meanMfe),meanFutureMaePct:round(meanMae),mfeToAbsMae:round(meanMae?meanMfe/Math.abs(meanMae):null),
    positiveSessions:sessions.filter((_,i)=>sessionMeans[i]>0).length,sessionCount:sessions.length,positiveSessionRatePct:round(sessions.length?100*sessionMeans.filter(v=>v>0).length/sessions.length:0),
    final5WinnerPrecisionPct:round(rows.length?100*winners/rows.length:0),final5WinnerRecallPct:round(totalWinners?100*winners/totalWinners:0),opportunities,
  });
}

export function buildCapacityCurve(ranked=[]){
  return Object.freeze(Object.fromEntries(CAPACITY_TOP_NS.map(n=>[`TOP_${n}`,coreSummary(ranked.filter(x=>x.rank<=n),ranked)])));
}

function groupedSummary(rows,allRows,field,values){return Object.fromEntries(values.map(value=>[value,coreSummary(rows.filter(x=>(x.feature[field]??'UNKNOWN')===value),allRows.filter(x=>(x.feature[field]??'UNKNOWN')===value))]));}

export function buildCapacityStability(ranked=[]){
  return Object.freeze(Object.fromEntries(CAPACITY_TOP_NS.map(n=>{
    const rows=ranked.filter(x=>x.rank<=n);
    const morning=rows.filter(x=>String(x.feature.decisionTimeJst)<'12:00'),afternoon=rows.filter(x=>String(x.feature.decisionTimeJst)>='12:00');
    const allMorning=ranked.filter(x=>String(x.feature.decisionTimeJst)<'12:00'),allAfternoon=ranked.filter(x=>String(x.feature.decisionTimeJst)>='12:00');
    return [`TOP_${n}`,{
      market:groupedSummary(rows,ranked,'segment',['PRIME','STANDARD','GROWTH']),
      liquidity:groupedSummary(rows,ranked,'liquidityBucket',['LOW','MID','HIGH']),
      gap:groupedSummary(rows,ranked,'gapBucket',['NON_GAP','GAP_UP']),
      time:{MORNING:coreSummary(morning,allMorning),AFTERNOON:coreSummary(afternoon,allAfternoon)},
    }];
  })));
}

function pearson(a,b){if(a.length<2||a.length!==b.length)return null;const ma=mean(a),mb=mean(b),num=a.reduce((s,x,i)=>s+(x-ma)*(b[i]-mb),0),da=Math.sqrt(a.reduce((s,x)=>s+(x-ma)**2,0)),db=Math.sqrt(b.reduce((s,x)=>s+(x-mb)**2,0));return da&&db?num/(da*db):null;}
function ranks(values){const indexed=values.map((v,i)=>({v,i})).sort((a,b)=>a.v-b.v),out=Array(values.length);for(let i=0;i<indexed.length;){let j=i+1;while(j<indexed.length&&indexed[j].v===indexed[i].v)j++;const r=(i+j+1)/2;for(let k=i;k<j;k++)out[indexed[k].i]=r;i=j;}return out;}
export function buildScoreCalibration(ranked=[]){
  const cumulative={};for(const pct of [1,2,5,10,20])cumulative[`TOP_${pct}_PCT`]=coreSummary(ranked.filter(x=>x.scorePercentile>=100-pct),ranked);
  const bands={TOP_1_PCT:ranked.filter(x=>x.scorePercentile>=99),P98_TO_99:ranked.filter(x=>x.scorePercentile>=98&&x.scorePercentile<99),P95_TO_98:ranked.filter(x=>x.scorePercentile>=95&&x.scorePercentile<98),P90_TO_95:ranked.filter(x=>x.scorePercentile>=90&&x.scorePercentile<95),P80_TO_90:ranked.filter(x=>x.scorePercentile>=80&&x.scorePercentile<90),MIDDLE_20_TO_80:ranked.filter(x=>x.scorePercentile>20&&x.scorePercentile<80),BOTTOM_20:ranked.filter(x=>x.scorePercentile<=20)};
  const perDecision=[];for(const k of new Set(ranked.map(x=>pointKey(x.feature)))){const rows=ranked.filter(x=>pointKey(x.feature)===k);perDecision.push(pearson(ranks(rows.map(x=>x.score)),ranks(rows.map(x=>Number(x.target.y30Bps)))));}
  return Object.freeze({cumulative,exclusiveBands:Object.fromEntries(Object.entries(bands).map(([k,v])=>[k,coreSummary(v,ranked)])),spearman:{global:round(pearson(ranks(ranked.map(x=>x.score)),ranks(ranked.map(x=>Number(x.target.y30Bps))))),meanPerDecision:round(mean(perDecision.filter(finite))),decisionCount:perDecision.filter(finite).length}});
}

export function buildReturnDistribution(ranked=[]){
  const rows=ranked.filter(x=>x.rank<=5),y=rows.map(x=>Number(x.target.y30Bps)),m=mean(y),s=std(y),sorted=[...y].sort((a,b)=>b-a),sum=y.reduce((a,x)=>a+x,0);
  const upperCount=p=>Math.max(1,Math.ceil(y.length*p)),trimUpper=p=>mean([...y].sort((a,b)=>a-b).slice(0,-upperCount(p)));
  const moments=n=>s?mean(y.map(x=>((x-m)/s)**n)):null;
  return Object.freeze({count:y.length,percentiles:Object.fromEntries([1,5,10,25,50,75,90,95,99].map(p=>[`P${p}`,round(quantile(y,p/100))])),min:round(quantile(y,0)),max:round(quantile(y,1)),mean:round(m),median:round(quantile(y,0.5)),skewness:round(moments(3)),kurtosis:round(moments(4)),excessKurtosis:round(moments(4)-3),positiveMeanBps:round(mean(y.filter(x=>x>0))),negativeMeanBps:round(mean(y.filter(x=>x<0))),top1PctContributionPct:round(sum?100*sorted.slice(0,upperCount(0.01)).reduce((a,x)=>a+x,0)/sum:null),top5PctContributionPct:round(sum?100*sorted.slice(0,upperCount(0.05)).reduce((a,x)=>a+x,0)/sum:null),upper1PctRemovedMeanBps:round(trimUpper(0.01)),upper5PctRemovedMeanBps:round(trimUpper(0.05))});
}

const bandOfRank=rank=>rank<=10?'RANK_6_TO_10':rank<=20?'RANK_11_TO_20':rank<=50?'RANK_21_TO_50':rank<=100?'RANK_51_TO_100':'RANK_101_PLUS';
function categorical(rows,field){const counts={};for(const row of rows){const value=String(row.feature[field]??'UNKNOWN');counts[value]=(counts[value]??0)+1;}return Object.fromEntries(Object.entries(counts).sort((a,b)=>b[1]-a[1]).map(([k,v])=>[k,{count:v,pct:round(100*v/rows.length)}]));}
export function buildMissedOpportunity(ranked=[]){
  return Object.freeze(Object.fromEntries(OPPORTUNITY_THRESHOLDS_BPS.map(threshold=>{
    const all=ranked.filter(x=>Number(x.target.y30Bps)>=threshold),rows=all.filter(x=>x.rank>5),bands={};for(const row of rows){const b=bandOfRank(row.rank);bands[b]=(bands[b]??0)+1;}
    const numeric=field=>summarizeNumeric(rows.map(x=>Number(x.feature[field])).filter(finite));
    return [`GE_${threshold}_BPS`,{opportunityCount:all.length,missedByTop5:rows.length,missRatePct:round(all.length?100*rows.length/all.length:0),rank:summarizeNumeric(rows.map(x=>x.rank)),rankPercentile:summarizeNumeric(rows.map(x=>x.scorePercentile)),score:summarizeNumeric(rows.map(x=>x.score)),rankBands:Object.fromEntries(Object.entries(bands).map(([k,v])=>[k,{count:v,pct:round(100*v/rows.length)}])),features:{currentReturnPct:numeric('currentReturnPct'),momentum30Pct:numeric('momentum30Pct'),vwapSlope15Pct:numeric('vwapSlope15Pct'),vwapDistancePct:numeric('vwapDistancePct'),cumulativeTurnover:numeric('cumulativeTurnover'),volumeAccelerationRatio:numeric('volumeAccelerationRatio'),futureMfe30Pct:summarizeNumeric(rows.map(x=>Number(x.target.futureMfe30Pct)).filter(finite)),futureMae30Pct:summarizeNumeric(rows.map(x=>Number(x.target.futureMae30Pct)).filter(finite))},market:categorical(rows,'segment'),liquidity:categorical(rows,'liquidityBucket'),gap:categorical(rows,'gapBucket'),timeOfDay:categorical(rows,'decisionTimeJst')}];
  })));
}

export function buildBreadthVsQuality(capacityCurve={}){
  const base=capacityCurve.TOP_5;
  return Object.freeze(Object.fromEntries([10,20,30,50].map(n=>{const row=capacityCurve[`TOP_${n}`];return [`TOP_5_TO_${n}`,{meanReturnChangeBps:round(row.meanReturnBps-base.meanReturnBps),meanReturnRetentionPct:round(base.meanReturnBps?100*row.meanReturnBps/base.meanReturnBps:null),positiveRateChangePctPoints:round(row.positiveRatePct-base.positiveRatePct),maeChangePctPoints:round(row.meanFutureMaePct-base.meanFutureMaePct),opportunityRecallChangePctPoints:Object.fromEntries(OPPORTUNITY_THRESHOLDS_BPS.map(t=>[`GE_${t}_BPS`,round(row.opportunities[`GE_${t}_BPS`].recallPct-base.opportunities[`GE_${t}_BPS`].recallPct)]))}];})));
}

export function diagnoseCapacity(ranked=[]){
  const capacityCurve=buildCapacityCurve(ranked);
  return Object.freeze({contract:SELECTOR_CAPACITY_DIAGNOSTIC_CONTRACT,capacityCurve,opportunityRecall:Object.fromEntries(Object.entries(capacityCurve).map(([k,v])=>[k,v.opportunities])),scoreCalibration:buildScoreCalibration(ranked),missedOpportunity:buildMissedOpportunity(ranked),distributionTop5:buildReturnDistribution(ranked),breadthVsQuality:buildBreadthVsQuality(capacityCurve),stability:buildCapacityStability(ranked)});
}

export default {rankFrozenScore,diagnoseCapacity,buildCapacityCurve,buildScoreCalibration,buildMissedOpportunity,buildReturnDistribution,buildBreadthVsQuality,buildCapacityStability};
