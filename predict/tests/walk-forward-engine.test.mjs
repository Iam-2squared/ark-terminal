import test from "node:test";
import assert from "node:assert/strict";

import{

splitWalkForward,
buildWalkForwardReport

}from "../analysis/walk-forward-engine.js";

test("Split",()=>{

const r=

splitWalkForward({

history:

Array.from(

{length:10},

(_,i)=>({

return:i

})

)

});

assert.equal(

r.train.length,

7

);

assert.equal(

r.test.length,

3

);

});

test("Walk Forward",()=>{

const r=

buildWalkForwardReport({

history:[

{return:5},
{return:6},
{return:4},
{return:7},
{return:5},
{return:6},
{return:4},
{return:6},
{return:5},
{return:4}

]

});

assert.equal(

r.version,

"walk-forward-v1"

);

assert.equal(

r.stable,

true

);

});
