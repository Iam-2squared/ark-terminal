import test from "node:test";
import assert from "node:assert/strict";

import createAccuracyDashboardHealth
from "../analysis/accuracy-dashboard-health.js";

test("healthy",()=>{

const h=
createAccuracyDashboardHealth({});

assert.equal(
h.status,
"healthy",
);

});

test("warning",()=>{

const h=
createAccuracyDashboardHealth({

accuracy:.5,

});

assert.equal(
h.status,
"warning",
);

});
