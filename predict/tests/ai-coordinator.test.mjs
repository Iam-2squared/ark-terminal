import test from "node:test";
import assert from "node:assert/strict";

import {
 runAICoordinator
}
from "../analysis/ai-coordinator.js";

test(
"Coordinator starts runtime",
async()=>{

 const result=
 await runAICoordinator({});

 assert.equal(
    result.ready,
    true
 );

 assert.equal(
    result.version,
    "ai-coordinator-v1"
 );

 assert.ok(
    result.runtime
 );

});
