import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {validateCashUpstreamAction} from './phase57_cash_upstream_action.mjs';

export const OWNERSHIP_SCHEMA='ARK_CASH_OWNERSHIP_BASELINE_V1';
const canonical=value=>Array.isArray(value)?value.map(canonical):value&&typeof value==='object'?Object.fromEntries(Object.keys(value).sort().map(k=>[k,canonical(value[k])])):value;
const sha256=value=>createHash('sha256').update(JSON.stringify(canonical(value))).digest('hex');
const symbol=v=>String(v??'').trim().toUpperCase();

function validatePositions(rows,label,{managed=false}={}){
  if(!Array.isArray(rows))throw Error(`${label}_POSITIONS_ARRAY_REQUIRED`);
  const seen=new Set();
  return rows.map(row=>{
    const s=symbol(row?.symbol); const q=Number(row?.quantity);
    if(!/^[0-9A-Z]{4}(?:\.T)?$/.test(s))throw Error(`${label}_POSITION_SYMBOL_INVALID`);
    const n=s.endsWith('.T')?s:`${s}.T`;
    if(seen.has(n))throw Error(`${label}_POSITION_DUPLICATE`); seen.add(n);
    if(!Number.isFinite(q)||q<=0)throw Error(`${label}_POSITION_QUANTITY_INVALID`);
    if(managed&&(!Number.isInteger(q)||q%100!==0))throw Error('ARK_MANAGED_POSITION_LOT_INVALID');
    return Object.freeze({symbol:n,quantity:q});
  });
}

export function validateOwnershipBaseline(value){
  if(!value||value.schemaId!==OWNERSHIP_SCHEMA)throw Error('OWNERSHIP_BASELINE_SCHEMA_REQUIRED');
  if(value.frozen!==true)throw Error('OWNERSHIP_BASELINE_MUST_BE_FROZEN');
  const {baselineSha256,...core}=value;
  if(!/^[a-f0-9]{64}$/i.test(String(baselineSha256??''))||sha256(core)!==baselineSha256)throw Error('OWNERSHIP_BASELINE_HASH_MISMATCH');
  const externalPositions=validatePositions(value.externalPositions,'EXTERNAL');
  const arkManagedPositions=validatePositions(value.arkManagedPositions,'ARK_MANAGED',{managed:true});
  const ext=new Set(externalPositions.map(x=>x.symbol));
  if(arkManagedPositions.some(x=>ext.has(x.symbol)))throw Error('POSITION_OWNERSHIP_OVERLAP');
  return Object.freeze({...value,externalPositions:Object.freeze(externalPositions),arkManagedPositions:Object.freeze(arkManagedPositions)});
}

export function freezeOwnershipBaseline({externalPositions=[],arkManagedPositions=[],capturedAt,source='LOCAL_PRIVATE_BASELINE'}={}){
  if(!Number.isFinite(Date.parse(String(capturedAt??''))))throw Error('OWNERSHIP_BASELINE_CAPTURED_AT_REQUIRED');
  const core={schemaId:OWNERSHIP_SCHEMA,capturedAt:new Date(capturedAt).toISOString(),source:String(source),frozen:true,externalPositions:validatePositions(externalPositions,'EXTERNAL'),arkManagedPositions:validatePositions(arkManagedPositions,'ARK_MANAGED',{managed:true})};
  const manifest={...core,baselineSha256:sha256(core)};
  return validateOwnershipBaseline(manifest);
}

export function buildLockedRequestFromAction(action,{snapshotPath,ownershipBaseline}={}){
  const upstream=validateCashUpstreamAction(action);
  const ownership=validateOwnershipBaseline(ownershipBaseline);
  const target=String(snapshotPath??'').trim(); if(!target)throw Error('SNAPSHOT_PATH_REQUIRED');
  return Object.freeze({
    schemaId:'ARK_CASH_LOCKED_REQUEST_V1', snapshotPath:target,
    intent:Object.freeze({symbol:upstream.symbol,direction:'LONG',side:upstream.side,positionEffect:upstream.positionEffect,quantity:upstream.quantity,orderType:upstream.orderType,limitPrice:upstream.limitPrice,timeInForce:upstream.timeInForce}),
    externalPositions:ownership.externalPositions,
    arkManagedPositions:ownership.arkManagedPositions,
    estimatedNotional:upstream.estimatedNotional,
    ownershipBaselineSha256:ownership.baselineSha256,
    upstreamLineage:Object.freeze({sourceActionSha256:upstream.actionSha256,sourceCashExecutionIntentSha256:upstream.sourceCashExecutionIntentSha256,sourceIntentSha256:upstream.lineage.sourceIntentSha256,sourceIntentId:upstream.lineage.sourceIntentId,strategyId:upstream.lineage.strategyId}),
    inspectionOnly:true,
  });
}

function args(argv){const out={};for(let i=2;i<argv.length;i+=2){if(!argv[i]?.startsWith('--')||argv[i+1]===undefined)throw Error('USAGE');out[argv[i].slice(2)]=argv[i+1];}return out;}
const isMain=process.argv[1]&&fileURLToPath(import.meta.url)===path.resolve(process.argv[1]);
if(isMain){try{const a=args(process.argv);if(!a.action||!a.ownership||!a.snapshot||!a.output)throw Error('USAGE');const action=JSON.parse(fs.readFileSync(a.action,'utf8'));const ownership=JSON.parse(fs.readFileSync(a.ownership,'utf8'));const request=buildLockedRequestFromAction(action,{snapshotPath:a.snapshot,ownershipBaseline:ownership});if(fs.existsSync(a.output))throw Error('OUTPUT_ALREADY_EXISTS');fs.writeFileSync(a.output,JSON.stringify(request,null,2));console.log('CASH_LOCKED_UPSTREAM_REQUEST_CREATED');}catch(error){console.error(`CASH_LOCKED_UPSTREAM_REQUEST_ERROR:${error.message}`);process.exitCode=2;}}
