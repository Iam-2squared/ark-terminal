import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {randomUUID,createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {EvidenceLog,instant,jstDate,exposedDate} from '../lib/phase57-offline-parity.mjs';
import {applyExternalCashFlow,classifyFreshness} from '../lib/phase57-operational-robustness.mjs';
import {VERSION,FREEZE,SAFETY,ACTIVE,finite,positive,quantity,text,timestamp,checkHash,fingerprint,orderIntent,validateLimits,portfolio,accountReconciliation,preflight,riskGate} from './contract.mjs';
export const STATES=Object.freeze(['CREATED','VALIDATED','BLOCKED','READY','SUBMISSION_REQUESTED','SUBMITTED','ACCEPTED','PARTIALLY_FILLED','FILLED','REJECTED','CANCEL_REQUESTED','CANCELLED','UNKNOWN','RECONCILIATION_REQUIRED']);
const transitions={CREATED:['VALIDATED','BLOCKED'],VALIDATED:['READY','BLOCKED'],READY:['SUBMISSION_REQUESTED','BLOCKED'],BLOCKED:[],SUBMISSION_REQUESTED:['SUBMITTED','REJECTED','UNKNOWN'],SUBMITTED:['ACCEPTED','REJECTED','UNKNOWN'],ACCEPTED:['PARTIALLY_FILLED','FILLED','CANCEL_REQUESTED','UNKNOWN'],PARTIALLY_FILLED:['PARTIALLY_FILLED','FILLED','CANCEL_REQUESTED','UNKNOWN'],CANCEL_REQUESTED:['PARTIALLY_FILLED','FILLED','CANCELLED','UNKNOWN'],UNKNOWN:['RECONCILIATION_REQUIRED'],RECONCILIATION_REQUIRED:['ACCEPTED','PARTIALLY_FILLED','FILLED','CANCELLED','REJECTED'],FILLED:[],CANCELLED:[],REJECTED:[]};
function move(order,status){assert.ok(transitions[order.status]?.includes(status),`INVALID_TRANSITION:${order.status}->${status}`);order.status=status;}
const locked=()=>({blocked:true,reason:'TRANSMISSION_LOCKED',transmitted:false});
export class TransmissionLockedAdapter {
  validateConnection(){return {available:false,status:'TRANSMISSION_LOCKED'};}
  getAccountSnapshot(){return {status:'UNKNOWN'};} getPositions(){return {status:'UNKNOWN'};}
  getOpenOrders(){return {status:'UNKNOWN'};} getOrderStatus(){return {status:'UNKNOWN'};}
  submitOrder(){return locked();} cancelOrder(){return locked();}
}
// Fixture response factory only. No network/Excel objects, environment unlocks or injected callbacks.
export class MockExecutionAdapter {
  validateConnection(){return {available:true,fixtureOnly:true};}
  submitOrder(intent){return {fixtureOnly:true,orderIntentId:intent.orderIntentId,status:'SUBMITTED',transmitted:false};}
  cancelOrder(intent){return {fixtureOnly:true,orderIntentId:intent.orderIntentId,status:'CANCELLED',transmitted:false};}
  getAccountSnapshot(snapshot){return {fixtureOnly:true,snapshot:structuredClone(snapshot)};}
  getPositions(){return {status:'UNKNOWN',fixtureOnly:true};} getOpenOrders(){return {status:'UNKNOWN',fixtureOnly:true};} getOrderStatus(){return {status:'UNKNOWN',fixtureOnly:true};}
}
function initialize(config){
  assert.equal(config.freezeSha256,FREEZE,'FREEZE_MISMATCH');
  assert.ok(['SYNTHETIC_FIXTURE','TRANSMISSION_LOCKED'].includes(config.mode),'UNSUPPORTED_MODE');
  assert.match(config.repoHead,/^[a-f0-9]{40}$/);checkHash(config.fixtureHash);
  const sessionDate=exposedDate(config.sessionDate);
  assert.ok(Array.isArray(config.symbols)&&config.symbols.length&&new Set(config.symbols).size===config.symbols.length,'SYMBOL_UNIVERSE_REQUIRED');
  for(const s of config.symbols)assert.match(s,/^[0-9A-Z]{4}\.T$/);
  const state={version:VERSION,sessionDate,limits:validateLimits(config.limits),cashJpy:positive(config.initialCashJpy),initialEquity:0,
    positions:{},orders:{},decisionIds:{},fillIds:{},cashFlowIds:{},realizedPnl:0,externalCashFlowJpy:0,
    deposits:0,withdrawals:0,manualAdjustments:0,context:null,reconciliation:'UNKNOWN',mode:'DISARMED',emergency:false,lastAt:timestamp(config.startedAt),sessionStartPnl:0};
  assert.equal(jstDate(state.lastAt),sessionDate);
  for(const p of config.positions??[]){
    assert.ok(config.symbols.includes(p.symbol)&&!Object.hasOwn(state.positions,p.symbol),'UNKNOWN_OR_DUPLICATE_POSITION');
    assert.ok(['LONG','SHORT'].includes(p.direction),'UNKNOWN_DIRECTION');quantity(p.quantity);positive(p.averagePrice);
    state.positions[p.symbol]={symbol:p.symbol,direction:p.direction,quantity:p.quantity,averagePrice:p.averagePrice,markPrice:p.averagePrice,collateral:p.direction==='SHORT'?p.averagePrice*p.quantity:0,proceeds:p.direction==='SHORT'?p.averagePrice*p.quantity:0};
  }
  state.initialEquity=portfolio(state).equityJpy;state.sessionStartEquity=state.initialEquity;return state;
}
function invariants(state){
  assert.ok(finite(state.cashJpy)&&state.cashJpy>=0,'NEGATIVE_CASH');
  for(const p of Object.values(state.positions)){assert.ok(Number.isSafeInteger(p.quantity)&&p.quantity>0,'INVALID_POSITION_QUANTITY');positive(p.markPrice);positive(p.averagePrice);}
  const p=portfolio(state);
  assert.ok(Math.abs(p.equityJpy-(state.initialEquity+state.externalCashFlowJpy+state.realizedPnl+p.unrealizedPnl))<0.00001,'EQUITY_CONSERVATION');
  for(const o of Object.values(state.orders))assert.ok(o.filledQuantity>=0&&o.filledQuantity<=o.intent.quantity,'OVERFILL');
}
function invalidate(state){state.context=null;state.reconciliation='UNKNOWN';}
function fill(state,order,event){
  assert.ok(['ACCEPTED','PARTIALLY_FILLED','CANCEL_REQUESTED'].includes(order.status),'FILL_STATE_INVALID');
  text(event.fillId);assert.ok(!Object.hasOwn(state.fillIds,event.fillId),'DUPLICATE_FILL');
  const q=event.quantity;assert.ok(Number.isSafeInteger(q)&&q>0&&q+order.filledQuantity<=order.intent.quantity,'OVERFILL_OR_INVALID_FILL');
  const price=positive(event.price);assert.ok(finite(event.feeJpy)&&event.feeJpy>=0,'INVALID_FEE');
  const i=order.intent;
  if(i.orderType==='LIMIT')assert.ok(i.side==='BUY'?price<=i.limitPrice:price>=i.limitPrice,'LIMIT_FILL_VIOLATION');
  let p=state.positions[i.symbol];const notional=q*price;
  if(i.positionEffect==='OPEN'){
    assert.ok(!p||p.direction===i.direction,'OPPOSITE_POSITION');
    state.cashJpy-=notional+event.feeJpy;
    if(!p)p=state.positions[i.symbol]={symbol:i.symbol,direction:i.direction,quantity:0,averagePrice:0,markPrice:price,collateral:0,proceeds:0};
    p.averagePrice=(p.quantity*p.averagePrice+notional)/(p.quantity+q);p.quantity+=q;p.markPrice=price;
    if(i.direction==='SHORT'){p.collateral+=notional;p.proceeds+=notional;}
  }else{
    assert.ok(p&&p.direction===i.direction&&q<=p.quantity,'CLOSE_POSITION_UNKNOWN_OR_EXCEEDED');
    const pnl=(price-p.averagePrice)*q*(p.direction==='LONG'?1:-1);state.realizedPnl+=pnl;
    if(p.direction==='LONG')state.cashJpy+=notional-event.feeJpy;
    else {const fraction=q/p.quantity,c=p.collateral*fraction,s=p.proceeds*fraction;state.cashJpy+=c+s-notional-event.feeJpy;p.collateral-=c;p.proceeds-=s;}
    p.quantity-=q;p.markPrice=price;if(!p.quantity)delete state.positions[i.symbol];
  }
  state.realizedPnl-=event.feeJpy;
  order.fillNotional+=notional;order.filledQuantity+=q;order.averageFillPrice=order.fillNotional/order.filledQuantity;
  state.fillIds[event.fillId]=fingerprint(event);move(order,order.filledQuantity===i.quantity?'FILLED':'PARTIALLY_FILLED');
  invalidate(state);
}
function reduce(state,event,config){
  const next=structuredClone(state),at=timestamp(event.at);assert.ok(instant(at)>=instant(state.lastAt),'NONMONOTONIC_TIMESTAMP');
  assert.equal(jstDate(at),state.sessionDate,'SESSION_BOUNDARY_REQUIRES_NEW_RUN');next.lastAt=at;
  const fixture=config.mode==='SYNTHETIC_FIXTURE';let output={};
  const get=()=>{assert.ok(Object.hasOwn(next.orders,event.orderIntentId),'UNKNOWN_ORDER');return next.orders[event.orderIntentId];};
  switch(event.kind){
    case 'CONTEXT': {
      checkHash(event.evidenceHash);assert.ok(instant(event.context.accountAt)<=instant(at)&&instant(event.context.feedAt)<=instant(at),'NONCAUSAL_CONTEXT');
      next.context=structuredClone(event.context);const r=accountReconciliation(next,event.context.account);next.reconciliation=r.status;output=r;break;
    }
    case 'CREATE': {
      assert.ok(!next.emergency,'EMERGENCY_STOP');
      const i=orderIntent(event.decision,{symbols:config.symbols,position:next.positions[event.decision.symbol]});
      assert.equal(timestamp(event.decision.createdAt),at,'CREATED_TIMESTAMP_MISMATCH');
      const decisionKey=fingerprint({decisionId:i.decisionId,sessionDate:i.sessionDate,strategyVersion:i.strategyVersion});
      if(Object.hasOwn(next.decisionIds,decisionKey)){
        assert.equal(next.decisionIds[decisionKey],i.orderIntentId,'CONFLICTING_DECISION');output={duplicate:true,orderIntentId:i.orderIntentId};break;
      }
      next.decisionIds[decisionKey]=i.orderIntentId;next.orders[i.orderIntentId]={intent:i,status:'CREATED',filledQuantity:0,fillNotional:0,averageFillPrice:null,submissionCount:0,blockReasons:[]};output={orderIntentId:i.orderIntentId};break;
    }
    case 'VALIDATE':{
      const o=get();move(o,'VALIDATED');const reasons=riskGate(next,o.intent,at);o.blockReasons=reasons;move(o,reasons.length?'BLOCKED':'READY');output={status:o.status,reasons};break;
    }
    case 'REQUEST':{
      const o=get();assert.equal(o.status,'READY','ORDER_NOT_READY');const reasons=riskGate(next,o.intent,at);
      if(!fixture)reasons.push('TRANSMISSION_LOCKED');
      if(reasons.length){move(o,'BLOCKED');o.blockReasons=reasons;output={...locked(),reasons};break;}
      assert.equal(o.submissionCount,0,'NO_AUTOMATIC_RESUBMISSION');move(o,'SUBMISSION_REQUESTED');o.submissionCount++;output={status:o.status,transmitted:false};break;
    }
    case 'ADAPTER_RESPONSE':{
      assert.ok(fixture,'TRANSMISSION_LOCKED');const o=get();assert.equal(o.status,'SUBMISSION_REQUESTED');
      assert.ok(['SUBMITTED','REJECTED','UNKNOWN'].includes(event.status),'INVALID_RESPONSE');move(o,event.status);break;
    }
    case 'ACCEPT':assert.ok(fixture,'TRANSMISSION_LOCKED');move(get(),'ACCEPTED');break;
    case 'FILL':assert.ok(fixture,'TRANSMISSION_LOCKED');fill(next,get(),event);break;
    case 'REJECT':assert.ok(fixture,'TRANSMISSION_LOCKED');move(get(),'REJECTED');break;
    case 'CANCEL_REQUEST':{
      const o=get();assert.ok(!next.emergency,'EMERGENCY_STOP');
      if(!fixture){output=locked();break;}move(o,'CANCEL_REQUESTED');break;
    }
    case 'CANCELLED':assert.ok(fixture,'TRANSMISSION_LOCKED');move(get(),'CANCELLED');invalidate(next);break;
    case 'UNKNOWN':move(get(),'UNKNOWN');invalidate(next);next.mode='DISARMED';break;
    case 'RECONCILIATION_REQUIRED':move(get(),'RECONCILIATION_REQUIRED');invalidate(next);break;
    case 'RESOLVE_ORDER':{
      assert.ok(fixture,'TRANSMISSION_LOCKED');text(event.operator);checkHash(event.evidenceHash);
      const o=get();assert.equal(o.status,'RECONCILIATION_REQUIRED');assert.equal(next.reconciliation,'MATCH','ACCOUNT_RECONCILIATION_REQUIRED');
      assert.ok(instant(at)-instant(next.context.accountAt)<=next.limits.maxAccountAgeMs,'STALE_ACCOUNT_RESOLUTION');
      assert.equal(event.filledQuantity,o.filledQuantity,'MISSING_FILL_HISTORY');
      assert.ok(['ACCEPTED','PARTIALLY_FILLED','FILLED','CANCELLED','REJECTED'].includes(event.status),'INVALID_RESOLUTION');
      if(event.status==='FILLED')assert.equal(o.filledQuantity,o.intent.quantity);
      if(event.status==='ACCEPTED'||event.status==='REJECTED')assert.equal(o.filledQuantity,0);
      if(event.status==='PARTIALLY_FILLED')assert.ok(o.filledQuantity>0&&o.filledQuantity<o.intent.quantity);
      move(o,event.status);invalidate(next);break;
    }
    case 'MODE':{
      text(event.operator);assert.ok(['DISARMED','SHADOW','ARM_REQUESTED','ARMED','EXIT_ONLY'].includes(event.mode),'INVALID_MODE');
      assert.ok(!next.emergency,'EMERGENCY_STOP');
      if(event.mode==='ARMED'){
        assert.equal(next.mode,'ARM_REQUESTED','MANUAL_ARM_REQUEST_REQUIRED');const reasons=preflight(next,at,{fixture});
        const p=portfolio(next),loss=Math.max(0,-(p.realizedPnl+p.unrealizedPnl-next.sessionStartPnl));
        if(loss>=next.limits.maxDailyLossJpy||loss/next.sessionStartEquity*100>=next.limits.maxDailyLossPct)reasons.push('DAILY_LOSS_LIMIT');
        next.mode=reasons.length?'DISARMED':'ARMED';output={reasons};
      }else next.mode=event.mode;break;
    }
    case 'EMERGENCY_STOP':
      next.emergency=true;next.mode='EMERGENCY_STOP';
      for(const o of Object.values(next.orders))if(['CREATED','VALIDATED','READY'].includes(o.status)){move(o,'BLOCKED');o.blockReasons=['EMERGENCY_STOP'];}
      break;
    case 'CLEAR_EMERGENCY':text(event.operator);checkHash(event.evidenceHash);assert.equal(event.confirm,true,'MANUAL_CONFIRM_REQUIRED');next.emergency=false;next.mode='DISARMED';invalidate(next);break;
    case 'DISCONNECT':next.mode='DISARMED';invalidate(next);break;
    case 'CASH_FLOW':{
      assert.ok(fixture,'TRANSMISSION_LOCKED');text(event.cashFlowId);assert.ok(!Object.hasOwn(next.cashFlowIds,event.cashFlowId),'DUPLICATE_CASH_FLOW');
      const p=portfolio(next),r=applyExternalCashFlow({cashJpy:next.cashJpy,equityJpy:p.equityJpy,tradingPnlJpy:next.realizedPnl,externalCashFlowJpy:next.externalCashFlowJpy},event.flow);
      next.cashJpy=r.cashJpy;next.externalCashFlowJpy=r.externalCashFlowJpy;next.cashFlowIds[event.cashFlowId]=fingerprint(event);
      const key={DEPOSIT:'deposits',WITHDRAWAL:'withdrawals',MANUAL_ADJUSTMENT:'manualAdjustments'}[event.flow.type];next[key]+=event.flow.amountJpy;invalidate(next);break;
    }
    case 'MARK':assert.ok(fixture,'TRANSMISSION_LOCKED');assert.ok(next.positions[event.symbol],'UNKNOWN_POSITION');next.positions[event.symbol].markPrice=positive(event.price);invalidate(next);break;
    case 'RECOVERY':
      next.mode=next.emergency?'EMERGENCY_STOP':'DISARMED';invalidate(next);
      for(const o of Object.values(next.orders))if(['SUBMISSION_REQUESTED','SUBMITTED','ACCEPTED','PARTIALLY_FILLED','CANCEL_REQUESTED'].includes(o.status))move(o,'UNKNOWN');
      break;
    default:throw Error('UNKNOWN_EVENT');
  }
  invariants(next);return {state:next,output};
}
export class ExecutionRuntime {
  #log;#state;#seen=new Map();#config;#failed=false;
  constructor(directory,config){
    this.#config=structuredClone(config);this.#state=initialize(config);
    const file=path.join(directory,'execution.jsonl');this.#log=new EvidenceLog(file);
    try{
      const rows=fs.existsSync(file)?fs.readFileSync(file,'utf8').trim().split('\n').filter(Boolean).map(JSON.parse):[];
      if(!rows.length)this.#log.append('INIT',{config:this.#config,version:VERSION,safety:SAFETY});
      else{
        assert.equal(rows[0].kind,'INIT');assert.deepEqual(rows[0].payload,{config:this.#config,version:VERSION,safety:SAFETY},'JOURNAL_IDENTITY_CHANGED');
        for(const row of rows.slice(1)){
          assert.ok(['COMMIT','REJECT_EVENT'].includes(row.kind),'UNKNOWN_JOURNAL_KIND');const {event}=row.payload;
          if(row.kind==='REJECT_EVENT'){assert.equal(row.payload.failClosed,true);invalidate(this.#state);this.#state.mode=this.#state.emergency?'EMERGENCY_STOP':'DISARMED';continue;}
          assert.ok(!this.#seen.has(event.eventId),'DUPLICATE_JOURNAL_EVENT');
          const r=reduce(this.#state,event,this.#config);assert.equal(fingerprint(r),row.payload.resultHash,'REPLAY_MISMATCH');
          this.#state=r.state;this.#seen.set(event.eventId,{hash:fingerprint(event),output:r.output});
        }
        this.process({eventId:`recovery-${this.#log.sequence}`,kind:'RECOVERY',at:this.#state.lastAt});
      }
    }catch(e){this.#log.close();throw e;}
  }
  process(event){
    assert.ok(!this.#failed,'JOURNAL_FAILED_RESTART_REQUIRED');event=structuredClone(event);text(event.eventId);
    const seen=this.#seen.get(event.eventId);
    if(seen){assert.equal(seen.hash,fingerprint(event),'CONFLICTING_EVENT_ID');return {duplicate:true,...structuredClone(seen.output)};}
    let r;
    try{r=reduce(this.#state,event,this.#config);}catch(error){
      try{this.#log.append('REJECT_EVENT',{event,reason:error.message,failClosed:true});invalidate(this.#state);this.#state.mode=this.#state.emergency?'EMERGENCY_STOP':'DISARMED';}catch{this.#failed=true;}throw error;
    }
    try{this.#log.append('COMMIT',{event,resultHash:fingerprint(r),output:r.output});}catch(error){this.#failed=true;throw error;}
    this.#state=r.state;this.#seen.set(event.eventId,{hash:fingerprint(event),output:r.output});return structuredClone(r.output);
  }
  // Production entry point cannot dispatch a supplied adapter; the lock is unconditional.
  submitOrder(){return new TransmissionLockedAdapter().submitOrder();}
  cancelOrder(){return new TransmissionLockedAdapter().cancelOrder();}
  status(now){
    const s=this.snapshot();let freshness='UNKNOWN';
    if(now&&s.context?.feedAt){try{freshness=classifyFreshness({sourceTimestamp:s.context.feedAt,observedAt:now,maxAgeMs:s.limits.maxFeedAgeMs}).status;}catch{freshness='UNKNOWN';}}
    return {schemaId:'ARK_EXECUTION_STATUS_V1',msii:s.context?.msiiConnected===true?'CONNECTED':'UNKNOWN',rss:freshness,
      excel:s.context?.excelConnected===true?'CONNECTED':'UNKNOWN',realtimeEngine:s.context?.engineReady===true?'READY':'BLOCKED',
      finalization:s.fixtureOnly&&s.context?.finalizationPassed===true?'FIXTURE_PASS':'UNVERIFIED',account:s.reconciliation,
      execution:s.mode,emergencyStop:s.emergency?'ON':'OFF',transmission:'LOCKED',fixtureOnly:s.fixtureOnly,safety:SAFETY};
  }
  snapshot(){return structuredClone({...this.#state,portfolio:portfolio(this.#state),safety:SAFETY,transmission:'LOCKED',fixtureOnly:this.#config.mode==='SYNTHETIC_FIXTURE',journalHealthy:!this.#failed});}
  close(){this.#log.close();this.#failed=true;}
}


// No automatic lock removal. Operator must stop every writer and bind the exact
// unchanged journal. Original lock and a recovery audit are preserved, not deleted.
export function recoverStoppedWriter(directory,config,{operator,confirmAllWritersStopped,expectedJournalSha256}){
  text(operator);assert.equal(confirmAllWritersStopped,true,'MANUAL_STOP_CONFIRMATION_REQUIRED');checkHash(expectedJournalSha256);
  const file=path.join(directory,'execution.jsonl'),lock=file+'.lock';
  const bytes=fs.readFileSync(file),actual=createHash('sha256').update(bytes).digest('hex');
  assert.equal(actual,expectedJournalSha256,'RECOVERY_JOURNAL_CHANGED');assert.ok(fs.existsSync(lock),'NO_ABANDONED_LOCK');
  const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'ark-recovery-verify-'));
  try{fs.writeFileSync(path.join(temporary,'execution.jsonl'),bytes);const verify=new ExecutionRuntime(temporary,config);verify.close();}
  finally{fs.rmSync(temporary,{recursive:true,force:true});}
  assert.equal(createHash('sha256').update(fs.readFileSync(file)).digest('hex'),actual,'RECOVERY_JOURNAL_CHANGED');
  const token=randomUUID(),archive=lock+'.quarantine-'+token;
  fs.writeFileSync(path.join(directory,'manual-recovery-'+token+'.json'),JSON.stringify({operator,confirmAllWritersStopped,expectedJournalSha256,action:'RELEASE_ABANDONED_WRITER_LOCK',transmission:'LOCKED'})+'\n',{flag:'wx'});
  fs.renameSync(lock,archive);return {archive,journalSha256:actual};
}
