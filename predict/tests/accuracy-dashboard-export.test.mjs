import test from "node:test";
import assert from "node:assert/strict";

import{
exportAccuracyDashboard,
exportAccuracyDashboardCSV,
}
from "../analysis/accuracy-dashboard-export.js";

test("json export",()=>{

const json=
exportAccuracyDashboard({a:1});

assert.ok(json.includes('"a": 1'));

});

test("csv export",()=>{

const csv=
exportAccuracyDashboardCSV({

cards:[
{
title:"Accuracy",
value:"80%",
},
],

});

assert.ok(csv.includes("Accuracy"));

});
