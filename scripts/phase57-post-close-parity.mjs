#!/usr/bin/env node
import fs from 'node:fs';
import {compareDay} from './lib/phase57-parity-report.mjs';
import {admitMode} from './lib/phase57-integration-gates.mjs';
import {digest} from './lib/phase57-offline-parity.mjs';
const [input,output]=process.argv.slice(2);
if(!input||!output)throw Error('USAGE: node scripts/phase57-post-close-parity.mjs paired-stages.json NEW_REPORT.json');
const bytes=fs.readFileSync(input),packet=JSON.parse(bytes);
for(const x of [packet.observed,packet.reference])admitMode({...x,mode:'POST_CLOSE_PARITY'});
const result={...compareDay(packet.observed,packet.reference),runtimeMode:'POST_CLOSE_PARITY',inputHash:digest(bytes)};
fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({output,classification:result.classification,realSessionCaptured:false}));
