import fs from 'node:fs';
import path from 'node:path';
import {runLongSelectorDevelopment} from '../predict/long-only/phase57-long-only-selector-development.js';

const arg=name=>{const i=process.argv.indexOf(name);return i<0?null:process.argv[i+1];};
const c=arg('--development-c'),d=arg('--development-d'),output=arg('--output');if(!c||!d||!output)throw new Error('usage: --development-c <l1-c.json> --development-d <l1-d.json> --output <selector-freeze.json>');
const result=runLongSelectorDevelopment({developmentC:JSON.parse(fs.readFileSync(c,'utf8')),developmentD:JSON.parse(fs.readFileSync(d,'utf8'))});
fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,`${JSON.stringify(result,null,2)}\n`,{flag:'wx'});console.log(JSON.stringify({status:'LONG_SELECTOR_DEVELOPMENT_FROZEN',selectedTarget:result.selectedTarget,freezeSha256:result.freezeSha256,output}));
