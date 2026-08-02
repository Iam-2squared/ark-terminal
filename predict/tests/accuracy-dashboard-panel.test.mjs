import test from "node:test";
import assert from "node:assert/strict";

import createAccuracyDashboardPanel
from "../analysis/accuracy-dashboard-panel.js";

test("panel contains four sections",()=>{

const panel=createAccuracyDashboardPanel({
cards:[{}],
calibration:{},
health:{},
metadata:{},
});

assert.equal(panel.sections.length,4);

});
