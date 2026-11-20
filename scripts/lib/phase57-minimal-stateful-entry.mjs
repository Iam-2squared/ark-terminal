import fs from 'node:fs';
import { createHash } from 'node:crypto';

const contractBytes = fs.readFileSync(new URL('../../predict/research/phase57-minimal-stateful-entry-contract.json', import.meta.url));
const deepFreeze = value => { if(value && typeof value==='object'){Object.values(value).forEach(deepFreeze);Object.freeze(value);}return value; };
export const CONTRACT = deepFreeze(JSON.parse(contractBytes));
export const CONTRACT_SHA256 = createHash('sha256').update(contractBytes).digest('hex');
export const FEATURES = Object.freeze([...CONTRACT.features]);
export const SAFETY = Object.freeze({...CONTRACT.safety});
export const sha256 = value => createHash('sha256').update(typeof value === 'string' ? value : JSON.stringify(value)).digest('hex');
const ms = v => {
  if (typeof v !== 'string' || !/(Z|[+-]\d{2}:\d{2})$/.test(v) || !Number.isFinite(Date.parse(v))) throw Error('EXPLICIT_TIMESTAMP_REQUIRED');
  return Date.parse(v);
};
const finite = x => typeof x === 'number' && Number.isFinite(x);
const iso = t => new Date(t).toISOString();
export const sessionDate = t => iso(ms(t) + 32400000).slice(0, 10);
const minute = t => {const j=iso(ms(t)+32400000);return Number(j.slice(11,13))*60+Number(j.slice(14,16));};
const mean = xs => xs.reduce((s,x)=>s+x,0)/xs.length;
const pct = (a,b) => (a/b-1)*100;

export function selectionSchedule(date) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) throw Error('SESSION_DATE_REQUIRED');
  return [...Array.from({length:30},(_,i)=>545+i*5),...Array.from({length:36},(_,i)=>755+i*5)]
    .map(m=>iso(ms(`${date}T${String(Math.floor(m/60)).padStart(2,'0')}:${String(m%60).padStart(2,'0')}:00+09:00`)));
}
function rejectOutcomeFields(value) {
  if (!value || typeof value !== 'object') return;
  for (const [key,child] of Object.entries(value)) {
    if (/^(labels?|targets?|outcomes?|outcomeAt|future.*|actualReturn.*|netReturn.*|mfe.*|mae.*)$/i.test(key)) throw Error('OUTCOME_IN_FEATURE_INPUT');
    rejectOutcomeFields(child);
  }
}
function canonicalPrefix(bars,t,date) {
  rejectOutcomeFields(bars);
  if (!Array.isArray(bars) || bars.length<7) throw Error('INSUFFICIENT_PREFIX');
  let prior=-Infinity;
  const out=bars.map(b=>{
    const start=ms(b.timestamp),available=ms(b.availableAt),m=minute(b.timestamp);
    if (sessionDate(b.timestamp)!==date || start%300000 || start<=prior || !((m>=540&&m<690)||(m>=750&&m<930))) throw Error('INVALID_PREFIX_GRID');
    if (start+300000>ms(t) || available<start+300000 || available>ms(t)) throw Error('NON_PIT_PREFIX');
    if (!['open','high','low','close','volume'].every(k=>finite(b[k])) || Math.min(b.open,b.low,b.close)<=0 || b.volume<0 || b.high<Math.max(b.open,b.close,b.low) || b.low>Math.min(b.open,b.close)) throw Error('INVALID_OHLCV');
    prior=start;return {timestamp:iso(start),availableAt:iso(available),open:b.open,high:b.high,low:b.low,close:b.close,volume:b.volume};
  });
  if (minute(out[0].timestamp)!==540) throw Error('SESSION_OPEN_MISSING');
  let expected=ms(t)-300000;
  for(let i=out.length-1;i>=out.length-7;i--){
    // Scheduled lunch is not a missing bar.
    const m=minute(iso(expected));if(m>=690&&m<750)expected=ms(`${date}T11:25:00+09:00`);
    if(ms(out[i].timestamp)!==expected)throw Error('RECENT_GRID_GAP_OR_STALE');
    expected-=300000;
  }
  return out;
}

