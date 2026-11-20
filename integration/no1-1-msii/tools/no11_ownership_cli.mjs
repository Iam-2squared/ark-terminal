#!/usr/bin/env node
/**
 * Local-only explicit Ownership drafting/freezing tool.
 * Never uploads broker positions, never touches Excel or sends an order.
 */
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {freezeConfirmedOwnership} from '../runtime/freeze_ownership.mjs';
import {inspectReadOnlySnapshot} from '../runtime/account_gate.mjs';

function parse(argv) {
  if(!['draft','freeze'].includes(argv[0])||(argv.length-1)%2)throw Error('USAGE_DRAFT_OR_FREEZE');
  const out={mode:argv[0]};
  for(let i=1;i<argv.length;i+=2){
    const k=argv[i],v=argv[i+1];
    if(!k.startsWith('--')||k.slice(2) in out)throw Error('ARG_INVALID_OR_DUPLICATE');
    out[k.slice(2)]=v;
  }
  return out;
}
function read(file,label){
  if(!file||!path.isAbsolute(file))throw Error(label+'_ABSOLUTE_PATH_REQUIRED');
  const obj=JSON.parse(fs.readFileSync(file,'utf8').replace(/^\uFEFF/,''));
  if(!obj||typeof obj!=='object'||Array.isArray(obj))throw Error(label+'_OBJECT_REQUIRED');
  return obj;
}
function write(file,value) {
  if(!file||!path.isAbsolute(file))throw Error('OUTPUT_ABSOLUTE_PATH_REQUIRED');
  if(fs.existsSync(file))throw Error('OUTPUT_ALREADY_EXISTS');
  fs.mkdirSync(path.dirname(file),{recursive:true,mode:0o700});
  fs.writeFileSync(file,JSON.stringify(value,null,2)+'\n',{flag:'wx',mode:0o600});
}
export function runOwnershipTool(args) {
  const snapshot=read(args.snapshot,'SNAPSHOT'),health=read(args.health,'HEALTH');
  if(args.mode==='draft'){
    const probe=inspectReadOnlySnapshot({snapshot,health});
    if(probe.status!=='RSS_STATUS_OBSERVED_READ_ONLY')throw Error('RSS_NOT_FRESH_READ_ONLY');
    if(snapshot.orders?.length)throw Error('OPEN_BROKER_ORDERS_PRESENT');
    return {schemaId:'ARK_NO11_PRIVATE_OWNERSHIP_DRAFT_V1',
      status:'USER_CLASSIFICATION_REQUIRED',
      positions:snapshot.positions.map(row=>({
        symbol:row.symbol,quantity:row.quantity,owner:'UNCLASSIFIED'
      })),sourceCapturedAt:snapshot.captureCompletedAt,
      instruction:'Set each owner exactly EXTERNAL or ARK_MANAGED, then confirm; never upload this private file'};
  }
  const classification=read(args.classification,'CLASSIFICATION');
  if(classification.schemaId!=='ARK_NO11_PRIVATE_OWNERSHIP_DRAFT_V1')throw Error('CLASSIFICATION_SCHEMA_INVALID');
  if(!Array.isArray(classification.positions))throw Error('CLASSIFICATION_ROWS_REQUIRED');
  const external=[],managed=[];
  for(const row of classification.positions){
    if(row.owner==='EXTERNAL')external.push({symbol:row.symbol,quantity:row.quantity});
    else if(row.owner==='ARK_MANAGED')managed.push({symbol:row.symbol,quantity:row.quantity});
    else throw Error('UNCLASSIFIED_POSITION_REMAINS');
  }
  return freezeConfirmedOwnership({snapshot,health,
    confirmedExternal:external,confirmedArkManaged:managed,
    explicitUserConfirmation:args.confirm});
}
if(process.argv[1]&&path.resolve(process.argv[1])===path.resolve(fileURLToPath(import.meta.url))){
  try{
    const args=parse(process.argv.slice(2));
    const result=runOwnershipTool(args);
    write(args.output,result);
    console.log(result.schemaId);
    console.log('STATUS='+(result.status||'FROZEN_PRIVATE_BASELINE'));
    console.log('NO_ORDER_OR_RSS_CALL=TRUE');
  }catch(e){console.error('NO11_OWNERSHIP_ERROR:'+e.message);process.exitCode=2;}
}
