import {createHash} from 'node:crypto';

export const L1_DECISION_TIMES_JST=Object.freeze(['09:30','10:00','10:30','11:00','11:30','13:00','14:00']);
export const L1_LABEL_CONTRACT=Object.freeze({winnerThresholdPct:5,lateDetectionRemainingUpsidePct:1,targetHorizon:'SAME_SESSION_ONLY',futureBarsRule:'availableAtJst > decisionAtJst'});
const pct=(a,b)=>Number.isFinite(a)&&Number.isFinite(b)&&b>0?100*(a/b-1):null;
const round=x=>Number.isFinite(x)?Number(x.toFixed(8)):x;
const decisionIso=(date,time)=>`${date}T${time}:00+09:00`;
const ordered=bars=>[...bars].sort((a,b)=>a.availableAtJst.localeCompare(b.availableAtJst));

export function buildCausalL1Features({sessionDate,symbol,decisionTimeJst,bars5m,previousAdjustedClose}={}){
  if(!L1_DECISION_TIMES_JST.includes(decisionTimeJst))throw new Error('decision time is not frozen in the L1 contract');
  const decisionAtJst=decisionIso(sessionDate,decisionTimeJst);
  const bars=ordered((bars5m??[]).filter(x=>x.sessionDate===sessionDate&&x.symbol===symbol&&x.availableAtJst<=decisionAtJst));
  if(!bars.length)return null;
  if(bars.some(x=>x.availableAtJst>decisionAtJst))throw new Error('future bar reached feature builder');
  const last=bars.at(-1),closeN=n=>bars.length>n?bars.at(-1-n).close:bars[0].open;
  const momentum5=pct(last.close,closeN(1)),momentum15=pct(last.close,closeN(3)),momentum30=pct(last.close,closeN(6));
  const totalVolume=bars.reduce((a,x)=>a+(Number(x.volume)||0),0),totalTurnover=bars.reduce((a,x)=>a+(Number(x.turnover)||0),0);
  const vwap=totalVolume>0&&totalTurnover>0?totalTurnover/totalVolume:null;
  let path=0,directionChanges=0,previousDirection=0;
  for(let i=1;i<bars.length;i++){
    const delta=bars[i].close-bars[i-1].close;path+=Math.abs(delta);
    const direction=Math.sign(delta);if(direction&&previousDirection&&direction!==previousDirection)directionChanges++;if(direction)previousDirection=direction;
  }
  const trueRanges=bars.map((bar,i)=>Math.max(bar.high-bar.low,i?Math.abs(bar.high-bars[i-1].close):0,i?Math.abs(bar.low-bars[i-1].close):0));
  const feature={sessionDate,symbol,decisionTimeJst,decisionAtJst,currentPrice:last.close,currentReturnPct:pct(last.close,previousAdjustedClose),momentum5Pct:momentum5,momentum15Pct:momentum15,momentum30Pct:momentum30,momentumAccelerationPct:momentum5===null||momentum15===null?null:momentum5-momentum15/3,cumulativeVolume:totalVolume,cumulativeTurnover:totalTurnover,vwap,vwapDistancePct:vwap?pct(last.close,vwap):null,sessionHighUpdate:last.high>=Math.max(...bars.map(x=>x.high)),rangeExpansionPct:pct(Math.max(...bars.map(x=>x.high)),Math.min(...bars.map(x=>x.low))),trendEfficiency:path>0?Math.abs(last.close-bars[0].open)/path:0,reversalCount:directionChanges,causalAtr: trueRanges.reduce((a,x)=>a+x,0)/trueRanges.length,observedBars:bars.length,latestAvailableAtJst:last.availableAtJst};
  return Object.freeze(Object.fromEntries(Object.entries(feature).map(([k,v])=>[k,typeof v==='number'?round(v):v])));
}

export function buildEvaluatorOnlyL1Label({sessionDate,symbol,decisionTimeJst,bars5m,terminalAuctions=[],previousAdjustedClose,officialFinalAdjustedClose,contract=L1_LABEL_CONTRACT}={}){
  const decisionAtJst=decisionIso(sessionDate,decisionTimeJst),all=ordered((bars5m??[]).filter(x=>x.sessionDate===sessionDate&&x.symbol===symbol));
  const observed=all.filter(x=>x.availableAtJst<=decisionAtJst),future=[...all.filter(x=>x.availableAtJst>decisionAtJst),...(terminalAuctions??[]).filter(x=>x.sessionDate===sessionDate&&x.symbol===symbol&&x.timestampJst>decisionAtJst).map(x=>({...x,availableAtJst:x.timestampJst}))];
  if(!observed.length||!future.length)return null;
  const current=observed.at(-1).close,finalClose=Number.isFinite(Number(officialFinalAdjustedClose))?Number(officialFinalAdjustedClose):all.at(-1).close,futureHigh=Math.max(...future.map(x=>x.high)),futureLow=Math.min(...future.map(x=>x.low));
  const finalReturnPct=pct(finalClose,previousAdjustedClose),remainingUpsidePct=pct(futureHigh,current);
  const label={sessionDate,symbol,decisionTimeJst,evaluatorOnly:true,finalReturnPct,winner:finalReturnPct>=contract.winnerThresholdPct,remainingUpsidePct,futureMfePct:remainingUpsidePct,futureMaePct:pct(futureLow,current),continuationToClosePct:pct(finalClose,current),lateDetection:finalReturnPct>=contract.winnerThresholdPct&&remainingUpsidePct<contract.lateDetectionRemainingUpsidePct,futureBarCount:future.length};
  return Object.freeze(Object.fromEntries(Object.entries(label).map(([k,v])=>[k,typeof v==='number'?round(v):v])));
}

