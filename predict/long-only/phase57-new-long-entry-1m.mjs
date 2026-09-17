/** Research-only, LONG-only 1-minute Entry. No network, broker or model dependencies.
 * Prices are absolute; closed-bar availability is enforced before decisions.
 * Reference fills and all future outcomes are separate from the state machine.
 */
import {createHash} from 'node:crypto';
export const MINUTE = 60_000;
export const SAFETY = Object.freeze(Object.fromEntries([
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed',
  'transmitted'].map(k=>[k,false])));
export const SPEC = Object.freeze({id:'NEW_LONG_ENTRY_1M_DUAL_PATH_RESEARCH_V1',
  barMilliseconds:MINUTE,watchMinutes:30,holdingMinutes:30,deadlineMinutes:60,
  roundTripCostPct:0.05,epsilonRelative:1e-10,firstDecision:'AFTER_FIRST_COMPLETED_MINUTE',
  continuation:'NO_PRIOR_CLOSE_BELOW_SELECTION_AND_CLOSE_ABOVE_SELECTION_AND_OPEN',
  rebound:'PRIOR_CLOSE_BELOW_SELECTION_AND_LATER_CLOSE_ABOVE_PREVIOUS_HIGH_AND_OPEN',
  fill:'NEXT_SCHEDULED_OPEN_AT_OR_AFTER_INTENT',missing:'UNKNOWN_NO_FILL_NO_IMPUTATION',
  position:'ONE_FIRST_SELECTION_PER_SYMBOL_SESSION_NO_REENTRY',
  evidence:'UNVALIDATED_RESEARCH_PROTOTYPE',safety:SAFETY});
