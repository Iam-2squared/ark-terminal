import test from "node:test";
import assert from "node:assert/strict";

import scoreAccuracyDashboard
from "../analysis/accuracy-dashboard-score.js";

test("score",()=>{

const s=
scoreAccuracyDashboard({

overview:{
accuracy:.8,
profitFactor:2,
sharpe:1.5,
},

});

assert.ok(s>0);

});
