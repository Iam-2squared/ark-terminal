import fs from 'node:fs';
import path from 'node:path';
import {buildL1CrossSectionDataset} from '../predict/long-only/phase57-long-only-l1-cross-section.js';

const arg=name=>{const i=process.argv.indexOf(name);return i<0?null:process.argv[i+1];};
const input=arg('--input'),output=arg('--output');if(!input||!output)throw new Error('usage: --input <integrated-development.json> --output <l1.json>');
const payload=JSON.parse(fs.readFileSync(input,'utf8'));
const result=buildL1CrossSectionDataset({partition:payload.partition,dailyRows:payload.dailyRows,bars5m:payload.bars5m,terminalAuctions:payload.terminalAuctions,sectorBySymbol:payload.sectorBySymbol});
fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,`${JSON.stringify(result,null,2)}\n`,{flag:'wx'});console.log(JSON.stringify({status:'L1_CROSS_SECTION_READY',partition:result.partition,audit:result.audit,output}));
