import test from "node:test";
import assert from "node:assert/strict";

import{

buildExplainabilityReport,
buildDecisionNarrative

}from "../analysis/explainability-engine.js";

test("Explainability",()=>{

const r=

buildExplainabilityReport({

recommendation:{
action:"BUY"
},

technicalScore:90,
macroScore:70,
aiScore:95,
riskScore:80

});

assert.equal(

r.action,

"BUY"

);

assert.equal(

r.topFactors.length,

3

);

});

test("Narrative",()=>{

const n=

buildDecisionNarrative({

report:

buildExplainabilityReport({

recommendation:{
action:"BUY"
}

})

});

assert.ok(

n.summary.includes(

"Main drivers"

)

);

});
