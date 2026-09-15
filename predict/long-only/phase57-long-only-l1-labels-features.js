import {createHash} from 'node:crypto';

export const L1_DECISION_TIMES_JST=Object.freeze(['09:30','10:00','10:30','11:00','11:30','13:00','13:30','14:00','14:30','15:00']);
export const L1_LABEL_CONTRACT=Object.freeze({winnerThresholdPct:5,largeWinnerThresholdPct:10,lateDetectionRemainingUpsidePct:1,gapUpThresholdPct:2,targetHorizon:'SAME_SESSION_ONLY',futureBarsRule:'availableAtJst > decisionAtJst'});
const pct=(a,b)=>Number.isFinite(a)&&Number.isFinite(b)&&b>0?100*(a/b-1):null;
const round=x=>Number.isFinite(x)?Number(x.toFixed(8)):x;
const decisionIso=(date,time)=>`${date}T${time}:00+09:00`;
const ordered=bars=>[...bars].sort((a,b)=>a.availableAtJst.localeCompare(b.availableAtJst));
const std=values=>{const xs=values.filter(Number.isFinite);if(!xs.length)return null;const mean=xs.reduce((a,x)=>a+x,0)/xs.length;return Math.sqrt(xs.reduce((a,x)=>a+(x-mean)**2,0)/xs.length);};
const priceLimitWidth=price=>{
  const bands=[[100,30],[200,50],[500,80],[700,100],[1000,150],[1500,300],[2000,400],[3000,500],[5000,700],[7000,1000],[10000,1500],[15000,3000],[20000,4000],[30000,5000],[50000,7000],[70000,10000],[100000,15000],[150000,30000],[200000,40000],[300000,50000],[500000,70000],[700000,100000],[1000000,150000],[1500000,300000],[2000000,400000],[3000000,500000],[5000000,700000],[7000000,1000000],[10000000,1500000],[15000000,3000000],[20000000,4000000],[30000000,5000000],[50000000,7000000]];
  return bands.find(([upper])=>price<upper)?.[1]??10000000;
};

