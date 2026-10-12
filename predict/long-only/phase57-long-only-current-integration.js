import {createHash} from 'node:crypto';
import {buildProspectiveP21FeatureFeed} from '../daytrade/phase57-p21-prospective-feature-feed.js';
import {selectInnerAdaptiveHorizon} from '../daytrade/phase57-nested-adaptive-horizon.js';
import {trainModel} from '../models/phase47-real-training.js';
import {simulateFrozenRatchetExit} from '../daytrade/phase57-frozen-ratchet-exit.js';
import {selectJpxOpportunityUniverse} from '../daytrade/phase57-p25-jpx-opportunity-universe.js';

export const LONG_ONLY_CURRENT_INTEGRATION_CONTRACT=Object.freeze({
  contractId:'PHASE57_LONG_ONLY_NEW_SELECTOR_CURRENT_ENTRY_EXIT_V1',
  currentSelector:'PHASE57_P25_JPX_OPPORTUNITY_UNIVERSE_V1',
  currentEntry:'PHASE57_P21_NESTED_ADAPTIVE_PROSPECTIVE_V1',
  currentExit:'STATE_MONOTONIC_RATCHET_V1',
  entryFitPartition:'DEVELOPMENT_C',
  comparisonPartition:'DEVELOPMENT_D',
  currentSelectorCapacity:50,
  candidateSelectorCapacity:5,
  costPct:0.05,
  currentEntryOutcomeMayTuneNewSelector:false,
  newEntryResearchAllowed:false,
  newExitResearchAllowed:false,
});

const finite=value=>value!==null&&value!==undefined&&value!==''&&Number.isFinite(Number(value));
const key=row=>`${row.sessionDate}|${row.symbol}|${row.decisionTimeJst}`;
const sha=value=>createHash('sha256').update(JSON.stringify(value)).digest('hex');
const iso=value=>new Date(value).toISOString();

function currentSelectorInput(row){
  return Object.freeze({
    symbol:String(row.symbol),sector:String(row.sector??'UNKNOWN'),market:String(row.segment??'UNKNOWN'),status:'analyzed',
    currentPrice:Number(row.currentPrice),volume:Number(row.cumulativeVolume),volumeRatio:Number(row.volumeAccelerationRatio),
    dailyChangePercent:Number(row.currentReturnPct),atrPercent:Number(row.causalAtr)/Number(row.currentPrice)*100,
    discoveryScore:50,technicalScore:50,confidence:0.5,qualityScore:50,scannedAt:String(row.decisionAtJst),
  });
}

export function selectCurrentSelectorCandidates(featureRows=[]){
  const groups=new Map();
  for(const row of featureRows){const k=`${row.sessionDate}|${row.decisionTimeJst}`;if(!groups.has(k))groups.set(k,[]);groups.get(k).push(row);}
  const selected=[];
  for(const rows of groups.values()){
    const source=new Map(rows.map(row=>[String(row.symbol),row]));
    const universe=selectJpxOpportunityUniverse({entries:rows.map(currentSelectorInput),dayCount:30,swingCount:30,maxCombinedCount:LONG_ONLY_CURRENT_INTEGRATION_CONTRACT.currentSelectorCapacity,maxPerSector:4,asOf:rows[0].decisionAtJst,maxAgeMs:null});
    for(const [rank,pick] of universe.combined.entries())selected.push(Object.freeze({...source.get(String(pick.symbol)),selectorRank:rank+1,selectorScore:Number(pick.opportunityScore),selectorId:universe.policy.sourceScope}));
  }
  return Object.freeze(selected);
}

function barsByIdentity(bars5m=[]){
  const map=new Map();
  for(const raw of bars5m){
    const k=`${raw.sessionDate}|${raw.symbol}`;
    if(!map.has(k))map.set(k,[]);
    map.get(k).push(Object.freeze({timestamp:iso(raw.availableAtJst??raw.timestamp),open:Number(raw.open),high:Number(raw.high),low:Number(raw.low),close:Number(raw.close),volume:Number(raw.volume??0)}));
  }
  for(const rows of map.values())rows.sort((a,b)=>a.timestamp.localeCompare(b.timestamp));
  return map;
}

function p21CurrentRow(candidate,bars,horizonBars){
  const cutoff=iso(candidate.decisionAtJst);
  const prefix=bars.filter(bar=>bar.timestamp<=cutoff);
  const feed=buildProspectiveP21FeatureFeed({symbol:String(candidate.symbol),sessionDate:String(candidate.sessionDate),bars5m:prefix,horizons:[horizonBars],latestBarClosed:true});
  return feed.complete?feed.currentRowsByHorizon[horizonBars]:null;
}

