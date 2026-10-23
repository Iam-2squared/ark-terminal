// Evaluator-only NS-MEASUREMENT-1. No training, feature or selector-policy changes.
const codeOf=row=>String(row?.Code??row?.code??row?.symbol??'').trim().toUpperCase();
const dateOf=row=>String(row?.Date??row?.date??row?.sessionDate??'');
const number=(row,...keys)=>{for(const key of keys){const value=Number(row?.[key]);if(Number.isFinite(value))return value;}return NaN;};
const timeOf=value=>{const match=String(value??'').match(/(\d{2}):(\d{2})/);return match?`${match[1]}:${match[2]}`:'';};
const minuteOf=time=>{const [h,m]=String(time).slice(0,5).split(':').map(Number);return h*60+m;};
const isoMinute=iso=>minuteOf(String(iso).slice(11,16));
const finite=value=>typeof value==='number'&&Number.isFinite(value);
const pct=(price,reference)=>finite(price)&&finite(reference)&&reference>0?100*(price/reference-1):null;
const anchorOf=minute=>minute>=540&&minute<690?540:minute>=750&&minute<930?750:null;
const bucketOf=minute=>{const anchor=anchorOf(minute);return anchor===null?null:anchor+5*Math.floor((minute-anchor)/5);};
const round8=value=>Number(Number(value).toFixed(8));

/** Mirror existing Minute acceptance and duplicate-conflict checks exactly. */
export function normalizeMinuteProvenance(rawRows=[]){
  const seen=new Map(),accepted=[];
  for(const row of rawRows){
    const sessionDate=dateOf(row),symbol=codeOf(row),time=timeOf(row?.Time??row?.time),minute=minuteOf(time);
    const open=number(row,'O','Open','open'),high=number(row,'H','High','high'),low=number(row,'L','Low','low'),close=number(row,'C','Close','close');
    const volume=number(row,'Vo','Volume','volume'),turnover=number(row,'Va','Turnover','turnover');
    const key=`${sessionDate}|${symbol}|${time}`;
    if(!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate)||!symbol||!time||![open,high,low,close].every(x=>Number.isFinite(x)&&x>0)||high<Math.max(open,close)||low>Math.min(open,close))continue;
    const canonical={sessionDate,symbol,time,minute,open,high,low,close,volume:Number.isFinite(volume)?volume:0,turnover:Number.isFinite(turnover)?turnover:0};
    if(seen.has(key)){
      if(JSON.stringify(seen.get(key))!==JSON.stringify(canonical))throw new Error(`conflicting duplicate minute row: ${key}`);
      continue;
    }
    seen.set(key,canonical);accepted.push(canonical);
  }
  accepted.sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate)||a.symbol.localeCompare(b.symbol)||a.minute-b.minute);
  const bySymbol=new Map();
  for(const row of accepted){
    const auction=row.minute===690||row.minute===930;
    if(!auction&&anchorOf(row.minute)===null)continue;
    const key=`${row.sessionDate}|${row.symbol}`;
    if(!bySymbol.has(key))bySymbol.set(key,[]);
    bySymbol.get(key).push(Object.freeze({...row,auction,availableMinute:row.minute+(auction?0:1)}));
  }
  return bySymbol;
}

const minuteIndexes=new WeakMap();
function provenanceIndex(minutes){
  let index=minuteIndexes.get(minutes);
  if(index)return index;
  const byBucket=new Map(),sessionDate=minutes[0]?.sessionDate,symbol=minutes[0]?.symbol;
  for(let i=0;i<minutes.length;i++){
    const row=minutes[i];
    if(i&&minutes[i-1].minute>row.minute)throw new Error('Minute provenance is not sorted');
    if(row.sessionDate!==sessionDate||row.symbol!==symbol)throw new Error('cross-session/symbol Minute provenance reached North-Star evaluator');
    if(!row.auction)byBucket.set(bucketOf(row.minute),row);
  }
  index={byBucket,sessionDate,symbol};minuteIndexes.set(minutes,index);return index;
}

function sourceForBar(bar,index,sessionDate,symbol){
  const end=isoMinute(bar.availableAtJst),start=bar.barStartJst?isoMinute(bar.barStartJst):end-5;
  if(bar.sessionDate!==sessionDate||bar.symbol!==symbol||String(bar.availableAtJst).slice(0,10)!==sessionDate)throw new Error('cross-session/symbol bar reached North-Star evaluator');
  const source=index.byBucket.get(start);
  if(!source||source.sessionDate!==sessionDate||source.symbol!==symbol||source.close!==Number(bar.close)||source.availableMinute>end)throw new Error('legacy bar close provenance mismatch');
  return source;
}

function lastAvailable(minutes,decision){
  // Continuous :29 close and :30 auction may share availability :30; auction is later in sorted order.
  let low=0,high=minutes.length;
  while(low<high){const mid=(low+high)>>>1;if(minutes[mid].availableMinute<=decision)low=mid+1;else high=mid;}
  return low?minutes[low-1]:null;
}

