import assert from 'node:assert/strict';
import {isDeepStrictEqual} from 'node:util';
import {compareRecords,exposedDate,instant,SAFETY,FREEZE} from './phase57-offline-parity.mjs';
export const STAGES=['DATA','SELECTOR','ENTRY','ALLOCATION','EXIT','LEDGER'];
const fraction=(a,b,fields)=>{const A=new Map(a.map(x=>[x.id,x])),B=new Map(b.map(x=>[x.id,x])),ids=[...new Set([...A.keys(),...B.keys()])];let exact=0;for(const id of ids)if(A.has(id)&&B.has(id)&&fields.every(k=>Object.hasOwn(A.get(id),k)&&Object.hasOwn(B.get(id),k)&&isDeepStrictEqual(A.get(id)[k],B.get(id)[k])))exact++;return ids.length?exact/ids.length:null;};
const delta=(a,b,key,time=false)=>{const B=new Map(b.map(x=>[x.id,x]));const xs=[];for(const x of a){const y=B.get(x.id);if(!y||x[key]==null||y[key]==null)continue;const l=time?instant(x[key]):x[key],r=time?instant(y[key]):y[key];assert.ok(Number.isFinite(l)&&Number.isFinite(r),'NONFINITE_COMPARISON_VALUE');xs.push(Math.abs(l-r));}xs.sort((a,b)=>a-b);const n=xs.length;return {matchedCount:n,median:n?(xs[Math.floor((n-1)/2)]+xs[Math.floor(n/2)])/2:null,max:n?xs.at(-1):null};};
/** Prepared six-stage comparator. Inputs are offline normalized records, never data-fetch commands. */
export function compareDay(left,right){
  for(const x of [left,right]){assert.ok(['USED_HISTORICAL_FIXTURE','SYNTHETIC_TRANSPORT_TEST'].includes(x.sourceClass),'REAL_CAPTURE_LOCKED');exposedDate(x.sessionDate);assert.equal(x.freezeSha256,FREEZE);for(const stage of STAGES)assert.ok(Array.isArray(x[stage]),'STAGE_ARRAY_REQUIRED');}
  assert.equal(left.sessionDate,right.sessionDate);assert.equal(left.sourceClass,right.sourceClass);
  const stages=STAGES.map(stage=>compareRecords(left[stage],right[stage],{stage}));
  const counts={};for(const s of stages)for(const m of s.mismatches)counts[m.primaryCause]=(counts[m.primaryCause]??0)+1;
  const entryTime=delta(left.ENTRY,right.ENTRY,'timestamp',true),entryPrice=delta(left.ENTRY,right.ENTRY,'referencePrice'),exitTime=delta(left.EXIT,right.EXIT,'timestamp',true);
  const terminal=(rows)=>[...rows].sort((a,b)=>instant(a.timestamp)-instant(b.timestamp)).at(-1);
  const l=terminal(left.LEDGER),r=terminal(right.LEDGER),sameTerminal=l&&r&&instant(l.timestamp)===instant(r.timestamp);
  return {schemaId:'ARK_PARITY_DAILY_V1',classification:left.sourceClass,sessionDate:left.sessionDate,freezeSha256:FREEZE,stages,metrics:{
    eligibleDecisionTimestamps:new Set(right.ENTRY.map(x=>x.timestamp)).size,
    fiveMinuteExactMatchRate:fraction(left.DATA,right.DATA,['symbol','timestamp','open','high','low','close','volume']),
    selectorSetMatchRate:fraction(left.SELECTOR,right.SELECTOR,['candidateSymbols']),
    selectedSymbolMatchRate:fraction(left.SELECTOR,right.SELECTOR,['selectedSymbols']),
    firstEnterExactMatchRate:fraction(left.ENTRY.filter(x=>x.action==='ENTER'),right.ENTRY.filter(x=>x.action==='ENTER'),['action','symbol','direction','timestamp','probability','features']),
    directionMatchRate:fraction(left.ENTRY.filter(x=>x.action==='ENTER'),right.ENTRY.filter(x=>x.action==='ENTER'),['direction']),
    entryTimestampDelta:entryTime,entryReferencePriceDelta:entryPrice,
    allocationAcceptedSetMatchRate:fraction(left.ALLOCATION,right.ALLOCATION,['acceptedSymbols']),
    quantityExactMatchRate:fraction(left.ALLOCATION,right.ALLOCATION,['quantities']),
    exitDecisionMatchRate:fraction(left.EXIT,right.EXIT,['exit','reason','barsHeld']),exitTimestampDelta:exitTime,
    shadowPnlDeltaJpy:sameTerminal?l.realizedPnlJpy-r.realizedPnlJpy:null,
    shadowEquityDeltaJpy:sameTerminal?l.equityJpy-r.equityJpy:null,
    mismatchCountsByCause:counts,missingEvents:left.health?.missingEvents??null,staleEvents:left.health?.staleEvents??null,
    excelRssUptime:left.health?.excelRssUptime??null,
  },reservedDataOpened:false,realSessionCaptured:false,safety:SAFETY};
}
