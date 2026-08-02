import test from "node:test";
import assert from "node:assert/strict";

import{

renderAiDashboard,
renderReasonList

}from "../analysis/dashboard-renderer.js";

test("Dashboard render",()=>{

const html=

renderAiDashboard({

analysis:{

dashboard:{

action:"BUY",
stars:4,
score:82,
confidence:91,
macro:"BULLISH",
regime:"BULL"

}

}

});

assert.ok(

html.includes("BUY")

);

assert.ok(

html.includes("Score")

);

});

test("Reason list",()=>{

const html=

renderReasonList([

"A",

"B"

]);

assert.ok(

html.includes("<li>A")

);

});
