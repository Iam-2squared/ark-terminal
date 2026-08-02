import test from "node:test";
import assert from "node:assert/strict";

import renderAccuracyDashboard
from "../analysis/accuracy-dashboard-ui.js";

test("ui ignores missing root",()=>{

assert.equal(
renderAccuracyDashboard({},null),
undefined,
);

});
