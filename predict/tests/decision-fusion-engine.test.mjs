import test from "node:test";
import assert from "node:assert/strict";

import{

DecisionFusionEngine,

fuseEngineDecisions

}

from "../analysis/decision-fusion-engine.js";

test(

"Fusion",

()=>{

const r=

fuseEngineDecisions({

engines:[

{

score:90,

confidence:90,

weight:2

},

{

score:70,

confidence:80,

weight:1

}

]

});

assert.ok(

r.score>80

);

assert.equal(

r.action,

"BUY"

);

});

test(

"Empty",

()=>{

const r=

fuseEngineDecisions();

assert.equal(

r.action,

"HOLD"

);

});

test(

"Class API",

()=>{

const e=

new DecisionFusionEngine();

const r=

e.run({

engines:[

{

score:80,

confidence:85,

weight:1

}

]

});

assert.equal(

r.engineCount,

1

);

});