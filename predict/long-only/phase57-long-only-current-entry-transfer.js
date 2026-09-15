import {createHash} from 'node:crypto';
import {buildDirectionFeatures,selectionSchedule} from '../../scripts/lib/phase57-minimal-stateful-entry.mjs';

export const CURRENT_ENTRY_TRANSFER_ASSETS=Object.freeze({
  modelSha256:'f05def20081e51dfe7391c7e80e8b8474e5c140c42a47dc29dcd94bca367ab8a',
  featureContractSha256:'cc70b1eb07c0719f72c4a8caa0f165a2812aec4af0b2fdeae42ef3ff400c4115',
  featureImplementationSha256:'7cd4ab03f4de8e0b845fc5f7fb2893d9585feee0989b0f6b085a18a28be73ba0',
  selectorFreezeCommit:'565d74b3dea823581fdb32380113aac5913a248d',
  selectorArtifactSha256:'994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb',
});

export const CURRENT_ENTRY_TRANSFER_SAFETY=Object.freeze({
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,paperTradingAllowed:false,shortAllowed:false,marginAllowed:false,leverageAllowed:false,
});

const finite=value=>typeof value==='number'&&Number.isFinite(value);
const iso=value=>new Date(value).toISOString();
const ms=value=>Date.parse(String(value??''));
const minuteOf=value=>{const date=new Date(ms(value)+9*60*60_000).toISOString();return Number(date.slice(11,13))*60+Number(date.slice(14,16));};
const thresholdKeys=Object.freeze([1,2,3,5]);
const shaBytes=value=>createHash('sha256').update(value).digest('hex');

export function assertCurrentEntryAssets({model,modelBytes,contractBytes,implementationBytes}={}){
  if(shaBytes(modelBytes)!==CURRENT_ENTRY_TRANSFER_ASSETS.modelSha256)throw new Error('CURRENT_ENTRY_MODEL_SHA256_MISMATCH');
  if(shaBytes(contractBytes)!==CURRENT_ENTRY_TRANSFER_ASSETS.featureContractSha256)throw new Error('CURRENT_ENTRY_FEATURE_CONTRACT_SHA256_MISMATCH');
  if(shaBytes(implementationBytes)!==CURRENT_ENTRY_TRANSFER_ASSETS.featureImplementationSha256)throw new Error('CURRENT_ENTRY_FEATURE_IMPLEMENTATION_SHA256_MISMATCH');
  if(model?.artifactClass!=='OFFLINE_DEVELOPMENT_CANDIDATE_NOT_PRODUCTION'||Number(model?.threshold)!==0.6)throw new Error('CURRENT_ENTRY_MODEL_IDENTITY_MISMATCH');
  if(model?.validationOpened!==false||Object.values(model?.safety??{}).some(value=>value!==false))throw new Error('CURRENT_ENTRY_MODEL_SAFETY_MISMATCH');
  if(Object.values(CURRENT_ENTRY_TRANSFER_SAFETY).some(value=>value!==false))throw new Error('LONG_ONLY_TRANSFER_SAFETY_MISMATCH');
  return true;
}

export function normalizeEntrySymbol(symbol){
  const value=String(symbol??'').trim().toUpperCase().replace(/\.T$/,'');
  if(!/^[0-9A-Z]{4}$/.test(value))throw new Error('CURRENT_ENTRY_SYMBOL_ADAPTER_UNAVAILABLE');
  return `${value}.T`;
}

export function normalizeEntryBars(bars=[]){
  return Object.freeze(bars.map(row=>Object.freeze({
    timestamp:String(row.barStartJst??row.timestamp),availableAt:String(row.availableAtJst??row.availableAt),
    open:Number(row.open),high:Number(row.high),low:Number(row.low),close:Number(row.close),volume:Number(row.volume??0),
  })).sort((a,b)=>a.timestamp.localeCompare(b.timestamp)));
}

export function completedPrefix(bars,evaluationTimestamp){
  const at=ms(evaluationTimestamp);
  return Object.freeze((bars??[]).filter(row=>Number.isFinite(ms(row.availableAt))&&ms(row.availableAt)<=at));
}

