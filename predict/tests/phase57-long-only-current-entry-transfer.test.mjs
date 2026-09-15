import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {
  assertCurrentEntryAssets,evaluateFrozenCurrentEntryLong,evaluateLongOnlyTransferSession,
  measureRemainingOpportunity,normalizeEntryBars,
} from '../long-only/phase57-long-only-current-entry-transfer.js';

const root=new URL('../../',import.meta.url);
const bytes=relative=>fs.readFileSync(new URL(relative,root));
const realModel=JSON.parse(bytes('predict/research/phase57-msh-entry-v1-model.json'));
const features=realModel.features;
const syntheticModel={...realModel,weights:features.map(()=>0),means:features.map(()=>0),scales:features.map(()=>1),intercept:2,threshold:.6};
const sessionDate='2024-11-11';
const bars=[];
for(let index=0;index<20;index++){
  const start=9*60+index*5,time=`${String(Math.floor(start/60)).padStart(2,'0')}:${String(start%60).padStart(2,'0')}`;
  const end=start+5,available=`${String(Math.floor(end/60)).padStart(2,'0')}:${String(end%60).padStart(2,'0')}`;
  const price=100+index*.1;
  bars.push({barStartJst:`${sessionDate}T${time}:00+09:00`,availableAtJst:`${sessionDate}T${available}:00+09:00`,open:price-.05,high:price+.15,low:price-.15,close:price,volume:1000+index});
}
const normalized=normalizeEntryBars(bars);
const candidate=index=>({sessionDate,symbol:String(1000+index),decisionTimestamp:`${sessionDate}T09:30:00+09:00`,decisionTimeJst:'09:30',
  decisionPrice:100.5,ridgeRank:index,ridgeScore:10-index,selectorOutcome:{opportunity1:1,opportunity2:0,opportunity3:0,opportunity5:0,mfePct:1.5,maePct:-.5}});

test('pins exact CURRENT Entry model, feature contract and implementation bytes',()=>{
  assert.equal(assertCurrentEntryAssets({model:realModel,modelBytes:bytes('predict/research/phase57-msh-entry-v1-model.json'),
    contractBytes:bytes('predict/research/phase57-minimal-stateful-entry-contract.json'),
    implementationBytes:bytes('scripts/lib/phase57-minimal-stateful-entry.mjs')}),true);
});

test('LONG-only adapter blocks at 09:30 and scores exact frozen features at 09:35',()=>{
  const early=evaluateFrozenCurrentEntryLong({candidate:candidate(1),bars:normalized,evaluationTimestamp:`${sessionDate}T09:30:00+09:00`,
    firstSelectionTimestamp:`${sessionDate}T09:30:00+09:00`,priorSelectionCount:0,model:syntheticModel});
  assert.equal(early.status,'BLOCKED');assert.match(early.reason,/INSUFFICIENT_PREFIX/);
  const ready=evaluateFrozenCurrentEntryLong({candidate:candidate(1),bars:normalized,evaluationTimestamp:`${sessionDate}T09:35:00+09:00`,
    firstSelectionTimestamp:`${sessionDate}T09:30:00+09:00`,priorSelectionCount:1,model:syntheticModel});
  assert.equal(ready.status,'PASS');assert.ok(ready.probability>.6);assert.equal(ready.entryReferencePrice,100.6);
});

test('stateful transfer preserves Top5 events and separates first PASS from repeated selection',()=>{
  const first=Array.from({length:5},(_,index)=>candidate(index+1));
  const second=first.map(row=>({...row,decisionTimestamp:`${sessionDate}T10:00:00+09:00`,decisionTimeJst:'10:00'}));
  const barsBySymbol=new Map(first.map(row=>[row.symbol,normalized]));
  const result=evaluateLongOnlyTransferSession({sessionDate,selections:[...first,...second],barsBySymbol,auctionsBySymbol:new Map(),model:syntheticModel});
  assert.equal(result.events.length,10);assert.equal(result.opportunities.length,5);
  assert.ok(result.events.slice(0,5).every(row=>row.directStatus==='BLOCKED'&&row.finalOpportunityStatus==='PASS'&&row.entryLatencyMinutes===5));
  assert.ok(result.events.slice(5).every(row=>row.directStatus==='PASS'&&row.directReason==='ALREADY_ENTERED_NO_REENTRY'));
  assert.ok(result.opportunities.every(row=>row.finalStatus==='PASS'&&row.latencyMinutes===5&&row.selectionCount===2));
  assert.equal(result.ticks.some(row=>row.status==='PASS'),true);
});

test('entry-time opportunity uses only future bars and true signed MAE',()=>{
  const measured=measureRemainingOpportunity({bars,auctions:[],referencePrice:100.6,evaluationTimestamp:`${sessionDate}T09:35:00+09:00`});
  assert.equal(measured.evaluable,true);assert.equal(measured.opportunity1,1);assert.ok(measured.mfePct>0);assert.ok(measured.maePct<=0);
});
