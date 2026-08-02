import test from "node:test";
import assert from "node:assert/strict";

import createAccuracyDashboardSnapshot
from "../analysis/accuracy-dashboard-snapshot.js";

test("snapshot",()=>{

const s=
createAccuracyDashboardSnapshot({

cards:[{}],

health:{
status:"healthy",
},

});

assert.equal(
s.health.status,
"healthy",
);

assert.equal(
s.cards.length,
1,
);

});