export function scoreFrozenLongRow(row,model){
  if(!row||Number(row.direction)!==1)throw new Error('LONG_DIRECTION_ROW_REQUIRED');
  if(!Array.isArray(model?.features)||!Array.isArray(model?.weights)||!Array.isArray(model?.means)||!Array.isArray(model?.scales))throw new Error('CURRENT_ENTRY_MODEL_VECTOR_UNAVAILABLE');
  const n=model.features.length;
  if(model.weights.length!==n||model.means.length!==n||model.scales.length!==n||model.scales.some(x=>!(Number(x)>0)))throw new Error('CURRENT_ENTRY_MODEL_VECTOR_MISMATCH');
  const z=Number(model.intercept)+model.features.reduce((sum,name,index)=>sum+Number(model.weights[index])*(Number(row.features?.[name])-Number(model.means[index]))/Number(model.scales[index]),0);
  if(!Number.isFinite(z))throw new Error('CURRENT_ENTRY_NONFINITE_LONG_SCORE');
  return z>=0?1/(1+Math.exp(-z)):Math.exp(z)/(1+Math.exp(z));
}

export function evaluateFrozenCurrentEntryLong({candidate,bars=[],evaluationTimestamp,firstSelectionTimestamp,priorSelectionCount,model}={}){
  const prefix=completedPrefix(bars,evaluationTimestamp),priceReference=prefix.at(-1)?.close;
  if(!prefix.length||!finite(priceReference))return Object.freeze({status:'UNAVAILABLE',reason:'ENTRY_REFERENCE_PRICE_UNAVAILABLE'});
  try{
    const row=buildDirectionFeatures({
      symbol:normalizeEntrySymbol(candidate.symbol),decisionTimestamp:evaluationTimestamp,bars:prefix,
      rank:Number(candidate.ridgeRank),score:Number(candidate.ridgeScore),priceReference,
      firstSelectionTimestamp,priorSelectionCount,direction:1,
    });
    const probability=scoreFrozenLongRow(row,model),pass=probability>Number(model.threshold);
    return Object.freeze({status:pass?'PASS':'WAIT',reason:pass?'LONG_ABOVE_FROZEN_THRESHOLD':'LONG_NOT_ABOVE_FROZEN_THRESHOLD',
      probability,threshold:Number(model.threshold),entryReferencePrice:priceReference,featureTimestamp:row.decisionTimestamp,
      latestFeatureAvailableAt:row.latestAvailableAt,featureSha256:row.featureSha256,prefixSha256:row.prefixSha256});
  }catch(error){
    return Object.freeze({status:'BLOCKED',reason:String(error?.message??error),entryReferencePrice:finite(priceReference)?priceReference:null,
      featureTimestamp:iso(evaluationTimestamp),latestFeatureAvailableAt:prefix.at(-1)?.availableAt??null});
  }
}

export function measureRemainingOpportunity({bars=[],auctions=[],referencePrice,evaluationTimestamp}={}){
  if(!(referencePrice>0)||!Number.isFinite(ms(evaluationTimestamp)))return null;
  const decisionMinute=minuteOf(evaluationTimestamp);
  const futureBars=(bars??[]).filter(row=>minuteOf(row.barStartJst??row.timestamp)>=decisionMinute&&ms(row.availableAtJst??row.availableAt)>ms(evaluationTimestamp));
  const futureAuctions=(auctions??[]).filter(row=>Number(row.minute)>decisionMinute);
  const result={evaluable:futureBars.length>0,futureBarCount:futureBars.length,futureAuctionCount:futureAuctions.length};
  for(const level of thresholdKeys)result[`opportunity${level}`]=futureBars.length?Number(futureBars.some(row=>Number(row.high)/referencePrice>=1+level/100)):null;
  const path=[...futureBars,...futureAuctions].sort((a,b)=>ms(a.availableAtJst??a.timestampJst??a.timestamp)-ms(b.availableAtJst??b.timestampJst??b.timestamp));
  if(path.length){
    result.mfePct=Math.max(0,100*(Math.max(...path.map(row=>Number(row.high)))/referencePrice-1));
    result.maePct=Math.min(0,100*(Math.min(...path.map(row=>Number(row.low)))/referencePrice-1));
  }else{result.mfePct=null;result.maePct=null;}
  return Object.freeze(result);
}

export function latencyBucket(minutes){
  if(!finite(minutes)||minutes<0)return null;
  if(minutes<=5)return '0_TO_5';
  if(minutes<=10)return 'GT5_TO_10';
  if(minutes<=20)return 'GT10_TO_20';
  if(minutes<=30)return 'GT20_TO_30';
  return 'GT30';
}

function stateKey(sessionDate,symbol){return `${sessionDate}|${symbol}`;}
function eventKey(event){return `${event.sessionDate}|${iso(event.decisionTimestamp)}|${event.symbol}`;}
function scheduleBeforeClose(sessionDate){return selectionSchedule(sessionDate).slice(0,-1);}