export function buildCausalL1Features({sessionDate,symbol,decisionTimeJst,bars5m,previousAdjustedClose,segment='UNKNOWN',corporateActionFlag=false}={}){
  if(corporateActionFlag)throw new Error('corporate-action intraday adjustment is unresolved; observation is ineligible');
  if(!L1_DECISION_TIMES_JST.includes(decisionTimeJst))throw new Error('decision time is not frozen in the L1 contract');
  const decisionAtJst=decisionIso(sessionDate,decisionTimeJst);
  const bars=ordered((bars5m??[]).filter(x=>x.sessionDate===sessionDate&&x.symbol===symbol&&x.availableAtJst<=decisionAtJst));
  if(!bars.length)return null;
  if(bars.some(x=>x.availableAtJst>decisionAtJst))throw new Error('future bar reached feature builder');
  const last=bars.at(-1),closeN=n=>bars.length>n?bars.at(-1-n).close:bars[0].open;
  const momentum5=pct(last.close,closeN(1)),momentum15=pct(last.close,closeN(3)),momentum30=pct(last.close,closeN(6));
  const totalVolume=bars.reduce((a,x)=>a+(Number(x.volume)||0),0),totalTurnover=bars.reduce((a,x)=>a+(Number(x.turnover)||0),0);
  const vwap=totalVolume>0&&totalTurnover>0?totalTurnover/totalVolume:null;
  const cumulativeVwaps=[];let runningVolume=0,runningTurnover=0;
  for(const bar of bars){runningVolume+=Number(bar.volume)||0;runningTurnover+=Number(bar.turnover)||0;cumulativeVwaps.push(runningVolume>0&&runningTurnover>0?runningTurnover/runningVolume:null);}
  let path=0,directionChanges=0,previousDirection=0;
  for(let i=1;i<bars.length;i++){
    const delta=bars[i].close-bars[i-1].close;path+=Math.abs(delta);
    const direction=Math.sign(delta);if(direction&&previousDirection&&direction!==previousDirection)directionChanges++;if(direction)previousDirection=direction;
  }
  const trueRanges=bars.map((bar,i)=>Math.max(bar.high-bar.low,i?Math.abs(bar.high-bars[i-1].close):0,i?Math.abs(bar.low-bars[i-1].close):0));
  const recentVolume=bars.slice(-3).reduce((a,x)=>a+(Number(x.volume)||0),0)/Math.min(3,bars.length),priorVolume=bars.length>=6?bars.slice(-6,-3).reduce((a,x)=>a+(Number(x.volume)||0),0)/3:null;
  const barReturns=bars.slice(1).map((bar,index)=>pct(bar.close,bars[index].close));
  const priorHigh=bars.length>1?Math.max(...bars.slice(0,-1).map(x=>x.high)):bars[0].open,sessionHigh=Math.max(...bars.map(x=>x.high));
  const gapPct=pct(bars[0].open,previousAdjustedClose),vwapThen=cumulativeVwaps[Math.max(0,cumulativeVwaps.length-4)];
  const feature={sessionDate,symbol,segment,decisionTimeJst,decisionAtJst,currentPrice:last.close,currentReturnPct:pct(last.close,previousAdjustedClose),gapPct,gapBucket:gapPct>=L1_LABEL_CONTRACT.gapUpThresholdPct?'GAP_UP':'NON_GAP',momentum5Pct:momentum5,momentum15Pct:momentum15,momentum30Pct:momentum30,momentumAccelerationPct:momentum5===null||momentum15===null?null:momentum5-momentum15/3,cumulativeVolume:totalVolume,cumulativeTurnover:totalTurnover,volumeAccelerationRatio:priorVolume>0?recentVolume/priorVolume:null,vwap,vwapDistancePct:vwap?pct(last.close,vwap):null,vwapSlope15Pct:vwap&&vwapThen?pct(vwap,vwapThen):null,sessionHighUpdate:last.high>=sessionHigh,highBreakoutPct:pct(last.high,priorHigh),rangeExpansionPct:pct(sessionHigh,Math.min(...bars.map(x=>x.low))),pullbackDepthPct:pct(last.close,sessionHigh),trendEfficiency:path>0?Math.abs(last.close-bars[0].open)/path:0,reversalCount:directionChanges,decisionVolatilityPct:std(barReturns),causalAtr:trueRanges.reduce((a,x)=>a+x,0)/trueRanges.length,observedBars:bars.length,latestAvailableAtJst:last.availableAtJst};
  return Object.freeze(Object.fromEntries(Object.entries(feature).map(([k,v])=>[k,typeof v==='number'?round(v):v])));
}

