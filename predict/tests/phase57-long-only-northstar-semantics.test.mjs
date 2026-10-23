import assert from 'node:assert/strict';
import test from 'node:test';
import {normalizeAndAggregateMinuteRows} from '../long-only/phase57-long-only-integrated-dataset.js';
import {buildCausalL1Features,buildEvaluatorOnlyL1Label} from '../long-only/phase57-long-only-l1-labels-features.js';
import {buildFixedHorizonTargets} from '../long-only/phase57-long-only-l2-fixed-horizon.js';
import {normalizeMinuteProvenance,auditRowSemantics} from '../long-only/phase57-long-only-northstar-semantics.js';

const date='2024-01-04',symbol='11110';
const row=(time,close=100,{open=close,high=close,low=close,...other}={})=>({Date:date,Code:symbol,Time:time,O:open,H:high,L:low,C:close,Vo:10,Va:10*close,...other});
const daily={unadjustedClose:105,adjustedClose:105,adjustedPreviousClose:100,adjustmentScale:1};
const near=(actual,expected)=>assert.ok(Math.abs(actual-expected)<1e-8,`${actual} != ${expected}`);
function setup(rawRows,decisionTimeJst='09:30'){
  const intraday=normalizeAndAggregateMinuteRows(rawRows),minutes=normalizeMinuteProvenance(rawRows).get(`${date}|${symbol}`)??[];
  const feature=buildCausalL1Features({sessionDate:date,symbol,decisionTimeJst,bars5m:intraday.bars,previousAdjustedClose:100});
  const label=buildEvaluatorOnlyL1Label({sessionDate:date,symbol,decisionTimeJst,bars5m:intraday.bars,terminalAuctions:intraday.terminalAuctions,previousAdjustedClose:100,officialFinalAdjustedClose:105});
  const target=buildFixedHorizonTargets({featureRows:[feature],bars5m:intraday.bars,evaluatorOnlyLabels:label?[label]:[]})[0]??null;
  const args={feature,target,label,bars:intraday.bars,minutes,daily};
  return {...args,result:auditRowSemantics(args)};
}

test('raw provenance reproduces normalizer acceptance, deduplication and auction split',()=>{
  const rows=[row('08:59'),row('09:00'),row('09:00'),row('09:04',102),row('11:30',103),row('12:15'),row('12:30',104),row('15:30',105),row('16:00'),row('10:00',0),row('10:05',100,{high:99})];
  const original=normalizeAndAggregateMinuteRows(rows),minutes=normalizeMinuteProvenance(rows).get(`${date}|${symbol}`);
  assert.equal(minutes.length,original.bars.reduce((n,bar)=>n+bar.observedMinutes,0)+original.terminalAuctions.length);
  assert.deepEqual(minutes.map(x=>[x.minute,x.availableMinute,x.auction]),[[540,541,false],[544,545,false],[690,690,true],[750,751,false],[930,930,true]]);
  for(const bar of original.bars){
    const start=Number(bar.barStartJst.slice(11,13))*60+Number(bar.barStartJst.slice(14,16));
    const source=minutes.filter(x=>!x.auction&&x.minute>=start&&x.minute<start+5).at(-1);
    assert.equal(bar.close,source.close);
  }
  assert.throws(()=>normalizeMinuteProvenance([row('09:00'),row('09:00',101)]),/conflicting duplicate/);
  assert.throws(()=>normalizeAndAggregateMinuteRows([row('09:00'),row('09:00',101)]),/conflicting duplicate/);
  // Conflict detection also precedes outside-session rejection in the original.
  assert.throws(()=>normalizeMinuteProvenance([row('08:59'),row('08:59',101)]),/conflicting duplicate/);
});

test('dense six-bar horizon is exactly 30m and freshness reflects last minute rather than bucket end',()=>{
  const rows=[row('09:25'),row('09:29'),...['09:34','09:39','09:44','09:49','09:54','09:59'].map((t,i)=>row(t,101+i))];
  const {result}=setup(rows);
  assert.equal(result.horizonMinutes,30);assert.equal(result.legacyBucketAgeMin,0);assert.equal(result.legacySourceAgeMin,0);
  assert.equal(result.referenceAgeMin,0);assert.equal(result.referenceValid,1);
  near(result.y30Bps,600);near(result.strict30Bps,600);near(result.strict30FreshBps,600);
  assert.equal(result.futureOpportunity5,1);assert.equal(result.timeTo5Min,25);
});

test('lunch six observations give 90m while strict30 is unavailable without lunch bridging',()=>{
  const rows=[row('11:29'),...['12:34','12:39','12:44','12:49','12:54','12:59'].map((t,i)=>row(t,101+i))];
  const {result}=setup(rows,'11:30');
  assert.equal(result.horizonMinutes,90);assert.equal(result.strict30Bps,null);assert.equal(result.strict30FreshBps,null);
  assert.equal(result.referenceValid,1);assert.equal(result.timeTo5Min,85);
});