export function canonical(x) {
  if (Array.isArray(x)) return `[${x.map(canonical).join(',')}]`;
  if (x && typeof x==='object') return `{${Object.keys(x).sort().map(k=>`${JSON.stringify(k)}:${canonical(x[k])}`).join(',')}}`;
  if (typeof x==='number' && !Number.isFinite(x)) throw Error('NONFINITE_JSON');
  return JSON.stringify(x);
}
export const digest = x=>createHash('sha256').update(canonical(x)).digest('hex');
export const SPEC_SHA = digest(SPEC);
const num=x=>typeof x==='number'&&Number.isFinite(x);
const integer=x=>num(x)&&Number.isInteger(x);
const pos=x=>num(x)&&x>0;
const below=(a,b)=>a < b-SPEC.epsilonRelative*Math.max(1,Math.abs(b));
const above=(a,b)=>below(b,a);
const copy=x=>JSON.parse(JSON.stringify(x));
function validAnchor(a) {
  if (!a || typeof a.eventId!=='string'||!a.eventId || typeof a.symbol!=='string'||!a.symbol ||
      typeof a.sessionDate!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(a.sessionDate)||
      !integer(a.selectedAt)||a.selectedAt%MINUTE!==0||!pos(a.referencePrice)||
      !integer(a.segmentEnd)||a.segmentEnd%MINUTE!==0||a.segmentEnd<=a.selectedAt||
      (a.direction!==undefined&&a.direction!=='LONG')) throw Error('INVALID_LONG_ANCHOR');
  if (new Date(a.selectedAt+9*3600_000).toISOString().slice(0,10)!==a.sessionDate ||
      new Date(a.segmentEnd-1+9*3600_000).toISOString().slice(0,10)!==a.sessionDate)
    throw Error('ANCHOR_SESSION_MISMATCH');
}
function cleanBar(b) {
  if (!b||typeof b.symbol!=='string'||!integer(b.startAt)||b.startAt%MINUTE!==0||
      !integer(b.endAt)||b.endAt-b.startAt!==MINUTE||!num(b.availableAt)||b.availableAt<b.endAt||
      ![b.open,b.high,b.low,b.close].every(pos)||
      b.high<Math.max(b.open,b.close,b.low)||b.low>Math.min(b.open,b.close,b.high))
    throw Error('INVALID_CLOSED_MINUTE');
  return Object.fromEntries(['symbol','startAt','endAt','availableAt','open','high','low','close'].map(k=>[k,b[k]]));
}
export class MinuteEntry {
  #s;
  constructor(anchor) {
    validAnchor(anchor);
    const a=Object.fromEntries(['eventId','symbol','sessionDate','selectedAt','referencePrice','segmentEnd'].map(k=>[k,anchor[k]]));
    this.#s={anchor:a,state:'WATCH',expectedStart:a.selectedAt,lastBar:null,pullbackAt:null,
      deadline:Math.min(a.selectedAt+SPEC.watchMinutes*MINUTE,a.segmentEnd),intent:null,
      reason:null,trace:[],clock:a.selectedAt,specSHA:SPEC_SHA};
  }
  view(){return copy(this.#s);}
  #record(kind,at,reason){this.#s.trace.push({kind,at,reason});}
  #end(state,at,reason){this.#s.state=state;this.#s.reason=reason;this.#record(state,at,reason);return this.view();}
  missing(startAt,now) {
    if (this.#s.state!=='WATCH'&&this.#s.state!=='PULLBACK') return this.view();
    if (startAt!==this.#s.expectedStart||!num(now)||now<startAt+MINUTE) throw Error('INVALID_MISSING_EVENT');
    if (startAt>=this.#s.deadline) return this.#end('EXPIRED',now,'WATCH_DEADLINE');
    return this.#end('UNKNOWN',now,'REQUIRED_MINUTE_UNOBSERVED');
  }
  close(input,now) {
    // Decisions consume only a validated prefix, never evaluator labels or future extrema.
    const b=cleanBar(input),s=this.#s,a=s.anchor;
    if (b.symbol!==a.symbol) throw Error('SYMBOL_MISMATCH');
    if (!num(now)||b.availableAt>now) throw Error('BAR_NOT_AVAILABLE');
    if(now<s.clock)throw Error('CLOCK_MOVED_BACKWARDS');
    if (s.lastBar&&b.startAt===s.lastBar.startAt) {
      if (canonical(b)!==canonical(s.lastBar)) throw Error('CONFLICTING_BAR_REVISION');
      return this.view();
    }
    if (s.state==='ENTER_INTENT'||s.state==='EXPIRED'||s.state==='UNKNOWN') return this.view();
    if (b.startAt<s.expectedStart) throw Error('OUT_OF_ORDER_BAR');
    if (b.startAt>s.expectedStart) return this.#end('UNKNOWN',now,'MISSING_MINUTE_BEFORE_CURRENT');
    if (b.startAt>=s.deadline||now>s.deadline||b.endAt>=a.segmentEnd)
      return this.#end('EXPIRED',now,'NO_EXECUTABLE_TIME_BEFORE_BOUNDARY');
    s.clock=now;
    const prior=s.lastBar,wasPullback=s.pullbackAt!==null;
    const rebound=wasPullback&&prior&&b.startAt>=s.pullbackAt&&above(b.close,prior.high)&&above(b.close,b.open);
    const continuation=!wasPullback&&above(b.close,a.referencePrice)&&above(b.close,b.open);
    s.expectedStart=b.endAt;s.lastBar=b;
    if (rebound||continuation) {
      const route=rebound?'PULLBACK_REBOUND':'CONTINUATION';
      s.intent={eventId:a.eventId,symbol:a.symbol,direction:'LONG',decisionAt:now,
        eligibleOpenAt:Math.ceil(now/MINUTE)*MINUTE,route,specSHA:SPEC_SHA,safety:SAFETY};
      return this.#end('ENTER_INTENT',now,route);
    }
    if (!wasPullback&&below(b.close,a.referencePrice)) {
      s.pullbackAt=b.endAt;s.state='PULLBACK';this.#record('PULLBACK',now,'CLOSED_BELOW_SELECTION');
    } else this.#record(s.state,now,'NO_CONFIRMATION');
    return this.view();
  }
  finish(now) {
    if (!num(now)) throw Error('INVALID_CLOCK');
    if (['WATCH','PULLBACK'].includes(this.#s.state)) {
      if (now<this.#s.deadline) return this.view();
      if (this.#s.expectedStart<this.#s.deadline) return this.#end('UNKNOWN',now,'OBSERVATION_STREAM_TRUNCATED');
      return this.#end('EXPIRED',now,'WATCH_DEADLINE');
    }
    return this.view();
  }
  snapshot(){const payload=this.view();return {version:1,payload,sha256:digest(payload)};}
  static restore(snapshot) {
    if (snapshot?.version!==1||digest(snapshot.payload)!==snapshot.sha256||snapshot.payload.specSHA!==SPEC_SHA)
      throw Error('SNAPSHOT_IDENTITY_MISMATCH');
    const e=new MinuteEntry(snapshot.payload.anchor);
    const s=snapshot.payload;
    if (!['WATCH','PULLBACK','ENTER_INTENT','EXPIRED','UNKNOWN'].includes(s.state)||
        s.deadline!==e.#s.deadline||!Array.isArray(s.trace)||!integer(s.expectedStart)||
        s.expectedStart<s.anchor.selectedAt||s.expectedStart>s.deadline||
        (s.state==='ENTER_INTENT')!==Boolean(s.intent)) throw Error('SNAPSHOT_STATE_INVALID');
    e.#s=copy(s);return e;
  }
}
export function replayIntent(anchor,bars) {
  const e=new MinuteEntry(anchor),map=new Map();
  for (const raw of bars) {
    const b=cleanBar(raw);
    if (b.symbol!==anchor.symbol) throw Error('SYMBOL_MISMATCH');
    if (map.has(b.startAt)) throw Error('DUPLICATE_MINUTE');
    map.set(b.startAt,b);
  }
  const end=Math.min(anchor.selectedAt+30*MINUTE,anchor.segmentEnd);
  for(let t=anchor.selectedAt;t<end;t+=MINUTE){
    const b=map.get(t);
    const s=b?e.close(b,b.availableAt):e.missing(t,t+MINUTE);
    if (['ENTER_INTENT','EXPIRED','UNKNOWN'].includes(s.state)) return s;
  }
  return e.finish(end);
}
export function referenceFill(anchor,intent,bars,latencyMinutes=0) {
  if (!intent) return {status:'NO_INTENT',price:null,at:null};
  if (![0,1].includes(latencyMinutes)) throw Error('UNREGISTERED_LATENCY');
  if(!integer(intent.eligibleOpenAt)||intent.eligibleOpenAt%MINUTE!==0||intent.eligibleOpenAt<anchor.selectedAt||
     (num(intent.decisionAt)&&intent.eligibleOpenAt<intent.decisionAt))throw Error('FILL_BEFORE_DECISION');
  const at=intent.eligibleOpenAt+latencyMinutes*MINUTE;
  if (at>=anchor.segmentEnd) return {status:'UNKNOWN_BOUNDARY',price:null,at:null};
  const b=bars.find(x=>x.startAt===at);
  if (!b) return {status:'UNKNOWN_NEXT_OPEN',price:null,at:null};
  if (b.symbol!==anchor.symbol||!pos(b.open)) throw Error('INVALID_REFERENCE_FILL');
  return {status:'REFERENCE_FILLED',price:b.open,at,route:intent.route,
    semantics:'NEXT_SCHEDULED_OPEN_ZERO_QUEUE_ASSUMPTION',actualFillGuaranteed:false};
}
export function forwardWindow(anchor,bars,startAt,minutes) {
  if (!integer(minutes)||minutes<=0||!integer(startAt)||startAt%MINUTE!==0) throw Error('INVALID_WINDOW');
  if (startAt+minutes*MINUTE>anchor.segmentEnd) return null;
  const map=new Map(bars.map(b=>[b.startAt,b])),out=[];
  for(let t=startAt;t<startAt+minutes*MINUTE;t+=MINUTE){
    const b=map.get(t);if(!b) return null;out.push(b);
  }
  return out;
}
export const pct=(price,ref)=>{if(!pos(price)||!pos(ref))throw Error('INVALID_RATIO');return 100*(price/ref-1);};
export function outcome(window,fill) {
  if (!window||!window.length||fill?.status!=='REFERENCE_FILLED') return null;
  const hi=Math.max(...window.map(b=>b.high)),lo=Math.min(...window.map(b=>b.low));
  return {D30:Math.max(0,-pct(lo,fill.price)),MFE:Math.max(0,pct(hi,fill.price)),
    netPct:pct(window.at(-1).close,fill.price)-SPEC.roundTripCostPct};
}
export function evaluateAnchor(anchor,bars,latencyMinutes=0) {
  const state=replayIntent(anchor,bars);
  const baseIntent={eligibleOpenAt:anchor.selectedAt,route:'IMMEDIATE_BASELINE'};
  const baseline=referenceFill(anchor,baseIntent,bars,latencyMinutes);
  const challenger=referenceFill(anchor,state.intent,bars,latencyMinutes);
  const score=f=>f.status==='REFERENCE_FILLED'?outcome(forwardWindow(anchor,bars,f.at,30),f):null;
  const deadline=anchor.selectedAt+60*MINUTE;
  const common=f=>f.status==='REFERENCE_FILLED'&&f.at<deadline?
    outcome(forwardWindow(anchor,bars,f.at,(deadline-f.at)/MINUTE),f):null;
  const primaryPanel=Boolean(forwardWindow(anchor,bars,anchor.selectedAt,60));
  return {eventId:anchor.eventId,symbol:anchor.symbol,sessionDate:anchor.sessionDate,state,
    primaryPanel,baseline,challenger,baseline30:score(baseline),challenger30:score(challenger),
    baselineCommon:common(baseline),challengerCommon:common(challenger),
    priceImprovementPct:baseline.status==='REFERENCE_FILLED'&&challenger.status==='REFERENCE_FILLED'?
      -pct(challenger.price,baseline.price):null};
}
const mean=a=>a.length?a.reduce((s,x)=>s+x,0)/a.length:null;
export function distribution(a) {
  const s=a.filter(num).sort((a,b)=>a-b),n=s.length;
  if(!n)return {n:0,mean:null,median:null,p95:null,es95:null,worst:null};
  const q=p=>{const k=(n-1)*p,i=Math.floor(k);return s[i]+(s[Math.ceil(k)]-s[i])*(k-i);};
  return {n,mean:mean(s),median:q(.5),p95:q(.95),es95:mean(s.slice(-Math.max(1,Math.ceil(n*.05)))),worst:s.at(-1)};
}
export function aggregate(ledger) {
  const panel=ledger.filter(x=>x.primaryPanel),entered=panel.filter(x=>x.challenger.status==='REFERENCE_FILLED');
  const paired=entered.filter(x=>x.baseline30&&x.challenger30);
  const cap=k=>{const w=panel.filter(x=>x.baselineCommon?.MFE>=k);return {denominator:w.length,
    retained:w.filter(x=>x.challengerCommon?.MFE>=k).length,
    ratio:w.length?w.filter(x=>x.challengerCommon?.MFE>=k).length/w.length:null};};
  const known=panel.filter(x=>x.challengerCommon||x.state.state==='EXPIRED');
  return {anchors:ledger.length,panel:panel.length,entered:entered.length,
    throughput:panel.length?entered.length/panel.length:null,paired:paired.length,
    symbols:new Set(entered.map(x=>x.symbol)).size,sessions:new Set(entered.map(x=>x.sessionDate)).size,
    capture3:cap(3),capture5:cap(5),priceImprovement:distribution(entered.map(x=>x.priceImprovementPct)),
    baselineD30:distribution(paired.map(x=>x.baseline30.D30)),
    challengerD30:distribution(paired.map(x=>x.challenger30.D30)),
    commonPolicyN:known.length,commonPolicyNetDelta:mean(known.map(x=>(x.challengerCommon?.netPct??0)-x.baselineCommon.netPct)),
    unresolved:ledger.filter(x=>x.state.state==='UNKNOWN'||x.challenger.status.startsWith('UNKNOWN')).length};
}
export function screen(metrics,kind) {
  // Test fixtures and software CI must never certify financial performance.
  if(kind!=='HISTORICAL_DEVELOPMENT')return {verdict:'NOT_A_PERFORMANCE_TEST',gates:null};
  if(!metrics.panel||!metrics.paired)return {verdict:'BLOCKED_NO_PAIRED_MINUTE_EVIDENCE',gates:null};
  if(metrics.paired<30||metrics.symbols<10||metrics.capture3.denominator<20||metrics.capture5.denominator<20)
    return {verdict:'INCONCLUSIVE_INSUFFICIENT_SAMPLE',gates:null};
  const gates={minEntries:metrics.entered>=30,minSymbols:metrics.symbols>=10,
    capture3:metrics.capture3.ratio!==null&&metrics.capture3.ratio>=.9,
    capture5:metrics.capture5.ratio!==null&&metrics.capture5.ratio>=.9,throughput:metrics.throughput>=.8,
    meanD30:metrics.challengerD30.mean<=metrics.baselineD30.mean*.9,
    tailES95:metrics.challengerD30.es95<=metrics.baselineD30.es95,
    cheaper:num(metrics.priceImprovement.mean)&&metrics.priceImprovement.mean>=0,
    commonNet:num(metrics.commonPolicyNetDelta)&&metrics.commonPolicyNetDelta>=0};
  return {verdict:Object.values(gates).every(Boolean)?'FAST_FAIL_CONTINUE_NOT_VALIDATED':'FAST_FAIL_KILL_THIS_SPEC',gates};
}
export function frozenExitHandoff(anchor,record) {
  if (record.eventId!==anchor.eventId||record.symbol!==anchor.symbol||record.sessionDate!==anchor.sessionDate)
    throw Error('HANDOFF_IDENTITY_MISMATCH');
  if(record.challenger.status!=='REFERENCE_FILLED')return null;
  return {kind:'RESEARCH_ENTRY_REFERENCE',selectorEventId:anchor.eventId,symbol:anchor.symbol,
    sessionDate:anchor.sessionDate,direction:'LONG',entryTimestamp:new Date(record.challenger.at).toISOString(),
    entryPrice:record.challenger.price,entryPolicy:SPEC.id,entryPolicySHA:SPEC_SHA,
    sourceSelectionTimestamp:new Date(anchor.selectedAt).toISOString(),quantity:null,
    exitPolicyUnchanged:true,executionSemantics:'REFERENCE_ONLY_NOT_BROKER_EXECUTION',safety:SAFETY};
}
