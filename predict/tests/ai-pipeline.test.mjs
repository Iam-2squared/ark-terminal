import test from "node:test";
import assert from "node:assert/strict";

import {
 executeAIPipeline
}
from "../analysis/ai-pipeline.js";

test(
"Pipeline executes",
async()=>{

 const result=
 await executeAIPipeline({});

 assert.equal(
    result.ready,
    true
 );

 assert.equal(
    result.version,
    "ai-pipeline-v1"
 );

 assert.ok(
    result.runtime
 );

 assert.ok(
    result.bootstrap
 );

});
