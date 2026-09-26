// Phase57 MSH-Entry LONG v1 pre-implementation feasibility primitives.
// Descriptive only: no fitting, scoring, thresholding, or policy decisions.

const FEATURE_NAMES=Object.freeze([
  'directionalReturnFromOpenPct','directionalVwapDistancePct','directionalMomentum3Pct',
  'directionalMomentumAccelerationPct','directionalPullback6Pct','relativeVolume5',
  'minutesSinceFirstSelection','hybridReciprocalRank','priorSelectionCount','direction',
]);

const finite=value=>typeof value==='number'&&Number.isFinite(value);
const ms=value=>finite(value)?value:Date.parse(String(value??''));
const iso=value=>new Date(value).toISOString();
const jstParts=value=>{
  const text=iso(ms(value)+9*60*60_000);
  return {date:text.slice(0,10),minute:Number(text.slice(11,13))*60+Number(text.slice(14,16))};
};
const startOf=(sessionDate,minute)=>ms(`${sessionDate}T${String(Math.floor(minute/60)).padStart(2,'0')}:${String(minute%60).padStart(2,'0')}:00+09:00`);
const regularMinute=minute=>(minute>=540&&minute<690)||(minute>=750&&minute<930);

function previousRegularStart(value,sessionDate){
  let candidate=ms(value)-5*60_000;
  const parts=jstParts(candidate);
  if(parts.date!==sessionDate)return null;
  if(parts.minute>=690&&parts.minute<750)candidate=startOf(sessionDate,685);
  return regularMinute(jstParts(candidate).minute)?candidate:null;
}

function precedingStarts(decisionTimestamp,sessionDate,count){
  const starts=[];
  let cursor=ms(decisionTimestamp);
  for(let index=0;index<count;index++){
    cursor=previousRegularStart(cursor,sessionDate);
    if(cursor===null)break;
    starts.push(cursor);
  }
  return starts;
}

function normalizeBars(bars,decisionTimestamp,sessionDate){
  const decision=ms(decisionTimestamp),map=new Map();
  for(const row of bars??[]){
    const timestamp=ms(row.timestamp??row.barStartJst),available=ms(row.availableAt??row.availableAtJst);
    if(!Number.isFinite(timestamp)||!Number.isFinite(available)||available>decision||jstParts(timestamp).date!==sessionDate)continue;
    const values={open:Number(row.open),high:Number(row.high),low:Number(row.low),close:Number(row.close),volume:Number(row.volume??0)};
    if(!Object.values(values).every(finite)||Math.min(values.open,values.high,values.low,values.close)<=0||values.volume<0)continue;
    map.set(timestamp,{timestamp,available,...values});
  }
  return map;
}

const available=value=>Object.freeze({status:'AVAILABLE',value});
const missing=(status,reason)=>Object.freeze({status,reason,value:null});

function exactRows(map,starts,historyCount){
  if(starts.length<historyCount)return {rows:null,status:'BLOCKED_BY_HISTORY',reason:'SAME_SESSION_COMPLETED_HISTORY_SHORT'};
  const rows=starts.slice(0,historyCount).map(start=>map.get(start)??null);
  if(rows.some(row=>!row))return {rows:null,status:'BLOCKED_BY_GRID',reason:'REQUIRED_COMPLETED_5M_SLOT_MISSING'};
  return {rows};
}

