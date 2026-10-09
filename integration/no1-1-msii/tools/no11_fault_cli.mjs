#!/usr/bin/env node
/**
 * Windows read-only capture fault reporter. Never resets Kill Switch and never
 * performs any broker/Excel operation. All state remains local to the PC.
 */
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {No11SafetyLedger} from '../runtime/safety_ledger.mjs';
const ALLOWED=new Set([
  'EXCEL_COM_RETRY_EXHAUSTED','RSS_ADDIN_NOT_LOADED',
  'ACCOUNT_SOURCE_UNAVAILABLE','READ_ONLY_CAPTURE_FAILED',
  'ACCOUNT_SNAPSHOT_STALE','RESTART_STATE_UNVERIFIED',
  'RSS_DISCONNECTED','BROKER_RECONCILIATION_UNKNOWN'
]);
export function faultStatus({mode,ledger,reason}={}){
  if(typeof ledger!=='string'||!path.isAbsolute(ledger))throw Error('ABSOLUTE_PRIVATE_LEDGER_PATH_REQUIRED');
  const runtime=new No11SafetyLedger(ledger);
  if(mode==='status'){
    const s=runtime.snapshot();return {
      schemaId:'ARK_NO11_PRIVATE_RUNTIME_SAFETY_REPORT_V1',
      killSwitchLatched:s.killSwitchLatched,
      faults:s.faults,session:s.session,
      sellFillLatched:s.sellFillLatched,
      executionAllowed:false,transmitted:false
    };
  }
  if(mode!=='latch'||!ALLOWED.has(reason))throw Error('UNSUPPORTED_FAULT_OR_MODE');
  const s=runtime.latchFault(reason);
  return {schemaId:'ARK_NO11_PRIVATE_RUNTIME_SAFETY_REPORT_V1',
    killSwitchLatched:s.killSwitchLatched,faults:s.faults,
    session:s.session,sellFillLatched:s.sellFillLatched,
    executionAllowed:false,transmitted:false};
}
if(process.argv[1]&&path.resolve(process.argv[1])===path.resolve(fileURLToPath(import.meta.url))){
  try{
    const argv=process.argv.slice(2);
    if(argv.length<3||argv[1]!=='--ledger')throw Error('USAGE_MODE_LEDGER_PATH_OPTIONAL_REASON');
    const result=faultStatus({mode:argv[0],ledger:argv[2],
      reason:argv[3]==='--reason'?argv[4]:undefined});
    console.log(result.killSwitchLatched?'KILL_SWITCH_LATCHED':'KILL_SWITCH_STATE_RECORDED_NOT_LIVE_READY');
    console.log('TRANSMITTED=FALSE');
  }catch(e){console.error('NO11_SAFETY_STATE_ERROR:'+e.message);process.exitCode=2;}
}
