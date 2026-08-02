import test from "node:test";
import assert from "node:assert/strict";

import buildAccuracyDashboardDecision
from "../analysis/accuracy-dashboard-decision.js";

test("decision",()=>{

const d=
buildAccuracyDashboardDecision({

overview:{
accuracy:.9,
profitFactor:2,
sharpe:2,
},

});

assert.equal(
d.approved,
true,
);

});
