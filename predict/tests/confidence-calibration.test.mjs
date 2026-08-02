import test from "node:test";
import assert from "node:assert/strict";

import{

calibrateConfidence,
buildConfidenceReport

}from "../analysis/confidence-calibration.js";

test("Calibration",()=>{

const r=

buildConfidenceReport({

confidence:90,

performance:{
accuracy:80
},

sampleSize:120

});

assert.ok(

r.confidence>

80

);

assert.equal(

r.label,

"High"

);

});

test("Small sample",()=>{

const r=

calibrateConfidence({

confidence:90,

performance:{
accuracy:90
},

sampleSize:5

});

assert.ok(

r.reliability<

0.1

);

});
