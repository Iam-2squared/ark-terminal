// CORRECTED-MEASUREMENT-1. Evaluator only: no fitting or policy changes.
import {normalizeMinuteProvenance} from './phase57-long-only-northstar-semantics.js';

const finite=value=>typeof value==='number'&&Number.isFinite(value);
const number=(row,...keys)=>{for(const key of keys){const value=Number(row?.[key]);if(Number.isFinite(value))return value;}return NaN;};
const minuteOf=value=>{const match=String(value??'').match(/(\d{2}):(\d{2})/);return match?Number(match[1])*60+Number(match[2]):NaN;};
const pct=(price,reference)=>finite(price)&&finite(reference)&&reference>0?100*(price/reference-1):null;
const round8=value=>Number(Number(value).toFixed(8));

function lastAvailable(minutes,decision){
  let answer=null;
  for(const row of minutes){
    if(row.availableMinute>decision)break;
    // Stable source order makes an auction at the same availability later.
    answer=row;
  }
  return answer;
}

function barSource(bar,minutes){
  const start=minuteOf(bar.barStartJst),end=minuteOf(bar.availableAtJst);
  const source=minutes.filter(row=>!row.auction&&row.minute>=start&&row.minute<end).at(-1)??null;
  if(!source||source.close!==Number(bar.close)||source.availableMinute>end)throw new Error('5m close provenance mismatch');
  return source;
}

function excursion(path,reference){
  if(!reference||!path.length)return {mfePct:null,maePct:null};
  const high=Math.max(...path.map(row=>row.high));
  const low=Math.min(...path.map(row=>row.low));
  return {mfePct:Math.max(0,pct(high,reference)),maePct:Math.min(0,pct(low,reference))};
}

function thresholdMetrics({futureBars,auctions,reference,decision}){
  const output={};
  for(const level of [2,3,5]){
    const ratio=1+level/100;
    const high=futureBars.find(row=>row.high/reference>=ratio)??null;
    const closeBar=futureBars.find(row=>row.close/reference>=ratio)??null;
    const auction=auctions.find(row=>row.close/reference>=ratio)??null;
    const closeCandidates=[
      ...(closeBar?[{minute:minuteOf(closeBar.availableAtJst),kind:'CONTINUOUS_5M_CLOSE'}]:[]),
      ...(auction?[{minute:auction.minute,kind:'TERMINAL_AUCTION_CLOSE'}]:[]),
    ].sort((a,b)=>a.minute-b.minute);
    const close=closeCandidates[0]??null;
    output[`highOpportunity${level}`]=high?1:0;
    output[`closeOpportunity${level}`]=close?1:0;
    output[`auctionCloseOpportunity${level}`]=auction?1:0;
    output[`timeToHigh${level}Min`]=high?minuteOf(high.availableAtJst)-decision:null;
    output[`timeToClose${level}Min`]=close?close.minute-decision:null;
    output[`firstCloseHitKind${level}`]=close?.kind??null;
  }
  return output;
}

export {normalizeMinuteProvenance};

