import test from "node:test";
import assert from "node:assert/strict";

import summarizeAccuracyDashboard
from "../analysis/accuracy-dashboard-summary.js";

test("summary",()=>{

const s=
summarizeAccuracyDashboard([
{accuracy:.9},
{accuracy:.8},
]);

assert.equal(s.count,2);
assert.equal(s.trend.direction,"up");

});
