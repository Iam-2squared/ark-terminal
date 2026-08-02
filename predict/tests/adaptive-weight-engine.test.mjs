import test from "node:test";
import assert from "node:assert/strict";

import {

AdaptiveWeightEngine,

normalizeWeights,

updateEngineWeights

}

from "../analysis/adaptive-weight-engine.js";

test(
"Normalize",
()=>{

const w=

normalizeWeights({

a:2,

b:2

});

assert.equal(

w.a,

0.5

);

assert.equal(

w.b,

0.5

);

}
);

test(
"Learning updates weights",
()=>{

const w=

updateEngineWeights({

weights:{

technical:1,

macro:1

},

results:[

{

name:"technical",

accuracy:90

},

{

name:"macro",

accuracy:40

}

]

});

assert.ok(

w.technical>

w.macro

);

}
);

test(
"Engine API",
()=>{

const e=

new AdaptiveWeightEngine({

a:1,

b:1

});

e.learn([

{

name:"a",

accuracy:95

}

]);

const w=

e.getWeights();

assert.ok(

w.a>

w.b

);

}
);