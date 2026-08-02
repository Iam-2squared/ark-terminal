import test from "node:test";
import assert from "node:assert/strict";

import{

buildRecommendation,
recommendationBadge

}from "../analysis/recommendation-engine.js";

test("Strong Buy",()=>{

const r=

buildRecommendation({

technicalScore:92,
macroScore:85,
aiScore:95,
riskScore:80

});

assert.equal(
r.action,
"STRONG BUY"
);

assert.equal(
r.stars,
5
);

});

test("Sell",()=>{

const r=

buildRecommendation({

technicalScore:20,
macroScore:25,
aiScore:30,
riskScore:20

});

assert.equal(
r.action,
"SELL"
);

});

test("Badge",()=>{

const b=

recommendationBadge({

recommendation:

buildRecommendation({

technicalScore:80,
macroScore:80,
aiScore:85,
riskScore:70

})

});

assert.ok(
b.stars>=4
);

});
