import assert from 'node:assert/strict';
import {hash,instant,iso,jstDate,SAFETY} from './phase57-offline-parity.mjs';
import {admitMode} from './phase57-integration-gates.mjs';

const top=['mode','sourceClass','sourceIdentity','workbookIdentity','workbookVersion','fieldMapSha256','captureId','captureTimestamp','sessionDate','connected','workbookHealthy','partialRead','rows','error'];
const fields=['slot','generation','symbol','sourceCode','sourceDate','sourceTime','open','high','low','close','volume','marketTimestamp','currentPrice','bestBid','bestAsk','cellErrors'];
const minute=t=>{const s=iso(instant(t)+32400000);return Number(s.slice(11,13))*60+Number(s.slice(14,16));};
const grid=start=>{const m=minute(iso(start));return start%300000===0&&((m>=540&&m<690)||(m>=750&&m<930));};

/** Observer only. No model import, strategy output, finality inference, or data repair. */
export class SourceObserver {
  constructor(){this.seen=new Map();this.bars=new Map();this.slots=new Map();this.last=-Infinity;this.identity=null;this.events=[];this.captures=0;this.windows={open0900:false,morning1130:false,lunch:false,reopen1230:false,close1530:false};}
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
    const problems=[];const emit=cause=>problems.push({captureId:packet.captureId,cause});
    if(packet.connected===false)emit('SOURCE_DISCONNECTED');
    else if(packet.connected!==true)emit('SOURCE_CONNECTION_UNVERIFIED');
    if(packet.workbookHealthy!==true)emit('EXCEL_CAPTURE_FAILURE');
    if(packet.partialRead!==false)emit('PARTIAL_READ');
    if(packet.error&&packet.error!=='MSII_CONNECTION_UNVERIFIED')emit('EXCEL_CAPTURE_FAILURE');
    const m=minute(packet.captureTimestamp),active=(m>=540&&m<690)||(m>=750&&m<930);
    if(m>=540&&m<=545)this.windows.open0900=true;
    if(m>=685&&m<=695)this.windows.morning1130=true;
    if(m>690&&m<750)this.windows.lunch=true;
    if(m>=750&&m<=755)this.windows.reopen1230=true;
    if(m>=925&&m<=935)this.windows.close1530=true;
    const inCapture=new Map();
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
      try{const mt=instant(row.marketTimestamp);if(mt>t)emit('CLOCK_DRIFT_OR_FUTURE_SOURCE');else if(active&&t-mt>30000)emit('STALE_SOURCE_DATA');}catch{emit('MISSING_MARKET_TIMESTAMP');}
      const key=hash([row.symbol,row.sourceDate,row.sourceTime]),vh=hash(value);
      if(inCapture.has(key)){emit(inCapture.get(key)===vh?'DUPLICATE_ROW':'CONFLICTING_DUPLICATE_ROW');continue;}inCapture.set(key,vh);
      let b=this.bars.get(key);
      if(!b){b={symbol:row.symbol,sourceCode:row.sourceCode,sourceDate:row.sourceDate,sourceTime:row.sourceTime,firstAppearanceTime:packet.captureTimestamp,lastChangeTime:packet.captureTimestamp,lastObservedAt:packet.captureTimestamp,valueHash:vh,observations:0,revisions:0,
        safeCompletedBarTime:null,finalizedState:'UNVERIFIED',refreshLatencyMs:null,
        labelHypotheses:{START:{barStart:iso(label),barEnd:iso(label+300000),validSessionGrid:grid(label)},END:{barStart:iso(label-300000),barEnd:iso(label),validSessionGrid:grid(label-300000)}}};this.bars.set(key,b);}
      if(vh!==b.valueHash){b.revisions++;b.lastChangeTime=packet.captureTimestamp;b.valueHash=vh;emit('OBSERVED_VALUE_REVISION');}
      b.lastObservedAt=packet.captureTimestamp;b.observations++;
    }
    this.events.push(...problems);return {duplicate:false,problems,strategyAllowed:false};
  }
  report(){return {schemaId:'ARK_REAL_SOURCE_SEMANTICS_REPORT_V1',mode:'SOURCE_SEMANTICS_ONLY',captures:this.captures,bars:[...this.bars.values()],events:this.events,coverage:this.windows,
    finalization:'UNVERIFIED',sourceSemanticsCompatibility:'NEEDS_REVIEW',strategyCalculated:false,readyForStrategy:false,
    missingBarVerdict:'UNVERIFIED_UNTIL_LABEL_AND_UNIVERSE_CONTRACT_CONFIRMED',unchangedValuesProveFinality:false,safety:SAFETY};}
}
