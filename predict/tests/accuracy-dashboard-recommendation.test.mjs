import test from "node:test";
import assert from "node:assert/strict";

import createAccuracyRecommendation
from "../analysis/accuracy-dashboard-recommendation.js";

test("recommendation A",()=>{

const r=
createAccuracyRecommendation({

overview:{
accuracy:.85,
profitFactor:2,
sharpe:1.2,
},

});

assert.equal(r.rating,"A");

});

test("recommendation C",()=>{

const r=
createAccuracyRecommendation({});

assert.equal(r.rating,"C");

});
