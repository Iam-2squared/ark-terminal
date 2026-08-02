import test from "node:test";
import assert from "node:assert/strict";

import {
AnalysisJobQueue
}
from "../analysis/analysis-job-queue.js";

test(
"Sequential jobs",
async()=>{

const q=
new AnalysisJobQueue();

const order=[];

await Promise.all([

q.add(async()=>{
order.push(1);
return 1;
}),

q.add(async()=>{
order.push(2);
return 2;
}),

q.add(async()=>{
order.push(3);
return 3;
})

]);

assert.deepEqual(
order,
[1,2,3]
);

});

test(
"Stats",
async()=>{

const q=
new AnalysisJobQueue();

await q.add(
async()=>100
);

const s=
q.stats();

assert.equal(
s.completed,
1
);

assert.equal(
s.running,
false
);

});

test(
"History clear",
()=>{

const q=
new AnalysisJobQueue();

q.completed.push({});

q.clearHistory();

assert.equal(
q.completed.length,
0
);

});