export function buildEvaluatorOnlyL1Label({sessionDate,symbol,decisionTimeJst,bars5m,terminalAuctions=[],previousAdjustedClose,officialFinalAdjustedClose,decisionTimeAtr,gapPct,contract=L1_LABEL_CONTRACT}={}){
  const decisionAtJst=decisionIso(sessionDate,decisionTimeJst),all=ordered((bars5m??[]).filter(x=>x.sessionDate===sessionDate&&x.symbol===symbol));
  const observed=all.filter(x=>x.availableAtJst<=decisionAtJst),future=[...all.filter(x=>x.availableAtJst>decisionAtJst),...(terminalAuctions??[]).filter(x=>x.sessionDate===sessionDate&&x.symbol===symbol&&x.timestampJst>decisionAtJst).map(x=>({...x,availableAtJst:x.timestampJst}))];
  if(!observed.length||!future.length)return null;
  const current=observed.at(-1).close,finalClose=Number.isFinite(Number(officialFinalAdjustedClose))?Number(officialFinalAdjustedClose):all.at(-1).close,futureHigh=Math.max(...future.map(x=>x.high)),futureLow=Math.min(...future.map(x=>x.low)),sessionHigh=Math.max(...all.map(x=>x.high),...(terminalAuctions??[]).map(x=>Number(x.high)).filter(Number.isFinite));
  const finalReturnPct=pct(finalClose,previousAdjustedClose),remainingUpsidePct=pct(futureHigh,current);
  const futureMaePct=pct(futureLow,current),atrPct=Number.isFinite(Number(decisionTimeAtr))&&current>0?100*Number(decisionTimeAtr)/current:null;
  const winner=finalReturnPct>=contract.winnerThresholdPct,largeWinner=finalReturnPct>=contract.largeWinnerThresholdPct,intradayReached5Pct=pct(sessionHigh,previousAdjustedClose)>=contract.winnerThresholdPct,limitUpPrice=previousAdjustedClose+priceLimitWidth(previousAdjustedClose),limitUpTouched=sessionHigh>=limitUpPrice-1e-8;
  const firstWinnerBar=all.find(x=>pct(x.close,previousAdjustedClose)>=contract.winnerThresholdPct),decisionMinutes=Number(decisionTimeJst.slice(0,2))*60+Number(decisionTimeJst.slice(3,5)),firstWinnerMinutes=firstWinnerBar?new Date(firstWinnerBar.availableAtJst).getTime():null,decisionMillis=new Date(decisionAtJst).getTime();
  const finalClass=largeWinner?'FINAL_GTE10':winner?'FINAL_GTE5':finalReturnPct>=3?'NEAR_3_TO_5':intradayReached5Pct?'INTRADAY_5_THEN_FAIL':'NON_WINNER';
  const label={sessionDate,symbol,decisionTimeJst,evaluatorOnly:true,finalReturnPct,winner,largeWinner,finalClass,remainingUpsidePct,futureMfePct:remainingUpsidePct,futureMaePct,decisionTimeAtrPct:atrPct,futureMfeAtr:atrPct?remainingUpsidePct/atrPct:null,futureMaeAtr:atrPct?futureMaePct/atrPct:null,continuationToClosePct:pct(finalClose,current),lateDetection:winner&&remainingUpsidePct<contract.lateDetectionRemainingUpsidePct,intradayReached5Pct,limitUpTouched,gapUpFailure:Number(gapPct)>=contract.gapUpThresholdPct&&!winner,timeToWinnerMinutes:firstWinnerMinutes===null?null:Math.max(0,(firstWinnerMinutes-decisionMillis)/60000),futureBarCount:future.length};
  return Object.freeze(Object.fromEntries(Object.entries(label).map(([k,v])=>[k,typeof v==='number'?round(v):v])));
}

export function evaluateEarlyWinnerDiscovery({features=[],evaluatorOnlyLabels=[],detectedKeys=[]}={}){
  const detected=new Set(detectedKeys),labels=new Map(evaluatorOnlyLabels.map(x=>[`${x.sessionDate}|${x.symbol}|${x.decisionTimeJst}`,x]));
  const winnerIds=new Set(evaluatorOnlyLabels.filter(x=>x.winner).map(x=>`${x.sessionDate}|${x.symbol}`)),firstDetections=[];
  for(const winnerId of winnerIds){
    const rows=features.filter(x=>`${x.sessionDate}|${x.symbol}`===winnerId&&detected.has(`${x.sessionDate}|${x.symbol}|${x.decisionTimeJst}`)).sort((a,b)=>a.decisionTimeJst.localeCompare(b.decisionTimeJst));
    if(!rows.length)continue;const feature=rows[0],label=labels.get(`${winnerId}|${feature.decisionTimeJst}`);if(label)firstDetections.push({feature,label});
  }
  const summarize=rows=>{
    const mean=key=>{const values=rows.map(x=>Number(x.label[key])).filter(Number.isFinite);return values.length?round(values.reduce((a,x)=>a+x,0)/values.length):null;};
    return Object.freeze({n:rows.length,meanRemainingUpsidePct:mean('remainingUpsidePct'),meanFutureMfePct:mean('futureMfePct'),meanFutureMaePct:mean('futureMaePct'),meanFutureMfeAtr:mean('futureMfeAtr'),meanFutureMaeAtr:mean('futureMaeAtr'),lateDetectionRatePct:rows.length?round(100*rows.filter(x=>x.label.lateDetection).length/rows.length):null});
  };
  const timeMinutes=value=>{const [h,m]=value.split(':').map(Number);return h*60+m-540;};
  const groupBy=key=>Object.freeze(Object.fromEntries([...new Set(firstDetections.map(x=>x.feature[key]??'UNKNOWN'))].sort().map(value=>[value,summarize(firstDetections.filter(x=>(x.feature[key]??'UNKNOWN')===value))])));
  return Object.freeze({winnerCount:winnerIds.size,detectedWinnerCount:firstDetections.length,earlyWinnerRecallPct:winnerIds.size?round(100*firstDetections.length/winnerIds.size):null,...summarize(firstDetections),meanTimeToDetectionMinutes:firstDetections.length?round(firstDetections.reduce((a,x)=>a+timeMinutes(x.label.decisionTimeJst),0)/firstDetections.length):null,byTimeOfDay:groupBy('decisionTimeJst'),byMarket:groupBy('segment'),byLiquidity:groupBy('liquidityBucket'),evaluatorOnly:true});
}

