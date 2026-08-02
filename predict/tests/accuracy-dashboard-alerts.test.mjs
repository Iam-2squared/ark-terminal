import test from "node:test";
import assert from "node:assert/strict";

import evaluateAccuracyAlerts
from "../analysis/accuracy-dashboard-alerts.js";

test("warning generated",()=>{

const alerts=
evaluateAccuracyAlerts({

accuracy:.5,

});

assert.equal(alerts.length,1);

});

test("critical generated",()=>{

const alerts=
evaluateAccuracyAlerts({

profitFactor:.8,

});

assert.equal(alerts[0].level,"critical");

});
