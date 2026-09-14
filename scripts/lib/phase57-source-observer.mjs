import assert from 'node:assert/strict';
import {hash,instant,iso,jstDate,SAFETY} from './phase57-offline-parity.mjs';
import {admitMode} from './phase57-integration-gates.mjs';

const top=['mode','sourceClass','sourceIdentity','workbookIdentity','workbookVersion','fieldMapSha256','captureId','captureTimestamp','sessionDate','connected','workbookHealthy','partialRead','rows','error'];
const fields=['slot','generation','symbol','sourceCode','sourceDate','sourceTime','open','high','low','close','volume','marketTimestamp','currentPrice','bestBid','bestAsk','cellErrors'];
const minute=t=>{const s=iso(instant(t)+32400000);return Number(s.slice(11,13))*60+Number(s.slice(14,16));};
const grid=start=>{const m=minute(iso(start));return start%300000===0&&((m>=540&&m<690)||(m>=750&&m<930));};

/** Observer only. No model import, strategy output, finality inference, or data repair. */
export class SourceObserver {
  constructor(){this.seen=new Map();this.bars=new Map();this.slots=new Map();this.last=-Infinity;this.identity=null;this.events=[];this.captures=0;this.feedObservations=[];this.connectionState='SOURCE_CONNECTION_UNVERIFIED';this.windows={open0900:false,morning1130:false,lunch:false,reopen1230:false,close1530:false};}
  step(packet){
    assert.ok(Object.keys(packet).every(k=>top.includes(k)),'UNEXPECTED_SOURCE_FIELD');
    assert.equal(packet.mode,'SOURCE_SEMANTICS_ONLY');admitMode(packet);
    for(const key of ['sourceIdentity','workbookIdentity','workbookVersion','captureId'])assert.ok(typeof packet[key]==='string'&&packet[key].length,`${key}_REQUIRED`);
    assert.match(packet.fieldMapSha256,/^[a-f0-9]{64}$/);
    const identity=hash([packet.sourceIdentity,packet.workbookIdentity,packet.workbookVersion,packet.fieldMapSha256,packet.sourceClass,packet.sessionDate]);
    if(this.identity!==null)assert.equal(identity,this.identity,'SOURCE_IDENTITY_CHANGED');
    const fingerprint=hash(packet);
    if(this.seen.has(packet.captureId)){assert.equal(this.seen.get(packet.captureId),fingerprint,'CONFLICTING_CAPTURE');return {duplicate:true};}
    const t=instant(packet.captureTimestamp);assert.ok(t>=this.last,'CLOCK_OR_CAPTURE_ORDER');
    assert.equal(jstDate(packet.captureTimestamp),packet.sessionDate,'TIMEZONE_MISMATCH');
    assert.ok(Array.isArray(packet.rows),'ROWS_REQUIRED');
    for(const row of packet.rows)assert.ok(Object.keys(row).every(k=>fields.includes(k)),'STRATEGY_OR_UNKNOWN_ROW_FIELD');
    this.identity=identity;this.last=t;this.seen.set(packet.captureId,fingerprint);this.captures++;
    const problems=[];const emitted=new Set();const emit=(cause,symbol=null)=>{const k=JSON.stringify([cause,symbol]);if(!emitted.has(k)){emitted.add(k);problems.push({captureId:packet.captureId,cause,...(symbol?{symbol}:{})});}};
    if(packet.connected===false)emit('SOURCE_DISCONNECTED');

    if(packet.workbookHealthy!==true)emit('EXCEL_CAPTURE_FAILURE');
    if(packet.partialRead!==false)emit('PARTIAL_READ');
    if(packet.error&&!['MSII_CONNECTION_UNVERIFIED','INCONSISTENT_EXCEL_SNAPSHOT'].includes(packet.error))emit('EXCEL_CAPTURE_FAILURE');
    const m=minute(packet.captureTimestamp),active=(m>=540&&m<690)||(m>=750&&m<930);
    if(m>=540&&m<=545)this.windows.open0900=true;
    if(m>=685&&m<=695)this.windows.morning1130=true;
    if(m>690&&m<750)this.windows.lunch=true;
    if(m>=750&&m<=755)this.windows.reopen1230=true;
    if(m>=925&&m<=935)this.windows.close1530=true;
    const trusted=packet.workbookHealthy===true&&packet.partialRead===false&&(!packet.error||packet.error==='MSII_CONNECTION_UNVERIFIED');
    const feeds=new Map();
    for(const row of packet.rows){
      const k=JSON.stringify([row.slot,row.generation,row.symbol,row.sourceCode]);
      const signature=hash([row.marketTimestamp,row.currentPrice??null,row.bestBid??null,row.bestAsk??null]);
      if(feeds.has(k)){if(feeds.get(k).signature!==signature)feeds.get(k).conflict=true;continue;}
      feeds.set(k,{signature,symbol:row.symbol,marketTimestamp:row.marketTimestamp,chartPresent:false,
        currentPrice:row.currentPrice,bestBid:row.bestBid,bestAsk:row.bestAsk,conflict:false});
    }
    for(const f of feeds.values()){
      f.freshnessState='UNVERIFIED';f.ageMs=null;f.fresh=false;
      try{const mt=instant(f.marketTimestamp);f.ageMs=t-mt;
        if(mt>t){f.freshnessState='FUTURE_TIMESTAMP';emit('CLOCK_DRIFT_OR_FUTURE_SOURCE',f.symbol);}
        else if(jstDate(f.marketTimestamp)!==packet.sessionDate){f.freshnessState='WRONG_MARKET_DATE';emit('MARKET_DATE_MISMATCH',f.symbol);}
        else if(t-mt<=30000){f.fresh=true;f.freshnessState='FRESH';}
        else if(active){f.freshnessState='STALE';emit('STALE_SOURCE_DATA',f.symbol);}
        else f.freshnessState='INACTIVE_SESSION';
      }catch{emit('MISSING_MARKET_TIMESTAMP',f.symbol);}
      f.quotesValid=[f.currentPrice,f.bestBid,f.bestAsk].every(x=>typeof x==='number'&&Number.isFinite(x)&&x>0)&&f.bestBid<=f.bestAsk;
      if(!f.quotesValid)emit('INVALID_CURRENT_QUOTES',f.symbol);
      if(f.conflict)emit('CONFLICTING_CURRENT_FEED',f.symbol);
    }
    const inCapture=new Map();
    const previousKeys=new Set(this.bars.keys());
    for(const row of packet.rows){
      if(!Number.isInteger(row.slot)||row.slot<0||!Number.isInteger(row.generation)||row.generation<0||!/^\d{4,5}\.T$/.test(row.symbol)||typeof row.sourceCode!=='string'){emit('SYMBOL_MAPPING_DIFFERENCE');continue;}
      const old=this.slots.get(row.slot),mapping=hash([row.symbol,row.sourceCode]);
      if(old&&(row.generation<old.generation||(mapping!==old.mapping&&row.generation<=old.generation))){emit('SYMBOL_MAPPING_DIFFERENCE');continue;}
      this.slots.set(row.slot,{generation:row.generation,mapping});
      if(row.sourceDate!==packet.sessionDate||!/^\d{2}:\d{2}:00$/.test(row.sourceTime)){emit('SOURCE_DATE_TIME_INVALID');continue;}
      const label=Date.parse(`${row.sourceDate}T${row.sourceTime}+09:00`);
      if(!Number.isFinite(label)||iso(label+32400000).slice(11,19)!==row.sourceTime){emit('SOURCE_DATE_TIME_INVALID');continue;}
      const value=['open','high','low','close','volume'].map(k=>row[k]);
      if(!value.every(x=>typeof x==='number'&&Number.isFinite(x))||row.low<=0||row.high<Math.max(row.open,row.close,row.low)||row.low>Math.min(row.open,row.close)||row.volume<0||(row.cellErrors?.length??0)>0){emit('MALFORMED_SOURCE_CELL');continue;}
      const f=feeds.get(JSON.stringify([row.slot,row.generation,row.symbol,row.sourceCode]));
      if((grid(label)||grid(label-300000))&&label<=t+300000)f.chartPresent=true;
      if(!trusted)continue; // preserve packet in journal, but do not learn timing from torn reads
      const key=hash([row.symbol,row.sourceDate,row.sourceTime]),vh=hash(value);
      if(inCapture.has(key)){emit(inCapture.get(key)===vh?'DUPLICATE_ROW':'CONFLICTING_DUPLICATE_ROW');continue;}inCapture.set(key,vh);
      let b=this.bars.get(key);
      if(!b){b={symbol:row.symbol,sourceCode:row.sourceCode,sourceDate:row.sourceDate,sourceTime:row.sourceTime,firstAppearanceTime:packet.captureTimestamp,lastChangeTime:packet.captureTimestamp,lastObservedAt:packet.captureTimestamp,valueHash:vh,observations:0,revisions:0,
        safeCompletedBarTime:null,finalizedState:'UNVERIFIED',refreshLatencyMs:null,nextBarFirstAppearanceTime:null,nextSourceTime:null,candidateFinalizationLatencyMs:null,revisionsAfterNextAppearance:0,
        firstAppearanceLatencyMs:{START:t-label,END:t-(label-300000)},
        labelHypotheses:{START:{barStart:iso(label),barEnd:iso(label+300000),validSessionGrid:grid(label)},END:{barStart:iso(label-300000),barEnd:iso(label),validSessionGrid:grid(label-300000)}}};this.bars.set(key,b);}
      if(vh!==b.valueHash){if(b.nextBarFirstAppearanceTime){b.revisionsAfterNextAppearance++;b.candidateFinalizationLatencyMs=null;emit('REVISION_AFTER_NEXT_BAR_APPEARANCE');}b.revisions++;b.lastChangeTime=packet.captureTimestamp;b.valueHash=vh;emit('OBSERVED_VALUE_REVISION');}
      b.lastObservedAt=packet.captureTimestamp;b.observations++;
    }
    // Only a newly observed adjacent successor after a prior capture supplies a candidate.
    // Initial backfills, lunch gaps and simultaneous first observations supply no finality evidence.
    const observed=[...this.bars.entries()].filter(([k])=>inCapture.has(k));
    for(const [key,b] of observed){
      if(previousKeys.has(key))continue;
      const label=instant(`${b.sourceDate}T${b.sourceTime}+09:00`);
      const priorKey=hash([b.symbol,b.sourceDate,iso(label-300000+32400000).slice(11,19)]);
      const prior=this.bars.get(priorKey);
      if(previousKeys.has(priorKey)&&prior&&grid(label)&&grid(label-300000)&&instant(prior.firstAppearanceTime)<t){
        prior.nextBarFirstAppearanceTime=packet.captureTimestamp;prior.nextSourceTime=b.sourceTime;
        prior.candidateFinalizationLatencyMs=t>=label?t-label:null;
        prior.candidateFinalizationLabelHypothesis='START';
        prior.successorAppearanceLatencyMs={START:t-label,END:t-(label-300000)};
      }
    }
    const feedList=[...feeds.values()].map(({signature,...f})=>({...f,captureId:packet.captureId,captureTimestamp:packet.captureTimestamp,
      connectionState:trusted&&packet.connected!==false&&f.fresh&&f.quotesValid&&f.chartPresent&&!f.conflict?'REAL_SOURCE_CONNECTED_OBSERVED':'SOURCE_CONNECTION_UNVERIFIED'}));
    this.connectionState=feedList.length&&feedList.every(f=>f.connectionState==='REAL_SOURCE_CONNECTED_OBSERVED')?'REAL_SOURCE_CONNECTED_OBSERVED':'SOURCE_CONNECTION_UNVERIFIED';
    if(this.connectionState!=='REAL_SOURCE_CONNECTED_OBSERVED'&&packet.connected!==false)emit('SOURCE_CONNECTION_UNVERIFIED');
    this.feedObservations.push(...feedList);
    this.events.push(...problems);return {duplicate:false,problems,connectionState:this.connectionState,currentFeeds:feedList,strategyAllowed:false};
  }
  report(){
    const latest=new Map();
    for(const b of this.bars.values()){const prior=latest.get(b.symbol);if(!prior||b.sourceTime>prior.sourceTime)latest.set(b.symbol,b);}
    const latestBars=[...latest.values()].map(b=>({symbol:b.symbol,latestSourceTime:b.sourceTime,
      latestBarFirstAppearance:b.firstAppearanceTime,latestBarLastChange:b.lastChangeTime,latestBarRevisions:b.revisions,
      latestBarAgeMs:this.last-instant(`${b.sourceDate}T${b.sourceTime}+09:00`),barAgeMeaning:'SOURCE_LABEL_AGE_NOT_FEED_STALENESS',
      candidateFinalizationLatencyMs:b.candidateFinalizationLatencyMs,labelHypothesis:'START_UNVERIFIED'}));
    return {connectionState:this.connectionState,currentFeedObservations:this.feedObservations,latestBars,
      ...(latestBars.length===1?latestBars[0]:{}),currentFeedFreshnessLimitMs:30000,feedFreshnessMeaning:'CURRENT_PRICE_UPDATE_AGE_NOT_CONNECTION_HEARTBEAT',schemaId:'ARK_REAL_SOURCE_SEMANTICS_REPORT_V1',mode:'SOURCE_SEMANTICS_ONLY',captures:this.captures,bars:[...this.bars.values()],events:this.events,coverage:this.windows,
    finalization:'UNVERIFIED',sourceSemanticsCompatibility:'NEEDS_REVIEW',strategyCalculated:false,readyForStrategy:false,
    missingBarVerdict:'UNVERIFIED_UNTIL_LABEL_AND_UNIVERSE_CONTRACT_CONFIRMED',unchangedValuesProveFinality:false,safety:SAFETY};}
}
