import test from "node:test";
import assert from "node:assert/strict";

import{

calibrateConfidence,

ConfidenceCalibrator

}

from "../analysis/confidence-calibrator.js";

test(

"High confidence",

()=>{

const r=

calibrateConfidence({

score:90,

agreementRate:95,

historicalAccuracy:88,

engineCount:5,

volatility:10

});

assert.ok(

r.confidence>=80

);

assert.equal(

r.level,

"Very High"

);

}

);

test(

"Low confidence",

()=>{

const r=

calibrateConfidence({

score:30,

agreementRate:20,

historicalAccuracy:35,

engineCount:1,

volatility:95

});

assert.ok(

r.confidence<50

);

}

);

test(

"Class API",

()=>{

const c=

new ConfidenceCalibrator();

const r=

c.evaluate({

score:70

});

assert.ok(

r.confidence>0

);

}

);