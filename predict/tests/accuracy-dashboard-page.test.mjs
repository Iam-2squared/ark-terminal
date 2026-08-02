import test from "node:test";
import assert from "node:assert/strict";

import buildAccuracyDashboardPage
from "../analysis/accuracy-dashboard-page.js";

test("page builds",()=>{

const page=buildAccuracyDashboardPage({
cards:[],
});

assert.ok(page.panel);
assert.ok(page.generatedAt);

});