export function buildDirectionFeatures({symbol,decisionTimestamp,bars,rank,score,priceReference,firstSelectionTimestamp,priorSelectionCount,direction}) {
  if (!/^[0-9A-Z]{4}\.T$/.test(symbol) || ![1,-1].includes(direction)) throw Error('INVALID_SYMBOL_OR_DIRECTION');
  const date=sessionDate(decisionTimestamp);
  if (!selectionSchedule(date).includes(iso(ms(decisionTimestamp)))) throw Error('INVALID_SELECTION_TIME');
  if (!Number.isInteger(rank)||rank<1||!finite(score)||!Number.isInteger(priorSelectionCount)||priorSelectionCount<0) throw Error('INVALID_LINEAGE');
  if (sessionDate(firstSelectionTimestamp)!==date||ms(firstSelectionTimestamp)>ms(decisionTimestamp)) throw Error('FUTURE_SELECTION_STATE');
  const prefix=canonicalPrefix(bars,decisionTimestamp,date),last=prefix.at(-1);
  if(priceReference!==last.close)throw Error('PRICE_REFERENCE_MISMATCH');
  const volume=prefix.reduce((s,b)=>s+b.volume,0),priorVolume=mean(prefix.slice(-6,-1).map(b=>b.volume));
  if(!(volume>0&&priorVolume>0))throw Error('VOLUME_DENOMINATOR_MISSING');
  const vwap=prefix.reduce((s,b)=>s+(b.high+b.low+b.close)/3*b.volume,0)/volume;
  const momentum3=pct(last.close,prefix.at(-4).close),momentum6=pct(last.close,prefix.at(-7).close);
  const high=Math.max(...prefix.slice(-6).map(b=>b.high)),low=Math.min(...prefix.slice(-6).map(b=>b.low));
  const values=[direction*pct(last.close,prefix[0].open),direction*pct(last.close,vwap),direction*momentum3,direction*(momentum3-momentum6),direction===1?pct(last.close,high):pct(low,last.close),last.volume/priorVolume,(ms(decisionTimestamp)-ms(firstSelectionTimestamp))/60000,1/rank,priorSelectionCount,direction];
  if(!values.every(finite))throw Error('NONFINITE_FEATURE');
  const record={contractSha256:CONTRACT_SHA256,symbol,sessionDate:date,decisionTimestamp:iso(ms(decisionTimestamp)),direction,features:Object.fromEntries(FEATURES.map((k,i)=>[k,values[i]])),prefixSha256:sha256(prefix),latestAvailableAt:prefix.at(-1).availableAt,selectorModelDigest:CONTRACT.selectorModelDigest,selectorFreezeSHA:CONTRACT.selectorFreezeSHA};
  return Object.freeze({...record,featureSha256:sha256(record)});
}

// Inference math only. There is intentionally no fit, threshold search or data-loader API.
export function scoreLogistic(row,artifact,{syntheticContractTest=false}={}) {
  if(!artifact)return {available:false,reason:'MODEL_UNAVAILABLE'};
  if(!syntheticContractTest||artifact.artifactClass!=='SYNTHETIC_CONTRACT_TEST')throw Error('REAL_MODEL_BLOCKED_NO_AUTHORIZED_TRAINING_DATASET');
  const {featureSha256,...core}=row;
  if(sha256(core)!==featureSha256||row.contractSha256!==CONTRACT_SHA256)throw Error('FEATURE_FREEZE_MISMATCH');
  if(artifact.contractSha256!==CONTRACT_SHA256||JSON.stringify(artifact.features)!==JSON.stringify(FEATURES))throw Error('MODEL_FEATURE_CONTRACT_MISMATCH');
  for(const k of ['weights','means','scales'])if(!Array.isArray(artifact[k])||artifact[k].length!==FEATURES.length||!artifact[k].every(finite))throw Error('INVALID_MODEL_VECTOR');
  if(!finite(artifact.intercept)||artifact.scales.some(s=>s<=0)||!finite(artifact.threshold)||artifact.threshold<0||artifact.threshold>1)throw Error('INVALID_MODEL_PARAMETERS');
  const z=artifact.intercept+FEATURES.reduce((s,k,i)=>s+artifact.weights[i]*(row.features[k]-artifact.means[i])/artifact.scales[i],0);
  if(!finite(z))throw Error('NONFINITE_SCORE');
  const probability=z>=0?1/(1+Math.exp(-z)):Math.exp(z)/(1+Math.exp(z));
  return {available:true,probability,threshold:artifact.threshold};
}
export function decideNow(pair,artifact,options={}) {
  if(pair.length!==2||pair[0].direction!==1||pair[1].direction!==-1)throw Error('PAIRED_DIRECTIONS_REQUIRED');
  if(pair[0].symbol!==pair[1].symbol||pair[0].decisionTimestamp!==pair[1].decisionTimestamp)throw Error('CROSS_EVENT_DIRECTION_PAIR');
  const long=scoreLogistic(pair[0],artifact,options),short=scoreLogistic(pair[1],artifact,options);
  if(!long.available||!short.available)return {action:'WATCH',direction:null,reason:'MODEL_UNAVAILABLE'};
  if(long.probability===short.probability)return {action:'WATCH',direction:null,reason:'DIRECTION_TIE'};
  const direction=long.probability>short.probability?1:-1,best=direction===1?long:short;
  return {action:best.probability>best.threshold?'ENTER':'WATCH',direction:best.probability>best.threshold?direction:null,probability:best.probability,longProbability:long.probability,shortProbability:short.probability,reason:best.probability>best.threshold?'ABOVE_SINGLE_THRESHOLD':'NOT_ABOVE_SINGLE_THRESHOLD'};
}

