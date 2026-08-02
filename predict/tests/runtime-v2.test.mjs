import test from "node:test";
import assert from "node:assert/strict";

import{
runtimeV2
}
from "../analysis/runtime-v2.js";

test(
"Runtime execute",
async()=>{

const value=
await runtimeV2.execute(
"sample",
async()=>123
);

assert.equal(
value,
123
);

});

test(
"Runtime stats",
()=>{

const s=
runtimeV2.stats();

assert.ok(
s.version
);

});