/** Flat evaluator fields; unavailable outcomes remain null, never zero/negative labels. */
export function auditRowSemantics({feature,target=null,label=null,bars=[],minutes=[],daily={}}={}){
  if(!feature?.sessionDate||!feature?.symbol||!feature?.decisionAtJst)throw new Error('complete causal feature identity required');
  const {sessionDate,symbol}=feature,decision=isoMinute(feature.decisionAtJst);
  if(!Number.isFinite(decision)||String(feature.decisionAtJst).slice(0,10)!==sessionDate)throw new Error('invalid decision timestamp');
  const index=provenanceIndex(minutes);
  if(minutes.length&&(index.sessionDate!==sessionDate||index.symbol!==symbol))throw new Error('cross-session/symbol Minute provenance reached North-Star evaluator');
  const legacyBar=bars.findLast(row=>isoMinute(row.availableAtJst)<=decision);
  if(!legacyBar)throw new Error('legacy reference bar is missing');
  const legacySource=sourceForBar(legacyBar,index,sessionDate,symbol),legacyReferencePrice=Number(legacyBar.close);
  if(round8(legacyReferencePrice)!==Number(feature.currentPrice))throw new Error('causal feature/reference close provenance mismatch');
  const legacyBucketAgeMin=decision-isoMinute(legacyBar.availableAtJst),legacySourceAgeMin=decision-legacySource.availableMinute;
  const reference=lastAvailable(minutes,decision),referenceAgeMin=reference?decision-reference.availableMinute:null;
  if(legacyBucketAgeMin<0||legacySourceAgeMin<0||(referenceAgeMin!==null&&referenceAgeMin<0))throw new Error('future information reached decision reference');
  const referenceValid=reference!==null&&referenceAgeMin<=5?1:0,referencePrice=referenceValid?reference.close:null;
  const endpointMinute=decision+30,strictBar=bars.findLast(row=>isoMinute(row.availableAtJst)<=endpointMinute&&isoMinute(row.availableAtJst)>decision);
  let strictPrice=null;
  if(strictBar){
    const source=sourceForBar(strictBar,index,sessionDate,symbol),age=endpointMinute-source.availableMinute;
    if(age<0)throw new Error('future information reached strict endpoint');
    if(age<=5)strictPrice=Number(strictBar.close);
  }
  const future=minutes.filter(row=>row.auction?row.minute>decision:row.minute>=decision);
  let futureMfePct=null,trueMaePct=null;
  const thresholds=[1,2,3,5],hits=Object.fromEntries(thresholds.map(level=>[`futureOpportunity${level}`,null])),times=Object.fromEntries(thresholds.map(level=>[`timeTo${level}Min`,null]));
  if(referenceValid&&future.length){
    let maxHigh=-Infinity,minLow=Infinity;
    for(const row of future){maxHigh=Math.max(maxHigh,row.high);minLow=Math.min(minLow,row.low);}
    futureMfePct=pct(maxHigh,referencePrice);trueMaePct=Math.min(0,pct(minLow,referencePrice));
    for(const level of thresholds){
      // Compare ratios at the exact threshold, with no result-dependent/tuned epsilon.
      const hit=future.find(row=>row.high/referencePrice>=1+level/100);
      hits[`futureOpportunity${level}`]=hit?1:0;
      times[`timeTo${level}Min`]=hit?hit.availableMinute-decision:null;
    }
  }
  const scale=Number(daily.adjustmentScale)||1,rawFinal=Number(daily.unadjustedClose)||Number(daily.adjustedClose)/scale,rawPrevious=Number(daily.adjustedPreviousClose)/scale;
  const finalPreviousReturnPct=pct(rawFinal,rawPrevious);
  const rawMae30Pct=finite(target?.futureMae30Pct)?target.futureMae30Pct:null,legacySessionMaePct=finite(label?.futureMaePct)?label.futureMaePct:null;
  const targetTimestamp=target?.target30AvailableAtJst;
  if(targetTimestamp&&String(targetTimestamp).slice(0,10)!==sessionDate)throw new Error('cross-session target reached North-Star evaluator');
  return Object.freeze({
    legacyReferencePrice,legacyBucketAgeMin,legacySourceAgeMin,referenceAgeMin,referenceValid,referencePrice,
    referenceChanged:referenceValid&&referencePrice!==legacyReferencePrice?1:0,
    horizonMinutes:targetTimestamp?isoMinute(targetTimestamp)-decision:null,
    y30Bps:finite(target?.y30Bps)?target.y30Bps:null,
    strict30Bps:strictPrice!==null?10000*(strictPrice/legacyReferencePrice-1):null,
    strict30FreshBps:strictPrice!==null&&referenceValid?10000*(strictPrice/referencePrice-1):null,
    rawMae30Pct,trueMae30Pct:rawMae30Pct===null?null:Math.min(0,rawMae30Pct),
    legacySessionMfePct:finite(label?.futureMfePct)?label.futureMfePct:null,
    legacySessionMaePct,legacyTrueSessionMaePct:legacySessionMaePct===null?null:Math.min(0,legacySessionMaePct),
    futureMfePct,trueMaePct,futureMinuteCount:future.length,...times,...hits,
    finalAdditionalPct:referenceValid?pct(rawFinal,referencePrice):null,finalPreviousReturnPct,
    winner:typeof label?.winner==='boolean'?(label.winner?1:0):(finalPreviousReturnPct!==null&&rawFinal/rawPrevious>=1.05?1:0),
  });
}

export default {normalizeMinuteProvenance,auditRowSemantics};
