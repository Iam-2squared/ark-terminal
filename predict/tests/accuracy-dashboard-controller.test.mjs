import test from "node:test";
import assert from "node:assert/strict";

import AccuracyDashboardController
from "../analysis/accuracy-dashboard-controller.js";

test("controller refresh",async()=>{

let rendered=false;

const controller=
new AccuracyDashboardController({

presenter:{
present(){
rendered=true;
return {};
},
},

dataProvider:async()=>({
rows:[],
}),

});

await controller.refresh();

assert.equal(rendered,true);

});
