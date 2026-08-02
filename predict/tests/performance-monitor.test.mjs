import test from "node:test";
import assert from "node:assert/strict";

import{

PerformanceMonitor

}from "../analysis/performance-monitor.js";

test(

"Performance record",

()=>{

const p=

new PerformanceMonitor();

const t=

p.start("analysis");

const r=

p.end(t);

assert.equal(

r.name,

"analysis"

);

assert.ok(

r.duration>=0

);

}

);

test(

"Summary",

()=>{

const p=

new PerformanceMonitor();

for(

let i=0;

i<5;

i++

){

const t=

p.start(i);

p.end(t);

}

const s=

p.summary();

assert.equal(

s.count,

5

);

assert.ok(

s.average>=0

);

}

);

test(

"Clear",

()=>{

const p=

new PerformanceMonitor();

const t=

p.start("a");

p.end(t);

p.clear();

assert.equal(

p.records.length,

0

);

}

);