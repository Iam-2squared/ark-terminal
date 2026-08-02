import test from "node:test";
import assert from "node:assert/strict";

import{

evaluateStrategy,
StrategyEvaluationEngine

}

from "../analysis/strategy-evaluation-engine.js";

test(
"Winning strategy",
()=>{

const r=

evaluateStrategy({

history:[

{return:5},

{return:8},

{return:-2},

{return:6}

]

});

assert.ok(
r.winRate>70
);

assert.ok(
r.score>60
);

});

test(
"Empty",
()=>{

const r=

evaluateStrategy();

assert.equal(
r.trades,
0
);

});

test(
"Class API",
()=>{

const e=

new StrategyEvaluationEngine();

const r=

e.evaluate({

history:[

{return:1}

]

});

assert.equal(
r.trades,
1
);

});