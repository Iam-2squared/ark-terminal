import test from "node:test";
import assert from "node:assert/strict";

import{

SelfLearningEngine

}

from "../analysis/self-learning-engine.js";

test(
"Learning",
()=>{

const e=

new SelfLearningEngine();

const r=

e.learn([

{

strategy:"A",

profit:1000

},

{

strategy:"A",

profit:-500

},

{

strategy:"B",

profit:300

}

]);

assert.equal(

r.A.trades,

2

);

assert.equal(

r.B.trades,

1

);

});

test(
"Reset",
()=>{

const e=

new SelfLearningEngine();

e.learn([

{

strategy:"A",

profit:100

}

]);

e.reset();

assert.equal(

Object.keys(

e.report()

).length,

0

);

});

test(
"Score",
()=>{

const e=

new SelfLearningEngine();

const r=

e.learn([

{

strategy:"A",

profit:5000

}

]);

assert.ok(

r.A.score>

50

);

});