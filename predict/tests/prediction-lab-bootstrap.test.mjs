import test from "node:test";
import assert from "node:assert/strict";

import {
 bootstrapPredictionLab
}
from "../analysis/prediction-lab-bootstrap.js";

test(
"Bootstrap initializes",
async()=>{

 const result=
 await bootstrapPredictionLab({});

 assert.equal(
    result.initialized,
    true
 );

 assert.equal(
    typeof result.timestamp,
    "string"
 );

});
