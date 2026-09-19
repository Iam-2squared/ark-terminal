import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {assembleLongOnlyL0Rows,TIMESTAMP_CONTRACT} from '../predict/long-only/phase57-long-only-integrated-dataset.js';

const arg=name=>{const i=process.argv.indexOf(name);return i<0?null:process.argv[i+1];};
const dailyPath=arg('--daily'),masterPath=arg('--master'),output=arg('--output'),partition=arg('--partition')??'DEVELOPMENT_A';
if(!dailyPath||!masterPath||!output)throw new Error('usage: --daily <normalized-cache.json> --master <normalized-cache.json> --partition DEVELOPMENT_A --output <l0-input.json>');
const daily=JSON.parse(fs.readFileSync(dailyPath,'utf8')),master=JSON.parse(fs.readFileSync(masterPath,'utf8'));
const rowsOf=value=>value.rows??(Array.isArray(value)?value.flatMap(page=>page?.payload?.data??page?.data??[]):[]);
const prepared=assembleLongOnlyL0Rows({dailyRows:rowsOf(daily),masterRows:rowsOf(master)});
const sourceParts=[daily.aggregateSha256??daily.sourceSha256,master.aggregateSha256??master.sourceSha256];
if(sourceParts.some(x=>!String(x??'').match(/^[a-f0-9]{64}$/)))throw new Error('daily/master source SHA-256 values are required');
const sourceSha256=createHash('sha256').update(sourceParts.join('|')).digest('hex');
const payload={schemaVersion:1,partition,rows:prepared.rows,admissionAudit:prepared.audit,sourceManifest:{sourceIdentity:'J_QUANTS_V2_DAILY_PLUS_DATED_MASTER_PRIVATE_IMMUTABLE_CACHE',sourceSha256,timestampContract:TIMESTAMP_CONTRACT}};
fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,`${JSON.stringify(payload,null,2)}\n`,{flag:'wx'});
console.log(JSON.stringify({status:'L0_INPUT_PREPARED',partition,rows:prepared.rows.length,audit:prepared.audit,output},null,2));
