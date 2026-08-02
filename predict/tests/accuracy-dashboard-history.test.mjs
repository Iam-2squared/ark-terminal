import test from "node:test";
import assert from "node:assert/strict";

import AccuracyDashboardHistory
from "../analysis/accuracy-dashboard-history.js";

test("history push",()=>{

const h=
new AccuracyDashboardHistory();

h.push({id:1});
h.push({id:2});

assert.equal(
h.latest().id,
2,
);

assert.equal(
h.all().length,
2,
);

});