// Each complete snapshot includes ALL Hybrid selected symbols, not only P21 ENTERs.
export class MinimalStatefulEntry {
  constructor(date,{model=null,syntheticContractTest=false}={}){if(model&&(!syntheticContractTest||model.artifactClass!=='SYNTHETIC_CONTRACT_TEST'))throw Error('REAL_MODEL_BLOCKED_NO_AUTHORIZED_TRAINING_DATASET');this.date=date;this.schedule=selectionSchedule(date);this.model=model?deepFreeze(structuredClone(model)):null;this.syntheticContractTest=syntheticContractTest;this.states=new Map();this.seenPoints=new Set();this.lastIndex=-1;this.closed=false;}
  step(snapshot,prefixes={}) {
    if(this.closed)throw Error('SESSION_CLOSED');
    rejectOutcomeFields(snapshot);
    if(snapshot.selectorModelDigest!==CONTRACT.selectorModelDigest||snapshot.selectorFreezeSHA!==CONTRACT.selectorFreezeSHA)throw Error('SELECTOR_FREEZE_MISMATCH');
    const t=iso(ms(snapshot.decisionTimestamp)),index=this.schedule.indexOf(t);
    if(index<0||sessionDate(t)!==this.date||index<=this.lastIndex||this.seenPoints.has(t))throw Error('DUPLICATE_OR_NONMONOTONIC_SNAPSHOT');
    if(typeof snapshot.complete!=='boolean')throw Error('SNAPSHOT_COMPLETENESS_REQUIRED');
    const candidates=snapshot.selected??[];
    if(!Array.isArray(candidates)||new Set(candidates.map(c=>c.symbol)).size!==candidates.length)throw Error('DUPLICATE_SELECTION_EVENT');
    for(const c of candidates)if(!/^[0-9A-Z]{4}\.T$/.test(c.symbol)||!Number.isInteger(c.rank)||c.rank<1||!finite(c.score)||!finite(c.priceReference)||c.priceReference<=0)throw Error('INVALID_CANDIDATE');
    if(!snapshot.complete&&candidates.length)throw Error('INCOMPLETE_SNAPSHOT_CANNOT_DECLARE_MEMBERSHIP');
    const gap=this.lastIndex>=0&&index>this.lastIndex+1;
    this.lastIndex=index;this.seenPoints.add(t);
    if(!snapshot.complete)return {events:[],transitions:[],status:'BLOCKED_SNAPSHOT_NO_ABSENCE_INFERENCE',gap,safety:SAFETY};
    const present=new Set(candidates.map(c=>c.symbol)),transitions=[],events=[];
    for(const [symbol,state] of this.states)if(state.state==='WATCHING'&&!present.has(symbol)){state.state='EXPIRED';state.expiredAt=t;transitions.push({symbol,at:t,to:'EXPIRED',reason:'NOT_SELECTED_ON_COMPLETE_SNAPSHOT'});}
    for(const c of candidates){
      const state=this.states.get(c.symbol)??{state:'UNSEEN',firstSelectionTimestamp:t,priorSelectionCount:0,firstEnterTimestamp:null,entryCount:0};
      const before=state.state;
      if(state.state==='UNSEEN')state.state='WATCHING';
      const core={eventId:`${this.date}|${t}|${c.symbol}`,symbolSessionId:`${this.date}|${c.symbol}`,sessionDate:this.date,symbol:c.symbol,decisionTimestamp:t,hybridRank:c.rank,hybridScore:c.score,selectionIndex:state.priorSelectionCount+1,priorSelectionCount:state.priorSelectionCount,firstSelectionTimestamp:state.firstSelectionTimestamp,minutesSinceFirstSelection:(ms(t)-ms(state.firstSelectionTimestamp))/60000,previousSelectionTimestamp:state.previousSelectionTimestamp??null,selectionLineage:snapshot.selectionLineage??null,sourceClass:snapshot.sourceClass??'UNKNOWN'};
      let pair=null,featureStatus='READY',decision={action:'WATCH',direction:null,reason:'MODEL_UNAVAILABLE'};
      try{pair=[1,-1].map(direction=>buildDirectionFeatures({symbol:c.symbol,decisionTimestamp:t,bars:prefixes[c.symbol]??[],rank:c.rank,score:c.score,priceReference:c.priceReference,firstSelectionTimestamp:state.firstSelectionTimestamp,priorSelectionCount:state.priorSelectionCount,direction}));}
      catch(error){featureStatus=String(error.message);}
      if(['ENTERED','EXPIRED'].includes(state.state))decision={action:'NO_ACTION',direction:null,reason:state.state};
      else if(!pair)decision={action:'WATCH',direction:null,reason:'BLOCKED_FEATURES'};
      else decision=decideNow(pair,this.model,{syntheticContractTest:this.syntheticContractTest});
      if(decision.action==='ENTER'){state.state='ENTERED';state.entryCount++;state.firstEnterTimestamp=t;state.enterDirection=decision.direction;}
      if(state.entryCount>1)throw Error('REENTRY_VIOLATION');
      state.priorSelectionCount++;state.previousSelectionTimestamp=t;this.states.set(c.symbol,state);
      if(before!==state.state)transitions.push({symbol:c.symbol,at:t,from:before,to:state.state,reason:decision.reason});
      events.push({...core,stateBefore:before,stateAfter:state.state,featureStatus,directionFeatures:pair,decision,firstEnterTimestamp:state.firstEnterTimestamp,entryCount:state.entryCount,p21UsedAsGate:false,safety:SAFETY});
    }
    return {events,transitions,status:'COMPLETE',gap,safety:SAFETY};
  }
  close(at){if(this.closed||sessionDate(at)!==this.date||minute(at)<930)throw Error('INVALID_SESSION_CLOSE');this.closed=true;const transitions=[];for(const [symbol,state] of this.states)if(state.state==='WATCHING'){state.state='EXPIRED';state.expiredAt=at;transitions.push({symbol,at,to:'EXPIRED',reason:'SESSION_CLOSE'});}return transitions;}
}

