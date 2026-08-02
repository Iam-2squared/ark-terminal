import test from "node:test";
import assert from "node:assert/strict";

import generateAccuracyDashboardReport
from "../analysis/accuracy-dashboard-report.js";

test("report",()=>{

const r=
generateAccuracyDashboardReport({

summary:{
accuracy:.8,
},

});

assert.equal(
r.overview.accuracy,
.8,
);

});
