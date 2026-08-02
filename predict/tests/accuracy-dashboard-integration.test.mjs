import test from "node:test";
import assert from "node:assert/strict";

import integrateAccuracyDashboard
from "../analysis/accuracy-dashboard-integration.js";

test("integration returns api",()=>{

const api=
integrateAccuracyDashboard();

assert.ok(api.refresh);
assert.ok(api.controller);

});