export function evaluateEarlyWinnerDiscovery({features=[],evaluatorOnlyLabels=[],detectedKeys=[]}={}){
  const detected=new Set(detectedKeys),labels=new Map(evaluatorOnlyLabels.map(x=>[`${x.sessionDate}|${x.symbol}|${x.decisionTimeJst}`,x]));
  const winnerIds=new Set(evaluatorOnlyLabels.filter(x=>x.winner).map(x=>`${x.sessionDate}|${x.symbol}`)),firstDetections=[];
  for(const winnerId of winnerIds){
    const rows=features.filter(x=>`${x.sessionDate}|${x.symbol}`===winnerId&&detected.has(`${x.sessionDate}|${x.symbol}|${x.decisionTimeJst}`)).sort((a,b)=>a.decisionTimeJst.localeCompare(b.decisionTimeJst));
    if(!rows.length)continue;const row=rows[0],label=labels.get(`${winnerId}|${row.decisionTimeJst}`);if(label)firstDetections.push(label);
  }
  const mean=key=>firstDetections.length?round(firstDetections.reduce((a,x)=>a+Number(x[key]),0)/firstDetections.length):null;
  const timeMinutes=value=>{const [h,m]=value.split(':').map(Number);return h*60+m-540;};
  return Object.freeze({winnerCount:winnerIds.size,detectedWinnerCount:firstDetections.length,earlyWinnerRecallPct:winnerIds.size?round(100*firstDetections.length/winnerIds.size):null,meanRemainingUpsidePct:mean('remainingUpsidePct'),meanFutureMfePct:mean('futureMfePct'),meanFutureMaePct:mean('futureMaePct'),meanTimeToDetectionMinutes:firstDetections.length?round(firstDetections.reduce((a,x)=>a+timeMinutes(x.decisionTimeJst),0)/firstDetections.length):null,lateDetectionRatePct:firstDetections.length?round(100*firstDetections.filter(x=>x.lateDetection).length/firstDetections.length):null,evaluatorOnly:true});
}

export function buildL1ResearchRows(args={}){
  const features=[],labels=[];
  for(const decisionTimeJst of L1_DECISION_TIMES_JST){
    const feature=buildCausalL1Features({...args,decisionTimeJst});
    if(!feature)continue;
    features.push(feature);
    const label=buildEvaluatorOnlyL1Label({...args,decisionTimeJst});if(label)labels.push(label);
  }
  const featureSha256=createHash('sha256').update(JSON.stringify(features)).digest('hex');
  const labelSha256=createHash('sha256').update(JSON.stringify(labels)).digest('hex');
  return Object.freeze({features:Object.freeze(features),evaluatorOnlyLabels:Object.freeze(labels),featureSha256,labelSha256,labelFieldsReachDecisionPipeline:false});
}

export function addCausalBreadthContext(featureRows,{sectorBySymbol={}}={}){
  const groups=new Map();
  for(const row of featureRows??[]){const key=`${row.sessionDate}|${row.decisionTimeJst}`;if(!groups.has(key))groups.set(key,[]);groups.get(key).push(row);}
  return Object.freeze((featureRows??[]).map(row=>{
    const peers=groups.get(`${row.sessionDate}|${row.decisionTimeJst}`),sector=sectorBySymbol[row.symbol]??'UNKNOWN',sectorPeers=peers.filter(x=>(sectorBySymbol[x.symbol]??'UNKNOWN')===sector);
    const positive=list=>list.length?100*list.filter(x=>Number(x.currentReturnPct)>0).length/list.length:null;
    return Object.freeze({...row,marketBreadthPositivePct:round(positive(peers)),sectorBreadthPositivePct:round(positive(sectorPeers)),sector,marketBreadthN:peers.length,sectorBreadthN:sectorPeers.length});
  }));
}

export default {buildCausalL1Features,buildEvaluatorOnlyL1Label,buildL1ResearchRows,addCausalBreadthContext,evaluateEarlyWinnerDiscovery};
