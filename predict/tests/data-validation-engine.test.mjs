import test from "node:test";
import assert from "node:assert/strict";

import{

validateAnalysisInput,
buildValidationReport

}from "../analysis/data-validation-engine.js";

test("Valid",()=>{

const r=

validateAnalysisInput({

state:{
analysis:{
technicalScore:80
},
prediction:{
confidence:90
},
indicators:{
rsi:60,
adx:{value:25}
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
r.valid,
true
);

});

test("Invalid",()=>{

const r=

buildValidationReport({

state:{
analysis:{},
indicators:{
rsi:150
}
},

macroInput:{
vix:-1
},

marketInput:{
trendScore:120
}

});

assert.equal(
r.valid,
false
);

assert.ok(
r.health<100
);

});