export function buildL1ResearchRows(args={}){
  const features=[],labels=[];
  for(const decisionTimeJst of L1_DECISION_TIMES_JST){
    const feature=buildCausalL1Features({...args,decisionTimeJst});
    if(!feature)continue;
    features.push(feature);
    const label=buildEvaluatorOnlyL1Label({...args,decisionTimeJst,decisionTimeAtr:feature.causalAtr,gapPct:feature.gapPct});if(label)labels.push(label);
  }
  const featureSha256=createHash('sha256').update(JSON.stringify(features)).digest('hex');
  const labelSha256=createHash('sha256').update(JSON.stringify(labels)).digest('hex');
  return Object.freeze({features:Object.freeze(features),evaluatorOnlyLabels:Object.freeze(labels),featureSha256,labelSha256,labelFieldsReachDecisionPipeline:false});
}

export function addCausalBreadthContext(featureRows,{sectorBySymbol={}}={}){
  const groups=new Map();
  for(const row of featureRows??[]){const key=`${row.sessionDate}|${row.decisionTimeJst}`;if(!groups.has(key))groups.set(key,[]);groups.get(key).push(row);}
  return Object.freeze((featureRows??[]).map(row=>{
    const peers=groups.get(`${row.sessionDate}|${row.decisionTimeJst}`),sector=sectorBySymbol[`${row.sessionDate}|${row.symbol}`]??sectorBySymbol[row.symbol]??'UNKNOWN',sectorPeers=peers.filter(x=>(sectorBySymbol[`${x.sessionDate}|${x.symbol}`]??sectorBySymbol[x.symbol]??'UNKNOWN')===sector);
    const positive=list=>list.length?100*list.filter(x=>Number(x.currentReturnPct)>0).length/list.length:null;
    return Object.freeze({...row,marketBreadthPositivePct:round(positive(peers)),sectorBreadthPositivePct:round(positive(sectorPeers)),sector,marketBreadthN:peers.length,sectorBreadthN:sectorPeers.length});
  }));
}

export function assignCausalLiquidityBuckets(featureRows=[]){
  const groups=new Map();
  for(const row of featureRows){const key=`${row.sessionDate}|${row.decisionTimeJst}`;if(!groups.has(key))groups.set(key,[]);groups.get(key).push(row);}
  return Object.freeze(featureRows.map(row=>{
    const peers=[...groups.get(`${row.sessionDate}|${row.decisionTimeJst}`)].sort((a,b)=>a.cumulativeTurnover-b.cumulativeTurnover||a.symbol.localeCompare(b.symbol));
    const rank=peers.findIndex(x=>x.symbol===row.symbol),fraction=(rank+1)/peers.length;
    return Object.freeze({...row,liquidityBucket:fraction<=1/3?'LOW':fraction<=2/3?'MID':'HIGH',liquidityCrossSectionN:peers.length});
  }));
}

export default {buildCausalL1Features,buildEvaluatorOnlyL1Label,buildL1ResearchRows,addCausalBreadthContext,assignCausalLiquidityBuckets,evaluateEarlyWinnerDiscovery};