export function measureCorrectedRow({feature,target=null,label=null,bars=[],minutes=[],terminalAuctions=[],daily={}}={}){
  if(!feature?.sessionDate||!feature?.symbol||!feature?.decisionAtJst)throw new Error('complete causal feature identity required');
  const {sessionDate,symbol}=feature,decision=minuteOf(feature.decisionAtJst);
  if(!Number.isFinite(decision)||String(feature.decisionAtJst).slice(0,10)!==sessionDate)throw new Error('invalid decision timestamp');
  if(minutes.some(row=>row.sessionDate!==sessionDate||row.symbol!==symbol))throw new Error('cross-session Minute provenance');
  if(bars.some(row=>row.sessionDate!==sessionDate||row.symbol!==symbol))throw new Error('cross-session 5m bars');
  if(terminalAuctions.some(row=>row.sessionDate!==sessionDate||row.symbol!==symbol))throw new Error('cross-session auctions');

  const legacyBar=bars.filter(row=>minuteOf(row.availableAtJst)<=decision).at(-1)??null;
  if(!legacyBar)throw new Error('legacy feature reference bar missing');
  if(round8(Number(legacyBar.close))!==Number(feature.currentPrice))throw new Error('feature/reference close provenance mismatch');

  const reference=lastAvailable(minutes,decision);
  const referenceAgeMin=reference?decision-reference.availableMinute:null;
  if(referenceAgeMin!==null&&referenceAgeMin<0)throw new Error('future decision price');
  const decisionPriceValid=Boolean(reference&&reference.close>0&&referenceAgeMin<=5);
  const decisionPrice=decisionPriceValid?reference.close:null;
  const decisionPriceKind=decisionPriceValid?(reference.auction?'TERMINAL_AUCTION_CLOSE':'LATEST_ACCEPTED_MINUTE_CLOSE'):null;

  const endpointMinute=decision+30;
  const continuousEndpoints=bars.filter(row=>minuteOf(row.availableAtJst)>decision&&minuteOf(row.availableAtJst)<=endpointMinute);
  const lastContinuous=continuousEndpoints.at(-1)??null;
  let endpoint=null;
  if(lastContinuous){
    const source=barSource(lastContinuous,minutes);
    if(endpointMinute-source.availableMinute<=5)endpoint={price:Number(lastContinuous.close),minute:minuteOf(lastContinuous.availableAtJst),kind:'CONTINUOUS_5M_CLOSE'};
  }
  const eligibleAuction=terminalAuctions.filter(row=>row.minute>decision&&row.minute<=endpointMinute).at(-1)??null;
  if(eligibleAuction&&(!endpoint||eligibleAuction.minute>=endpoint.minute))endpoint={price:eligibleAuction.close,minute:eligibleAuction.minute,kind:'TERMINAL_AUCTION_CLOSE'};

  const futureBars=bars.filter(row=>minuteOf(row.barStartJst)>=decision&&minuteOf(row.availableAtJst)>decision);
  const futureAuctions=terminalAuctions.filter(row=>row.minute>decision);
  const futurePath=[...futureBars,...futureAuctions.map(row=>({...row,availableAtJst:row.timestampJst}))]
    .sort((a,b)=>minuteOf(a.availableAtJst)-minuteOf(b.availableAtJst));
  const path30=futurePath.filter(row=>minuteOf(row.availableAtJst)<=endpointMinute);
  const thirty=decisionPriceValid?excursion(path30,decisionPrice):{mfePct:null,maePct:null};
  const session=decisionPriceValid?excursion(futurePath,decisionPrice):{mfePct:null,maePct:null};
  const opportunities=decisionPriceValid&&(futureBars.length||futureAuctions.length)
    ?thresholdMetrics({futureBars,auctions:futureAuctions,reference:decisionPrice,decision})
    :Object.fromEntries([2,3,5].flatMap(level=>[[`highOpportunity${level}`,null],[`closeOpportunity${level}`,null],[`auctionCloseOpportunity${level}`,null],[`timeToHigh${level}Min`,null],[`timeToClose${level}Min`,null],[`firstCloseHitKind${level}`,null]]));

  const scale=Number(daily.adjustmentScale)||1;
  const rawFinal=number(daily,'unadjustedClose')||number(daily,'adjustedClose')/scale;
  const rawPrevious=number(daily,'adjustedPreviousClose')/scale;
  const legacyTimestamp=target?.target30AvailableAtJst;
  if(legacyTimestamp&&String(legacyTimestamp).slice(0,10)!==sessionDate)throw new Error('cross-session legacy target');
  return Object.freeze({
    decisionPrice,decisionPriceValid:decisionPriceValid?1:0,decisionPriceKind,referenceAgeMin,
    legacyReferencePrice:Number(legacyBar.close),legacyReferenceAgeMin:decision-minuteOf(legacyBar.availableAtJst),
    corrected30ReturnBps:decisionPriceValid&&endpoint?10000*(endpoint.price/decisionPrice-1):null,
    corrected30EndpointMinute:endpoint?.minute??null,corrected30EndpointAgeMin:endpoint?endpointMinute-endpoint.minute:null,
    corrected30EndpointKind:endpoint?.kind??null,corrected30Evaluable:decisionPriceValid&&endpoint?1:0,
    mfe30Pct:thirty.mfePct,mae30Pct:thirty.maePct,sessionMfePct:session.mfePct,sessionMaePct:session.maePct,
    futureBarCount:futureBars.length,futureAuctionCount:futureAuctions.length,...opportunities,
    legacySixObservationReturnBps:finite(target?.y30Bps)?target.y30Bps:null,
    legacySixObservationElapsedMin:legacyTimestamp?minuteOf(legacyTimestamp)-decision:null,
    finalAdditionalPct:decisionPriceValid?pct(rawFinal,decisionPrice):null,
    finalPreviousReturnPct:pct(rawFinal,rawPrevious),
    finalPrevious5:typeof label?.winner==='boolean'?(label.winner?1:0):null,
  });
}

export default {normalizeMinuteProvenance,measureCorrectedRow};