export function buildCurrentEntryTrainingRows({candidateRows=[],bars5m=[],horizons=[1,3,6,12,24]}={}){
  const lookup=barsByIdentity(bars5m),out=Object.fromEntries(horizons.map(h=>[h,[]]));
  for(const candidate of candidateRows){
    const bars=lookup.get(`${candidate.sessionDate}|${candidate.symbol}`)??[],cutoff=iso(candidate.decisionAtJst),index=bars.findIndex(bar=>bar.timestamp===cutoff);
    if(index<5)continue;
    const feed=buildProspectiveP21FeatureFeed({symbol:String(candidate.symbol),sessionDate:String(candidate.sessionDate),bars5m:bars.slice(0,index+1),horizons,latestBarClosed:true});
    if(!feed.complete)continue;
    for(const h of horizons){
      const future=bars[index+h],current=bars[index],base=feed.currentRowsByHorizon[h];
      if(!future||!base)continue;
      const actualReturnPct=100*(future.close/current.close-1);
      out[h].push(Object.freeze({...base,outcomeAt:future.timestamp,outcomeSessionDate:candidate.sessionDate,label:actualReturnPct>=0?1:0,actualReturnPct,barrierBps:Math.abs(actualReturnPct)*100}));
    }
  }
  return Object.freeze(Object.fromEntries(Object.entries(out).map(([h,rows])=>[h,Object.freeze(rows)])));
}

function projected(row,names){return {...row,features:Object.fromEntries((names??Object.keys(row.features??{})).filter(name=>finite(row.features?.[name])).map(name=>[name,Number(row.features[name])]))};}

export function fitCurrentEntryAdapter({trainingRowsByHorizon}={}){
  const selection=selectInnerAdaptiveHorizon(trainingRowsByHorizon,{roundTripCostPct:LONG_ONLY_CURRENT_INTEGRATION_CONTRACT.costPct});
  if(!selection.selected)throw new Error('CURRENT Entry could not select a Development C prior-only candidate');
  const picked=selection.selected,rows=(trainingRowsByHorizon[picked.horizonBars]??[]).map(row=>projected(row,picked.featureKeys));
  const model=trainModel({rows,modelType:picked.modelType,options:picked.modelOptions});
  const identity={contractId:LONG_ONLY_CURRENT_INTEGRATION_CONTRACT.contractId,horizonBars:picked.horizonBars,featureFamily:picked.featureFamily,featureKeys:picked.featureKeys,modelType:picked.modelType,configId:picked.configId,threshold:picked.threshold,trainingRows:rows.length};
  return Object.freeze({picked:Object.freeze({...picked,signals:undefined}),model,artifactSha256:sha(identity),identity:Object.freeze(identity)});
}

export function applyCurrentEntryLongOnly({candidateRows=[],bars5m=[],adapter}={}){
  if(!adapter?.model||!adapter?.picked)throw new Error('frozen CURRENT Entry adapter required');
  const lookup=barsByIdentity(bars5m),accepted=[],blocked={NOT_READY:0,WAIT:0,SHORT:0};
  for(const candidate of candidateRows){
    const bars=lookup.get(`${candidate.sessionDate}|${candidate.symbol}`)??[],row=p21CurrentRow(candidate,bars,adapter.picked.horizonBars);
    if(!row){blocked.NOT_READY++;continue;}
    const probability=Math.max(0.001,Math.min(0.999,Number(adapter.model.predict(projected(row,adapter.picked.featureKeys))))),confidence=Math.max(probability,1-probability);
    if(confidence<Number(adapter.picked.threshold)){blocked.WAIT++;continue;}
    if(probability<0.5){blocked.SHORT++;continue;}
    accepted.push(Object.freeze({...candidate,entryTimestamp:iso(candidate.decisionAtJst),entryPrice:Number(candidate.currentPrice),signalDirection:1,entryAccepted:true,frozenBeforeOutcome:true,currentOutcomeUsed:false,entryProbability:probability,entryConfidence:confidence,currentEntryArtifactSha256:adapter.artifactSha256}));
  }
  return Object.freeze({accepted:Object.freeze(accepted),blocked:Object.freeze(blocked),shortTrades:0,marginTrades:0,leverage:0});
}

export function replayCurrentExitLongOnly({entries=[],bars5m=[]}={}){
  const lookup=barsByIdentity(bars5m),trades=[];
  for(const entry of entries){
    const bars=lookup.get(`${entry.sessionDate}|${entry.symbol}`)??[],cutoff=String(entry.entryTimestamp),index=bars.findIndex(bar=>bar.timestamp===cutoff);
    if(index<5||index>=bars.length-1)continue;
    const outcome=simulateFrozenRatchetExit({entryPrice:entry.entryPrice,signalDirection:'LONG',contextBars:bars.slice(0,index+1),futureBars:bars.slice(index+1),frozenEntry:true,sessionDate:entry.sessionDate});
    if(!outcome)continue;
    trades.push(Object.freeze({...entry,exitTimestamp:outcome.outcomeAt,exitPrice:outcome.exitPrice,exitReason:outcome.exitReason,netReturnPct:outcome.netReturnPct,grossReturnPct:outcome.grossReturnPct,mfePct:outcome.mfePct,maePct:outcome.maePct,mfeCapturePct:outcome.captureRatio===null?null:100*outcome.captureRatio,barsHeld:outcome.barsHeld}));
  }
  return Object.freeze(trades);
}

export default {selectCurrentSelectorCandidates,buildCurrentEntryTrainingRows,fitCurrentEntryAdapter,applyCurrentEntryLongOnly,replayCurrentExitLongOnly};