/**
 * Applies the exact frozen MSH feature formulas, scaler, weights and threshold to LONG only.
 * Frozen Selector membership is never recomputed between its contractual timestamps. The last
 * explicit Top5 is merely the active opportunity set on which the CURRENT Entry state machine
 * receives its native five-minute evaluation clock until the next explicit Selector decision.
 */
export function evaluateLongOnlyTransferSession({sessionDate,selections=[],barsBySymbol=new Map(),auctionsBySymbol=new Map(),model}={}){
  const grouped=new Map();
  for(const raw of selections){
    const event={...raw,decisionTimestamp:iso(raw.decisionTimestamp)};
    if(event.sessionDate!==sessionDate)throw new Error('CROSS_SESSION_SELECTOR_EVENT');
    if(!grouped.has(event.decisionTimestamp))grouped.set(event.decisionTimestamp,[]);
    grouped.get(event.decisionTimestamp).push(event);
  }
  const decisions=[...grouped.keys()].sort();
  if(decisions.some(at=>grouped.get(at).length!==5))throw new Error('FROZEN_SELECTOR_TOP5_CARDINALITY_MISMATCH');
  const states=new Map(),events=[],ticks=[];
  const cadence=scheduleBeforeClose(sessionDate);

  for(let decisionIndex=0;decisionIndex<decisions.length;decisionIndex++){
    const at=decisions[decisionIndex],rows=grouped.get(at).sort((a,b)=>a.ridgeRank-b.ridgeRank||String(a.symbol).localeCompare(String(b.symbol)));
    const present=new Set(rows.map(row=>String(row.symbol)));
    for(const state of states.values())if(state.state==='WATCHING'&&!present.has(state.symbol)){
      state.state='EXPIRED';state.expiredAt=at;state.expiredReason='NOT_SELECTED_ON_NEXT_COMPLETE_FROZEN_SELECTOR_DECISION';
    }
    for(const row of rows){
      const key=stateKey(sessionDate,row.symbol);
      let state=states.get(key);
      if(!state){state={key,sessionDate,symbol:String(row.symbol),state:'WATCHING',firstSelectionTimestamp:at,priorSelectionCount:0,selectionCount:0,
        firstSelectorEventId:eventKey(row),firstDecisionPrice:Number(row.decisionPrice),firstPassTimestamp:null,firstPassPrice:null,expiredAt:null};states.set(key,state);}
      state.selectionCount+=1;state.currentCandidate=row;
      const event={...row,selectorEventId:row.selectorEventId??eventKey(row),decisionTimestamp:at,symbolSessionId:key,selectionIndex:state.selectionCount,
        firstSelectionTimestamp:state.firstSelectionTimestamp,isFirstSelection:state.selectionCount===1,stateBeforeDecision:state.state,
        directStatus:null,directReason:null,longProbability:null,entryFeatureTimestamp:null,entryFeatureAvailableAt:null,entryReferencePriceAtDecision:null};
      if(state.state==='ENTERED'){
        event.directStatus='PASS';event.directReason='ALREADY_ENTERED_NO_REENTRY';
      }else if(state.state==='EXPIRED'){
        event.directStatus='REJECT';event.directReason='TERMINAL_EXPIRED_UNTIL_NEXT_SESSION';
      }
      events.push(event);
    }

    const end=decisionIndex+1<decisions.length?ms(decisions[decisionIndex+1]):Infinity;
    const evaluationTimes=cadence.filter(tick=>ms(tick)>=ms(at)&&ms(tick)<end);
    for(const tick of evaluationTimes){
      for(const row of rows){
        const state=states.get(stateKey(sessionDate,row.symbol));
        if(state.state!=='WATCHING')continue;
        const bars=barsBySymbol.get(String(row.symbol))??[];
        const result=evaluateFrozenCurrentEntryLong({candidate:row,bars,evaluationTimestamp:tick,firstSelectionTimestamp:state.firstSelectionTimestamp,
          priorSelectionCount:state.priorSelectionCount,model});
        state.priorSelectionCount+=1;
        ticks.push({symbolSessionId:state.key,selectorDecisionTimestamp:at,evaluationTimestamp:tick,status:result.status,reason:result.reason,
          probability:result.probability??null,entryReferencePrice:result.entryReferencePrice??null});
        const officialEvent=events.find(event=>event.symbolSessionId===state.key&&event.decisionTimestamp===at);
        if(ms(tick)===ms(at)&&officialEvent&&!officialEvent.directStatus){
          officialEvent.directStatus=result.status;officialEvent.directReason=result.reason;officialEvent.longProbability=result.probability??null;
          officialEvent.entryFeatureTimestamp=result.featureTimestamp??null;officialEvent.entryFeatureAvailableAt=result.latestFeatureAvailableAt??null;
          officialEvent.entryReferencePriceAtDecision=result.entryReferencePrice??null;
        }
        if(result.status==='PASS'){
          state.state='ENTERED';state.firstPassTimestamp=tick;state.firstPassPrice=result.entryReferencePrice;state.firstPassProbability=result.probability;
          state.entryOutcome=measureRemainingOpportunity({bars,auctions:auctionsBySymbol.get(String(row.symbol))??[],referencePrice:state.firstPassPrice,evaluationTimestamp:tick});
        }
      }
    }
    for(const event of events.filter(event=>event.decisionTimestamp===at&&!event.directStatus)){
      event.directStatus='UNAVAILABLE';event.directReason='NO_CURRENT_ENTRY_EVALUATION_TICK';
    }
  }

  const sessionClose=`${sessionDate}T15:30:00+09:00`;
  for(const state of states.values())if(state.state==='WATCHING'){
    state.state='EXPIRED';state.expiredAt=sessionClose;state.expiredReason='SESSION_CLOSE';
  }
  for(const event of events){
    const state=states.get(event.symbolSessionId),passAt=state.firstPassTimestamp;
    const relativePass=passAt&&ms(passAt)>=ms(event.decisionTimestamp);
    const latency=relativePass?(ms(passAt)-ms(event.decisionTimestamp))/60_000:null;
    event.finalOpportunityStatus=state.state==='ENTERED'?'PASS':'REJECT';
    event.firstPassTimestamp=passAt;event.firstPassPrice=state.firstPassPrice;event.firstPassProbability=state.firstPassProbability??null;
    event.entryLatencyMinutes=latency;event.entryLatencyBucket=latencyBucket(latency);
    event.entryAfterThisSelectorEvent=Boolean(relativePass);event.enteredBeforeThisSelectorEvent=Boolean(passAt&&ms(passAt)<ms(event.decisionTimestamp));
    event.consumedReturnBps=relativePass?10_000*(state.firstPassPrice/Number(event.decisionPrice)-1):null;
    for(const level of thresholdKeys)event[`entryOpportunity${level}`]=relativePass?state.entryOutcome?.[`opportunity${level}`]??null:null;
    event.entryMfePct=relativePass?state.entryOutcome?.mfePct??null:null;event.entryMaePct=relativePass?state.entryOutcome?.maePct??null:null;
    event.entryOutcomeEvaluable=relativePass?Boolean(state.entryOutcome?.evaluable):null;
  }
  const opportunities=[...states.values()].map(state=>{
    const first=events.find(event=>event.selectorEventId===state.firstSelectorEventId),latency=state.firstPassTimestamp?(ms(state.firstPassTimestamp)-ms(state.firstSelectionTimestamp))/60_000:null;
    return {symbolSessionId:state.key,sessionDate,stateSymbol:state.symbol,firstSelectorEventId:state.firstSelectorEventId,
      firstSelectionTimestamp:state.firstSelectionTimestamp,firstDecisionPrice:state.firstDecisionPrice,selectionCount:state.selectionCount,
      finalStatus:state.state==='ENTERED'?'PASS':'REJECT',expiredAt:state.expiredAt,expiredReason:state.expiredReason??null,
      firstPassTimestamp:state.firstPassTimestamp,firstPassPrice:state.firstPassPrice,firstPassProbability:state.firstPassProbability??null,
      latencyMinutes:latency,latencyBucket:latencyBucket(latency),consumedReturnBps:state.firstPassTimestamp?10_000*(state.firstPassPrice/state.firstDecisionPrice-1):null,
      entryOutcomeEvaluable:state.firstPassTimestamp?Boolean(state.entryOutcome?.evaluable):null,
      entryOutcome:state.entryOutcome??null,firstSelectorOutcome:first?.selectorOutcome??null};
  });
  return Object.freeze({events:Object.freeze(events),opportunities:Object.freeze(opportunities),ticks:Object.freeze(ticks)});
}

export default {assertCurrentEntryAssets,evaluateFrozenCurrentEntryLong,evaluateLongOnlyTransferSession,measureRemainingOpportunity,latencyBucket};
