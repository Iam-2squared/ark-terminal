#!/usr/bin/env node
/**
 * No.1.1 local OFFLINE/LOCKED inspection. NO broker/Excel/RSS interfaces.
 * 'probe' only observes read-only account freshness; never says trade-ready.
 * 'prepare-locked' requires an upstream Frozen decision envelope, never selects.
 */
import fs from 'node:fs';
import path from 'node:path';
import {makeLockedIntent,digest} from '../runtime/locked_intent.mjs';
import {No11SafetyLedger} from '../runtime/safety_ledger.mjs';
import {inspectLockedAccount,inspectReadOnlySnapshot} from '../runtime/account_gate.mjs';

function parse(argv) {
  const [mode,...rest]=argv;
  if(!['probe','initialize-ledger','prepare-locked'].includes(mode))throw Error('MODE_REQUIRED');
  if(rest.length%2!==0)throw Error('KEY_VALUE_ARGUMENTS_REQUIRED');
  const args={mode};
  for(let i=0;i<rest.length;i+=2) {
    const key=rest[i],val=rest[i+1];
    if(!key.startsWith('--')||key.slice(2) in args)throw Error('INVALID_OR_DUPLICATE_OPTION');
    args[key.slice(2)]=val;
  }
  return args;
}
function load(file,label) {
  if(!file||!path.isAbsolute(file))throw Error(label+'_ABSOLUTE_PATH_REQUIRED');
  const x=JSON.parse(fs.readFileSync(file,'utf8').replace(/^\uFEFF/,''));
  if(!x||typeof x!=='object'||Array.isArray(x))throw Error(label+'_OBJECT_REQUIRED');
  return x;
}
function output(file,value) {
  if(!file||!path.isAbsolute(file))throw Error('OUTPUT_ABSOLUTE_PATH_REQUIRED');
  if(fs.existsSync(file))throw Error('OUTPUT_ALREADY_EXISTS');
  fs.mkdirSync(path.dirname(file),{recursive:true,mode:0o700});
  fs.writeFileSync(file,JSON.stringify(value,null,2)+'\n',{flag:'wx',mode:0o600});
}
export function inspect(input) {
  if(input.mode==='initialize-ledger'){
    const x=new No11SafetyLedger(input.ledger);
    return {schemaId:'ARK_NO11_LEDGER_BOOTSTRAP_INSPECTION_V1',
      status:'RESTART_LOCKED_BY_DEFAULT',ledgerRevision:x.snapshot().revision,
      killSwitchLatched:x.snapshot().killSwitchLatched,executionAllowed:false,transmitted:false};
  }
  const snapshot=load(input.snapshot,'SNAPSHOT');
  const health=load(input.health,'RSS_HEALTH');
  if(input.mode==='probe'){
    return inspectReadOnlySnapshot({snapshot,health});
  }
  const sourceDecision=load(input.decision,'DECISION');
  const ownership=load(input.ownership,'OWNERSHIP');
  const mapping=load(input['symbol-map'],'SYMBOL_MAP');
  if(!Array.isArray(mapping.rows))throw Error('SYMBOL_MAP_ROWS_REQUIRED');
  const reservation=load(input.reservation,'RESERVATION');
  if(reservation.schemaId!=='ARK_NO11_EXPLICIT_SHADOW_CASH_RESERVATION_V1')throw Error('RESERVATION_SCHEMA_REQUIRED');
  const intent=makeLockedIntent(sourceDecision,{symbolMap:mapping.rows});
  const account=inspectLockedAccount({
    snapshot,health,ownership,lockedIntent:intent,
    maxOrderNotional:reservation.maxCashDebit
  });
  const safety=new No11SafetyLedger(input.ledger);
  const safetyGate=intent.side==='BUY'?safety.inspectBuy(intent.session):safety.inspectSell(intent.session);
  const blockers=[...new Set([...account.blockers,...safetyGate.blockers])];
  const core={
    schemaId:'ARK_NO11_LOCKED_PREFLIGHT_INSPECTION_V1',
    status:blockers.length?'BLOCKED':'LOCKED_CANDIDATE_ONLY',
    blockers,
    strategyFreezeCommit:intent.strategyFreezeCommit,
    sourceIntentId:intent.sourceIntentId,
    sourceEventId:intent.sourceEventId,
    lockedIntentSha256:intent.lockedIntentSha256,
    ownershipBaselineSha256:account.ownershipBaselineSha256,
    sourceFreshnessCertified:health.actualFeedTimestampCertified===true,
    sourceEvidenceMode:intent.evidenceMode,
    transmissionAllowed:false,executable:false,executionAllowed:false,
    brokerWriteAllowed:false,excelOrderWriteAllowed:false,
    rssOrderFunctionAllowed:false,transmitted:false,productionReady:false,
  };
  return {...core,inspectionSha256:digest(core)};
}
const isCLI = process.argv[1] && path.resolve(process.argv[1])===path.resolve(new URL(import.meta.url).pathname);
if(isCLI){
  try{
    const args=parse(process.argv.slice(2));
    const result=inspect(args);
    if(args.output)output(args.output,result);
    // Never emit private broker balances or position identities to stdout.
    console.log(result.status);
    if('blockers' in result)console.log('BLOCKERS='+result.blockers.join(';'));
    console.log('TRANSMITTED=FALSE');
    if(result.status==='BLOCKED')process.exitCode=2;
  }catch(e){console.error('NO11_LOCKED_PREFLIGHT_ERROR:'+e.message);process.exitCode=2;}
}