// Attach labels only downstream of the frozen feature row. No label feeds a decision.
export function attachPrimaryTarget(row,labelBundle){
  const {featureSha256,...core}=row;if(sha256(core)!==featureSha256)throw Error('FEATURE_FREEZE_MISMATCH');
  if(labelBundle.eventId!==`${row.sessionDate}|${row.decisionTimestamp}|${row.symbol}`||labelBundle.contractSha256!==CONTRACT_SHA256||labelBundle.featureSha256!==featureSha256||labelBundle.roundTripCostBps!==5)throw Error('LABEL_LINEAGE_MISMATCH');
  if(labelBundle.featureFrozenBeforeLabels!==true)throw Error('LABEL_NOT_AFTER_FEATURE_FREEZE');
  const h=labelBundle.horizons?.[3],key=row.direction===1?'LONG':'SHORT';
  if(!h?.complete)return {...row,target:null,targetStatus:'UNLABELED'};
  let t=ms(row.decisionTimestamp);const expected=[];
  for(let i=0;i<3;i++){if(minute(iso(t))>=690&&minute(iso(t))<750)t=ms(`${row.sessionDate}T12:30:00+09:00`);if(minute(iso(t))>=930)throw Error('OVERNIGHT_LABEL_FORBIDDEN');expected.push(iso(t));t+=300000;}
  if(JSON.stringify(h.barStarts)!==JSON.stringify(expected)||ms(h.outcomeAvailableAt)<t||sessionDate(h.outcomeAvailableAt)!==row.sessionDate)throw Error('LABEL_GRID_OR_AVAILABILITY_MISMATCH');
  const value=h[key];if(!value||!finite(value.grossReturnBps)||!finite(value.netReturnBps)||Math.abs(value.grossReturnBps-5-value.netReturnBps)>1e-9)throw Error('INVALID_LABEL_COST');
  return {...row,target:Number(value.netReturnBps>0),targetStatus:'LABELED',targetContract:CONTRACT.target.primary};
}

export function validationAdmission({trainingDatasetIds=[],modelFrozen=false,thresholdFrozen=false,independentReviewPassed=false,accessLedgerComplete=false,winnerRuleFrozen=false}={}){
  const blockers=[];if(!trainingDatasetIds.length)blockers.push('NO_AUTHORIZED_TRAINING_DATASET');
  if(!CONTRACT.model.trainingDatasetIds.length)blockers.push('TRAINING_CONTRACT_NOT_AUTHORIZED');
  for(const [key,value] of Object.entries({modelFrozen,thresholdFrozen,independentReviewPassed,accessLedgerComplete,winnerRuleFrozen}))if(value!==true)blockers.push(key);
  return {allowed:blockers.length===0,blockers,safety:SAFETY};
}
