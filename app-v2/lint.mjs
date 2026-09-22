import fs from 'node:fs';import assert from 'node:assert/strict';import {spawnSync} from 'node:child_process';
for(const file of ['server.mjs','data.mjs','demo.mjs','build.mjs'])assert.equal(spawnSync(process.execPath,['--check',file]).status,0);
const ui=fs.readFileSync('src/app.ts','utf8');assert.ok(!/\beval\s*\(|new Function\(|document\.write/.test(ui));assert.ok(!/method\s*:\s*['"](?:POST|PUT|DELETE|PATCH)/.test(ui));console.log('Syntax and read-only architecture lint PASS');
