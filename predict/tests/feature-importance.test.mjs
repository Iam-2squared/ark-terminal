import test from "node:test";
import assert from "node:assert/strict";

import { calculateFeatureImportance }
from "../analysis/feature-importance-engine.js";

test("Feature importance ranks strongest feature first", () => {

const result = calculateFeatureImportance(
{
rsi:0.8,
macd:0.2,
volume:0.4
},
{
score:80
}
);

assert.equal(result[0].name,"rsi");
assert.ok(result[0].weight > result[1].weight);

});
