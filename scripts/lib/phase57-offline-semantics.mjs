import assert from 'node:assert/strict';
import {instant,iso,jstDate,exposedDate,symbolId,hash,SAFETY} from './phase57-offline-parity.mjs';

const minute=t=>{const s=iso(instant(t)+32400000);return Number(s.slice(11,13))*60+Number(s.slice(14,16));};
const endpoint=t=>instant(t)%300000===0&&((minute(t)>540&&minute(t)<=690)||(minute(t)>750&&minute(t)<=930));
export function classifyGap(previous,current,{savedFixture=false,sourceMissingConfirmed=false,sessionTransitionConfirmed=false}={}){
  const a=instant(previous),b=instant(current);
  if(b<=a||!endpoint(previous)||!endpoint(current))return 'INVALID_5M_GRID';
  if(jstDate(previous)!==jstDate(current))return sessionTransitionConfirmed&&minute(previous)===930&&minute(current)===545?'EXPECTED_SESSION_GAP':'UNKNOWN';
  if(b-a===300000)return null;
  if(minute(previous)===690&&minute(current)===755)return 'LUNCH_BREAK';
  return sourceMissingConfirmed?'SOURCE_MISSING':savedFixture?'FIXTURE_LIMITATION':'UNKNOWN';
}

const fields=['captureId','symbol','sourceDate','sourceTime','captureAt','open','high','low','close','volume','marketTimestamp','connected','workbookHealthy','rssError'];
// SOURCE SEMANTICS ONLY: no Entry, EXIT or portfolio evaluation.
// Unchanging values and successor rows are observations, NOT finalization proof.
export function diagnoseSnapshots(snapshots){
  assert.ok(Array.isArray(snapshots)&&snapshots.length,'EMPTY_CAPTURE');
  const seen=new Map(),bars=new Map(),events=[];let last=-Infinity;
  for(const row of snapshots){
    assert.ok(Object.keys(row).every(k=>fields.includes(k)),'STRATEGY_OR_UNKNOWN_FIELD_FORBIDDEN');
    exposedDate(row.sourceDate);symbolId(row.symbol);
    const t=instant(row.captureAt);assert.ok(t>=last,'CAPTURE_ORDER');last=t;
    assert.equal(jstDate(row.captureAt),row.sourceDate,'TIMEZONE_MISMATCH');
    assert.match(row.sourceTime,/^\d\d:\d\d:00$/);
    const source=instant(`${row.sourceDate}T${row.sourceTime}+09:00`);
    assert.ok(typeof row.captureId==='string'&&row.captureId.length>0,'CAPTURE_ID_REQUIRED');
    if(seen.has(row.captureId)){assert.equal(seen.get(row.captureId),hash(row),'CONFLICTING_CAPTURE_ID');events.push({captureId:row.captureId,cause:'DUPLICATE_CAPTURE'});continue;}
    seen.set(row.captureId,hash(row));
    const reasons=[];
    if(row.connected!==true)reasons.push('MSII_DISCONNECTED');
    if(row.workbookHealthy!==true)reasons.push('EXCEL_CAPTURE_FAILURE');
    if(row.rssError)reasons.push('RSS_CELL_ERROR');
    if(!['open','high','low','close','volume'].every(k=>Number.isFinite(row[k]))||row.volume<0||Math.min(row.open,row.low,row.close)<=0||row.low>Math.min(row.open,row.close)||row.high<Math.max(row.open,row.low,row.close))reasons.push('MALFORMED_NUMERIC_CELL');
    const m=minute(row.captureAt),active=(m>=540&&m<690)||(m>=750&&m<930);
    if(!row.marketTimestamp)reasons.push('MISSING_MARKET_TIMESTAMP');
    else{const mt=instant(row.marketTimestamp);if(mt>t)reasons.push('FUTURE_MARKET_TIMESTAMP');else if(active&&t-mt>30000)reasons.push('RSS_STALE_DATA');}
    if(source>t)reasons.push('SOURCE_LABEL_AFTER_CAPTURE');
    const key=row.symbol+'|'+row.sourceDate+'|'+row.sourceTime;
    let b=bars.get(key);
    if(!b){b={symbol:row.symbol,sourceDate:row.sourceDate,sourceTime:row.sourceTime,firstObservedAt:row.captureAt,lastObservedAt:row.captureAt,lastChangedAt:row.captureAt,versions:0,observations:0,valueHash:null,finalization:'UNVERIFIED',labelHypotheses:{START:{barStart:iso(source),barEnd:iso(source+300000)},END:{barStart:iso(source-300000),barEnd:iso(source)}}};bars.set(key,b);}
    const valueHash=hash(['open','high','low','close','volume'].map(k=>row[k]));
    if(b.valueHash!==valueHash){b.versions++;b.lastChangedAt=row.captureAt;b.valueHash=valueHash;}else reasons.push('UNCHANGED_SNAPSHOT_NOT_FINALITY_PROOF');
    b.observations++;b.lastObservedAt=row.captureAt;
    for(const cause of reasons)events.push({captureId:row.captureId,cause});
  }
  const windows={open0900:false,morning1130:false,reopen1230:false,close1530:false};
  for(const row of snapshots){const m=minute(row.captureAt);if(m>=540&&m<=545)windows.open0900=true;if(m>=685&&m<=695)windows.morning1130=true;if(m>=750&&m<=755)windows.reopen1230=true;if(m>=925&&m<=935)windows.close1530=true;}
  for(const b of bars.values())for(const candidate of Object.values(b.labelHypotheses))candidate.validSessionGrid=endpoint(candidate.barEnd);
  return {schemaId:'ARK_SOURCE_SEMANTICS_DIAGNOSTIC_V1',classification:'SYNTHETIC_OR_USED_SOURCE_DIAGNOSTIC_NOT_STRATEGY',snapshots:snapshots.length,uniqueCaptures:seen.size,bars:[...bars.values()],events,coverageWindows:windows,sourceLabel:'UNVERIFIED',finalization:'UNVERIFIED',strategyCalculated:false,readyForStrategy:false,safety:SAFETY};
}

export function tickSnapshotDiagnostic(ticks){
  assert.ok(Array.isArray(ticks)&&ticks.length<=300,'TICK_ROW_LIMIT');
  const counts=new Map();
  for(const t of ticks){assert.deepEqual(Object.keys(t).sort(),['price','timestamp','volume']);exposedDate(jstDate(t.timestamp));assert.ok(Number.isFinite(t.price)&&t.price>0&&Number.isFinite(t.volume)&&t.volume>=0,'INVALID_TICK');const id=hash(t);counts.set(id,(counts.get(id)??0)+1);}
  return {rows:ticks.length,identicalRowRepeats:[...counts.values()].reduce((n,x)=>n+x-1,0),rowsDropped:0,interpretation:'IDENTICAL_TICKS_MAY_BE_DISTINCT_TRADES_NO_DEDUP_WITHOUT_SOURCE_ID',modelInput:false};
}