function featureAudit({bars,decisionTimestamp,sessionDate,rank,firstSelectionTimestamp,priorSelectionCount}){
  const map=normalizeBars(bars,decisionTimestamp,sessionDate),starts=precedingStarts(decisionTimestamp,sessionDate,80);
  const last=starts.length?map.get(starts[0]):null,open=map.get(startOf(sessionDate,540));
  const output={};

  if(!last){
    for(const name of ['directionalMomentum3Pct','directionalMomentumAccelerationPct','directionalPullback6Pct','relativeVolume5'])
      output[name]=missing('BLOCKED_BY_GRID','LATEST_COMPLETED_5M_SLOT_MISSING');
  }else{
    const four=exactRows(map,starts,4);
    output.directionalMomentum3Pct=four.rows
      ?available(100*(four.rows[0].close/four.rows[3].close-1))
      :missing(four.status,four.reason);

    const seven=exactRows(map,starts,7);
    output.directionalMomentumAccelerationPct=seven.rows
      ?available(100*(seven.rows[0].close/seven.rows[3].close-1)-100*(seven.rows[0].close/seven.rows[6].close-1))
      :missing(seven.status,seven.reason);

    const six=exactRows(map,starts,6);
    output.directionalPullback6Pct=six.rows
      ?available(100*(six.rows[0].close/Math.max(...six.rows.map(row=>row.high))-1))
      :missing(six.status,six.reason);
    if(six.rows){
      const denominator=six.rows.slice(1).reduce((sum,row)=>sum+row.volume,0)/5;
      output.relativeVolume5=denominator>0?available(six.rows[0].volume/denominator):missing('NOT_DEFINED','VOLUME_DENOMINATOR_ZERO');
    }else output.relativeVolume5=missing(six.status,six.reason);
  }

  if(!open)output.directionalReturnFromOpenPct=missing('BLOCKED_BY_SESSION_OPEN','EXACT_09_00_BAR_MISSING');
  else if(!last)output.directionalReturnFromOpenPct=missing('BLOCKED_BY_GRID','LATEST_COMPLETED_5M_SLOT_MISSING');
  else output.directionalReturnFromOpenPct=available(100*(last.close/open.open-1));

  if(!open)output.directionalVwapDistancePct=missing('BLOCKED_BY_SESSION_OPEN','EXACT_09_00_BAR_MISSING');
  else if(!last)output.directionalVwapDistancePct=missing('BLOCKED_BY_GRID','LATEST_COMPLETED_5M_SLOT_MISSING');
  else{
    const sessionStarts=[];
    for(let minute=540;minute<jstParts(starts[0]).minute+1;minute+=5){
      if(regularMinute(minute))sessionStarts.push(startOf(sessionDate,minute));
      if(minute===685)minute=745;
    }
    const rows=sessionStarts.map(start=>map.get(start)??null);
    if(rows.some(row=>!row))output.directionalVwapDistancePct=missing('BLOCKED_BY_GRID','SESSION_TO_DATE_5M_SLOT_MISSING');
    else{
      const volume=rows.reduce((sum,row)=>sum+row.volume,0);
      if(!(volume>0))output.directionalVwapDistancePct=missing('NOT_DEFINED','VOLUME_DENOMINATOR_ZERO');
      else{
        const vwap=rows.reduce((sum,row)=>sum+(row.high+row.low+row.close)/3*row.volume,0)/volume;
        output.directionalVwapDistancePct=available(100*(last.close/vwap-1));
      }
    }
  }

  const elapsed=(ms(decisionTimestamp)-ms(firstSelectionTimestamp))/60_000;
  output.minutesSinceFirstSelection=finite(elapsed)&&elapsed>=0?available(elapsed):missing('NOT_DEFINED','INVALID_SELECTION_LINEAGE');
  output.hybridReciprocalRank=Number.isInteger(rank)&&rank>=1&&rank<=5?available(1/rank):missing('NOT_DEFINED','INVALID_RANK');
  output.priorSelectionCount=Number.isInteger(priorSelectionCount)&&priorSelectionCount>=0?available(priorSelectionCount):missing('NOT_DEFINED','INVALID_SELECTION_LINEAGE');
  output.direction=available(1);
  return Object.freeze(output);
}

