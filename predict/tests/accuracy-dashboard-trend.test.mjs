import test from "node:test";
import assert from "node:assert/strict";

import calculateAccuracyTrend
from "../analysis/accuracy-dashboard-trend.js";

test("trend up",()=>{

const r=
calculateAccuracyTrend([
{accuracy:.8},
{accuracy:.7},
]);

assert.equal(r.direction,"up");

});

test("trend flat",()=>{

const r=
calculateAccuracyTrend([]);

assert.equal(r.direction,"flat");

});
