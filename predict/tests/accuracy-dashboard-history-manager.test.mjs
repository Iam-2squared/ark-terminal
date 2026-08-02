import test from "node:test";
import assert from "node:assert/strict";

import createAccuracyDashboardHistoryManager
from "../analysis/accuracy-dashboard-history-manager.js";

test("manager",()=>{

const m=
createAccuracyDashboardHistoryManager();

m.save({id:10});

assert.equal(
m.latest().id,
10,
);

m.clear();

assert.equal(
m.list().length,
0,
);

});
