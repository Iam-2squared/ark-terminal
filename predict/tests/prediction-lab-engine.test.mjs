import test from "node:test";
import assert from "node:assert/strict";

import{

buildPredictionLabEngine,
buildPredictionSummary

}from "../analysis/prediction-lab-engine.js";

test("Prediction Lab Engine",()=>{

const engine=

buildPredictionLabEngine({

state:{

analysis:{

technicalScore:90,
totalScore:90,
dataQualityScore:95

},

prediction:{

confidence:88

},

indicators:{

rsi:65,
adx:{value:30},
atr:{percent:2}

}

},

macroInput:{

nikkei:1,
nasdaq:2,
sox:3,
vix:18

},

marketInput:{

trendScore:85,
adx:30,
rsi:65,
volatility:15

},

history:[

{return:5},
{return:3},
{return:-1},
{return:4},
{return:2},
{return:5}

]

});

assert.equal(

engine.version,

"prediction-lab-v2"

);

assert.ok(

engine.dashboard.score>0

);

});

test("Prediction Summary",()=>{

const s=

buildPredictionSummary({

engine:

buildPredictionLabEngine()

});

assert.equal(

s.title,

"Prediction Lab AI"

);

});