function futureLabelAudit({bars,minutes=[],auctions=[],decisionTimestamp,sessionDate,decisionPrice}){
  const decision=ms(decisionTimestamp),decisionMinute=jstParts(decision).minute,endpoint=decision+30*60_000;
  const expected=[];
  for(let cursor=decision;cursor<endpoint;cursor+=5*60_000){
    const parts=jstParts(cursor);
    if(parts.date===sessionDate&&regularMinute(parts.minute))expected.push(cursor);
  }
  const closeMinute=Math.max(-Infinity,...(auctions??[]).map(row=>Number(row.minute)).filter(Number.isFinite),
    ...(bars??[]).map(row=>jstParts(row.availableAtJst??row.availableAt).minute).filter(Number.isFinite));
  const allFuture=(bars??[]).filter(row=>{
    const start=ms(row.barStartJst??row.timestamp),availableAt=ms(row.availableAtJst??row.availableAt);
    return start>=decision&&availableAt>decision&&availableAt<=endpoint;
  });
  const byStart=new Map(allFuture.map(row=>[ms(row.barStartJst??row.timestamp),row]));
  let reason=null;
  if(!finite(decisionPrice)||decisionPrice<=0)reason='REFERENCE_PRICE_UNAVAILABLE';
  else if(expected.length===0)reason=decisionMinute>=690&&decisionMinute<750?'LUNCH_BREAK':'INSUFFICIENT_FUTURE';
  else if(closeMinute<=decisionMinute||expected.some(start=>jstParts(start).minute>=closeMinute))reason='SESSION_END';
  else{
    const absent=expected.filter(start=>!byStart.has(start));
    if(absent.length){
      const rawMinutes=(minutes??[]).filter(row=>!row.auction).map(row=>Number(row.minute));
      const partial=absent.some(start=>{
        const minute=jstParts(start).minute;
        return rawMinutes.some(value=>value>=minute&&value<minute+5);
      });
      reason=partial?'MISSING_BAR':'PROVIDER_GAP';
    }
  }
  if(reason)return Object.freeze({labelable:false,reason,expectedBarCount:expected.length,observedBarCount:allFuture.length,
    highAvailable:false,closeAvailable:false,ordinalClass:null,closeOrdinalClass:null});
  const rows=expected.map(start=>byStart.get(start));
  const highReturnPct=100*(Math.max(...rows.map(row=>Number(row.high)))/decisionPrice-1);
  const closeReturnPct=100*(Math.max(...rows.map(row=>Number(row.close)))/decisionPrice-1);
  const ordinal=value=>value>=5?4:value>=3?3:value>=2?2:value>=1?1:0;
  return Object.freeze({labelable:true,reason:null,expectedBarCount:expected.length,observedBarCount:rows.length,
    highAvailable:true,closeAvailable:true,ordinalClass:ordinal(highReturnPct),closeOrdinalClass:ordinal(closeReturnPct),
    highReturnPct,closeReturnPct,windowEndTimestamp:iso(endpoint)});
}

export function auditEntryFeasibilityEvent({event,bars=[],minutes=[],auctions=[],firstSelectionTimestamp,priorSelectionCount,currentAtomicStatus=null,currentAtomicReason=null}={}){
  if(event?.direction&&event.direction!=='LONG')throw new Error('LONG_ONLY_EVENT_REQUIRED');
  const sessionDate=String(event.sessionDate),decisionTimestamp=String(event.decisionTimestamp);
  const features=featureAudit({bars,decisionTimestamp,sessionDate,rank:Number(event.ridgeRank),firstSelectionTimestamp,priorSelectionCount});
  const label=futureLabelAudit({bars,minutes,auctions,decisionTimestamp,sessionDate,decisionPrice:Number(event.decisionPrice)});
  return Object.freeze({
    selectorEventId:event.selectorEventId,sessionDate,symbol:String(event.symbol),decisionTimestamp,
    decisionPrice:Number(event.decisionPrice),ridgeRank:Number(event.ridgeRank),ridgeScore:Number(event.ridgeScore),
    decisionPriceAgeMinutes:Number(event.decisionPriceAgeMinutes),decisionPriceSource:event.decisionPriceSource,
    firstSelectionTimestamp,priorSelectionCount,symbolSessionId:`${sessionDate}|${event.symbol}`,
    currentAtomicStatus,currentAtomicReason,features,label,direction:'LONG',shortScoreEvaluated:false,
  });
}

export {FEATURE_NAMES,featureAudit,futureLabelAudit,precedingStarts};
export default {FEATURE_NAMES,auditEntryFeasibilityEvent,featureAudit,futureLabelAudit,precedingStarts};
