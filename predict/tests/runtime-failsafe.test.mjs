import test from "node:test";
import assert from "node:assert/strict";

import{

runFailSafe,
shouldRunAnalysis

}from "../analysis/runtime-failsafe.js";

test("Valid input",()=>{

const r=

runFailSafe({

state:{
analysis:{
technicalScore:80
},
prediction:{
confidence:90
},
indicators:{
rsi:60,
adx:{value:20}
}
},

macroInput:{
vix:18
},

marketInput:{
trendScore:75
}

});

assert.equal(

r.allow,

true

);

});

test("Invalid input",()=>{

const r=

runFailSafe({

state:{
analysis:{},
indicators:{
rsi:120
}
},

macroInput:{
vix:-3
},

marketInput:{
trendScore:130
}

});

assert.equal(

r.allow,

false

);

assert.ok(

r.html.includes(

"AI Analysis Stopped"

)

);

});

test("ShouldRun",()=>{

assert.equal(

shouldRunAnalysis({

state:{
analysis:{
technicalScore:50
}
}

}),

true

);

});