test('sparse bars separate source age, six-observation horizon and strict endpoint coverage',()=>{
  const rows=[row('09:25'),row('09:30',101),row('09:40',102),row('09:50',103),row('09:54',103),row('10:00',104),row('10:10',105),row('10:20',106)];
  const {result}=setup(rows);
  assert.equal(result.legacyBucketAgeMin,0);assert.equal(result.legacySourceAgeMin,4);assert.equal(result.referenceAgeMin,4);
  assert.equal(result.horizonMinutes,55);near(result.strict30Bps,300);
  const older=setup(rows.filter(x=>x.Time!=='09:54')).result;
  assert.equal(older.strict30Bps,null);assert.equal(older.horizonMinutes,55);
});

test('stale reference remains unscorable and future price is not imported into decision time',()=>{
  const {result}=setup([row('09:30'),row('10:00',150),row('10:05',160)],'10:00');
  assert.equal(result.legacyBucketAgeMin,25);assert.equal(result.legacySourceAgeMin,29);
  assert.equal(result.referenceAgeMin,29);assert.equal(result.referenceValid,0);assert.equal(result.referencePrice,null);
  assert.equal(result.futureMfePct,null);assert.equal(result.trueMaePct,null);assert.equal(result.timeTo5Min,null);
  assert.equal(result.futureOpportunity5,null);assert.equal(result.finalAdditionalPct,null);
  assert.equal(result.futureMinuteCount,2);
});

test('reference freshness boundary is inclusive at five minutes and excludes six',()=>{
  const atFive=setup([row('09:24'),row('09:30',105)]).result;
  const atSix=setup([row('09:23'),row('09:30',105)]).result;
  assert.equal(atFive.referenceAgeMin,5);assert.equal(atFive.referenceValid,1);assert.equal(atFive.futureOpportunity5,1);
  assert.equal(atSix.referenceAgeMin,6);assert.equal(atSix.referenceValid,0);assert.equal(atSix.futureOpportunity5,null);
});

test('auction exactly at decision supplies reference but is excluded from future path',()=>{
  const {result}=setup([row('11:29'),row('11:30',110),row('12:30',116),row('15:30',117)],'11:30');
  assert.equal(result.legacyReferencePrice,100);assert.equal(result.referencePrice,110);assert.equal(result.referenceChanged,1);assert.equal(result.referenceAgeMin,0);
  assert.equal(result.futureMinuteCount,2);near(result.futureMfePct,100*(117/110-1));
  assert.equal(result.futureOpportunity5,1);assert.equal(result.timeTo5Min,61);
  assert.equal(result.trueMaePct,0);
});

test('raw positive MAE is preserved and clipped adverse MAE is zero',()=>{
  const rows=[row('09:29'),...['09:34','09:39','09:44','09:49','09:54','09:59'].map((t,i)=>row(t,101+i))];
  const {result}=setup(rows);
  near(result.rawMae30Pct,1);near(result.legacySessionMaePct,1);
  assert.equal(result.trueMae30Pct,0);assert.equal(result.legacyTrueSessionMaePct,0);assert.equal(result.trueMaePct,0);
});

test('future hit boundary uses direct exact ratio without optimized epsilon',()=>{
  const exact=setup([row('09:29'),row('09:30',105)]).result;
  const below=setup([row('09:29'),row('09:30',104.999999)]).result;
  assert.equal(exact.futureOpportunity5,1);assert.equal(exact.timeTo5Min,1);
  assert.equal(below.futureOpportunity5,0);assert.equal(below.timeTo5Min,null);
});

test('empty future path and null target never become zero outcome labels',()=>{
  const {result}=setup([row('14:59')],'15:00');
  assert.equal(result.referenceValid,1);assert.equal(result.futureMinuteCount,0);
  for(const name of ['futureMfePct','trueMaePct','futureOpportunity5','y30Bps','horizonMinutes','rawMae30Pct','strict30Bps'])assert.equal(result[name],null,name);
});

test('provenance corruption and cross-session data fail closed',()=>{
  const args=setup([row('09:29'),row('09:30',105)]);
  assert.throws(()=>auditRowSemantics({...args,feature:{...args.feature,currentPrice:99}}),/reference close provenance mismatch/);
  assert.throws(()=>auditRowSemantics({...args,bars:args.bars.map((bar,i)=>i===0?{...bar,close:99}:bar)}),/bar close provenance mismatch/);
  assert.throws(()=>auditRowSemantics({...args,minutes:[...args.minutes,{...args.minutes[1],sessionDate:'2024-01-05'}]}),/cross-session/);
  assert.throws(()=>auditRowSemantics({...args,target:{target30AvailableAtJst:'2024-01-05T10:00:00+09:00'}}),/cross-session target/);
});

test('same-session de-adjusted official close is retained for final reference outcome',()=>{
  const args=setup([row('09:29'),row('09:30',105)]);
  const result=auditRowSemantics({...args,daily:{adjustedClose:10.5,adjustedPreviousClose:10,adjustmentScale:0.1}});
  near(result.finalAdditionalPct,5);near(result.finalPreviousReturnPct,5);
});
