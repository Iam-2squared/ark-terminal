import fs from 'node:fs';
import path from 'node:path';
import {buildFrozenExitV4Universe} from '../predict/daytrade/phase57-exit-v4-large-scale.js';

const arg=(name,fallback)=>{const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;};
const input=arg('--input','data/screener-universe.json');
const output=arg('--output','tmp/phase57-exit-v4-large-scale-universe.json');
const seed=arg('--seed','phase57-exit-v4-large-scale-v1');
const universe=JSON.parse(fs.readFileSync(input,'utf8'));
const manifest=buildFrozenExitV4Universe({universe,seed});
fs.mkdirSync(path.dirname(output),{recursive:true});
fs.writeFileSync(output,`${JSON.stringify(manifest,null,2)}\n`);
console.log(JSON.stringify({status:manifest.status,output,manifestSha256:manifest.manifestSha256,sourceUniverseRowCount:manifest.sourceUniverseRowCount,pilotCount:manifest.pilot.length,expansionCount:manifest.expansion.length,safety:manifest.safety},null,2));
