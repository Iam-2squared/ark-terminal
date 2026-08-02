import test from "node:test";
import assert from "node:assert/strict";

import{
analysisOrchestrator
}
from "../analysis/analysis-orchestrator.js";

test(
"Multiple engines",
async()=>{

const report=

await analysisOrchestrator.analyze({

symbol:"7203",

engines:[

{

name:"A",

run:async()=>1

},

{

name:"B",

run:async()=>2

}

]

});

assert.equal(
report.engines.length,
2
);

assert.equal(
report.symbol,
"7203"
);

});