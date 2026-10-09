/**
 * Private, persistent fail-closed No.1.1 SELL-fill latch and runtime-safety state.
 * No broker/Excel/RSS writes; SHA is an integrity checksum, not authentication.
 */
import fs from 'node:fs';
import path from 'node:path';
import {digest,LOCKED_FLAGS} from './locked_intent.mjs';

export const LEDGER_SCHEMA='ARK_NO11_PRIVATE_SAFETY_LEDGER_V1';
const error = message => {throw Error(message);};
const absTime = (s,label) => {
  if(typeof s!=='string'||!/(Z|[+-]\d{2}:\d{2})$/.test(s)||!Number.isFinite(Date.parse(s))) error(label);
  return Date.parse(s);
};
const sessionCheck = s => /^\d{4}-\d{2}-\d{2}$/.test(s??'') ? s : error('SESSION_INVALID');
const jstDate = ms => new Intl.DateTimeFormat('en-CA',{
  timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit'
}).format(new Date(ms)).replace(/\//g,'-');

function verifyPayload(value) {
  if(!value || value.schemaId!==LEDGER_SCHEMA) error('SAFETY_LEDGER_SCHEMA_INVALID');
  const {ledgerSha256,...core}=value;
  if(typeof ledgerSha256!=='string'||ledgerSha256!==digest(core)) error('SAFETY_LEDGER_HASH_MISMATCH');
  if(typeof core.killSwitchLatched!=='boolean'||typeof core.sellFillLatched!=='boolean') error('SAFETY_LEDGER_BOOLEAN_INVALID');
  if(!Array.isArray(core.faults)||!core.executions||typeof core.executions!=='object'||Array.isArray(core.executions)) error('SAFETY_LEDGER_STRUCTURE_INVALID');
  if(core.session!==null) sessionCheck(core.session);
  if(core.sellFillLatched && (!core.session || !core.firstSellFillAt)) error('SAFETY_LEDGER_LATCH_INCONSISTENT');
  for(const [k,v] of Object.entries(LOCKED_FLAGS)) if(core.safety?.[k]!==v) error('SAFETY_LEDGER_UNSAFE:'+k);
  return core;
}
function privateAtomicWrite(filename,body) {
  const dir=path.dirname(filename);
  fs.mkdirSync(dir,{recursive:true,mode:0o700});
  const temp=filename+'.tmp-'+process.pid+'-'+Math.random().toString(16).slice(2);
  try {
    const handle=fs.openSync(temp,'wx',0o600);
    try {fs.writeFileSync(handle,body,{encoding:'utf8'});fs.fsyncSync(handle);}
    finally {fs.closeSync(handle);}
    fs.renameSync(temp,filename);
  } finally {if(fs.existsSync(temp)) fs.unlinkSync(temp);}
}
export class No11SafetyLedger {
  constructor(filename) {
    if(typeof filename!=='string'||!path.isAbsolute(filename)) error('ABSOLUTE_PRIVATE_LEDGER_PATH_REQUIRED');
    this.filename=filename;
    this.corrupt=false;
    if(fs.existsSync(filename)) {
      try {
        if(!fs.lstatSync(filename).isFile()||fs.lstatSync(filename).isSymbolicLink()) error('UNSAFE_LEDGER_FILE');
        this.state=verifyPayload(JSON.parse(fs.readFileSync(filename,'utf8')));
      } catch(err) {
        this.corrupt=true;
        this.state=null;
      }
    } else {
      this.state={
        schemaId:LEDGER_SCHEMA,session:null,killSwitchLatched:true,
        faults:['RESTART_STATE_UNVERIFIED'],sellFillLatched:false,firstSellFillAt:null,
        executions:{},lastVerifiedReadAt:null,revision:0,safety:LOCKED_FLAGS
      };
      this._persist();
    }
  }
  _requireValid() {if(this.corrupt||!this.state) error('SAFETY_LEDGER_CORRUPT_FAIL_CLOSED');}
  _persist() {
    this._requireValid();
    this.state.revision++;
    privateAtomicWrite(this.filename,JSON.stringify({...this.state,ledgerSha256:digest(this.state)},null,2)+'\n');
  }
  snapshot() {
    this._requireValid();
    return structuredClone({...this.state,ledgerSha256:digest(this.state)});
  }
  latchFault(reason) {
    this._requireValid();
    if(typeof reason!=='string'||!reason.trim()) error('FAULT_REASON_REQUIRED');
    this.state.killSwitchLatched=true;
    if(!this.state.faults.includes(reason)) this.state.faults.push(reason);
    this._persist();
    return this.snapshot();
  }
  /** Start/reset only with a positively verified *new* JPX session and account snapshot. */
  verifyTradingSession({session,calendarVerified,accountReconciled,sourceFresh,readAt}) {
    this._requireValid();
    const day=sessionCheck(session), ms=absTime(readAt,'SESSION_READ_AT_INVALID');
    if(jstDate(ms)!==day) error('SESSION_CLOCK_MISMATCH');
    if(calendarVerified!==true||accountReconciled!==true||sourceFresh!==true) {
      return this.latchFault('SESSION_VERIFICATION_FAILED');
    }
    if(this.state.session && day<this.state.session) return this.latchFault('SESSION_REGRESSION');
    if(this.state.lastVerifiedReadAt && ms<Date.parse(this.state.lastVerifiedReadAt)) {
      return this.latchFault('SOURCE_CLOCK_REGRESSION');
    }
    if(this.state.session!==day) {
      this.state.session=day;
      this.state.sellFillLatched=false;
      this.state.firstSellFillAt=null;
    }
    this.state.lastVerifiedReadAt=new Date(ms).toISOString();
    this._persist();
    return this.snapshot();
  }
  /** A normal RSS poll may redeliver the same execution; deduplicate by ID. */
  recordBrokerSellFill(fill) {
    this._requireValid();
    if(!fill||fill.source!=='MARKETSPEED_II_RSS'||fill.brokerReconciled!==true||fill.verifiedExecution===false) {
      return this.latchFault('UNVERIFIED_BROKER_FILL');
    }
    const id=fill.brokerExecutionId;
    if(typeof id!=='string'||!id.trim()||typeof fill.orderId!=='string'||!fill.orderId.trim()) {
      return this.latchFault('BROKER_EXECUTION_ID_UNKNOWN');
    }
    if(fill.side!=='SELL'||!Number.isSafeInteger(fill.quantity)||fill.quantity<=0) {
      return this.latchFault('BROKER_SELL_FILL_INVALID');
    }
    const at=absTime(fill.executedAt,'BROKER_FILL_TIME_INVALID');
    const day=sessionCheck(fill.session);
    if(jstDate(at)!==day||day!==this.state.session) return this.latchFault('BROKER_FILL_SESSION_MISMATCH');
    const fingerprint=digest({id,orderId:fill.orderId,side:fill.side,quantity:fill.quantity,executedAt:fill.executedAt,session:day});
    const previous=this.state.executions[id];
    if(previous) {
      if(previous!==fingerprint) return this.latchFault('BROKER_EXECUTION_ID_CONFLICT');
      return this.snapshot();
    }
    this.state.executions[id]=fingerprint;
    if(!this.state.sellFillLatched) {
      this.state.sellFillLatched=true;
      this.state.firstSellFillAt=new Date(at).toISOString();
    } else if(at < Date.parse(this.state.firstSellFillAt)) {
      // An earlier, previously unseen fill indicates out-of-order account state.
      return this.latchFault('LATE_EARLIER_SELL_FILL');
    }
    this._persist();
    return this.snapshot();
  }
  /** No approval here can ever turn on broker or Excel transmission. */
  explicitSafetyReset({humanApproved,healthyAccountVerified,sourceFresh,readAt}) {
    this._requireValid();
    absTime(readAt,'RESET_READ_AT_INVALID');
    if(humanApproved!==true||healthyAccountVerified!==true||sourceFresh!==true||!this.state.session) {
      return this.latchFault('RESET_REJECTED_NO_HEALTH_PROOF');
    }
    this.state.killSwitchLatched=false;
    this.state.faults=[];
    this._persist();
    return this.snapshot();
  }
  inspectBuy(session) {
    this._requireValid();
    const reasons=[];
    if(sessionCheck(session)!==this.state.session) reasons.push('UNVERIFIED_TRADING_SESSION');
    if(this.state.killSwitchLatched||this.state.faults.length) reasons.push('KILL_SWITCH_OR_RUNTIME_FAULT');
    if(this.state.sellFillLatched) reasons.push('NO11_AFTER_FIRST_SELL_FILL_BUY_PROHIBITED');
    return Object.freeze({
      status:reasons.length?'BLOCKED':'LOCKED_ONLY_CANDIDATE',
      blockers:reasons,executionAllowed:false,transmitted:false
    });
  }
}
