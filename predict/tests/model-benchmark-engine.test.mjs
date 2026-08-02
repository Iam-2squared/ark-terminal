import test from "node:test";
import assert from "node:assert/strict";

import{

benchmarkModels,
ModelBenchmarkEngine

}

from "../analysis/model-benchmark-engine.js";

test(
"Ranking",
()=>{

const r=

benchmarkModels({

models:[

{

name:"A",

accuracy:82,

profitFactor:1.9,

maxDrawdown:12,

latency:40

},

{

name:"B",

accuracy:91,

profitFactor:2.5,

maxDrawdown:8,

latency:25

}

]

});

assert.equal(

r.best.name,

"B"

);

assert.equal(

r.count,

2

);

});

test(
"Class",
()=>{

const e=

new ModelBenchmarkEngine();

const r=

e.evaluate({

models:[

{

name:"A",

accuracy:90

}

]

});

assert.equal(

r.count,

1

);

});