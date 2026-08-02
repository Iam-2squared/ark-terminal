import test from "node:test";
import assert from "node:assert/strict";

import {

calculatePositionSize,

PositionSizingEngine

}

from "../analysis/position-sizing-engine.js";

test(
"Basic calculation",
()=>{

const r=

calculatePositionSize({

capital:100000,

allocation:0.3,

confidence:80,

riskLevel:20,

price:500

});

assert.ok(
r.shares>0
);

assert.ok(
r.investAmount>0
);

});

test(
"Zero allocation",
()=>{

const r=

calculatePositionSize({

capital:100000,

allocation:0,

price:100

});

assert.equal(
r.shares,
0
);

});

test(
"Class API",
()=>{

const e=

new PositionSizingEngine();

const r=

e.calculate({

capital:50000,

allocation:0.5,

confidence:90,

riskLevel:10,

price:250

});

assert.ok(
r.estimatedCost>0
);

});