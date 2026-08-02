import test from "node:test";
import assert from "node:assert/strict";

import{

renderAnalysisPanel,
createAnalysisView

}from "../analysis/ui-integration.js";

test("Panel render",()=>{

const html=

renderAnalysisPanel({

state:{

analysis:{
technicalScore:90,
totalScore:90,
dataQualityScore:95
},

prediction:{
confidence:90
},

indicators:{
rsi:65,
adx:{value:30},
atr:{percent:2}
}

},

macroInput:{

nikkei:1,
nasdaq:2,
sox:3,
vix:18

},

marketInput:{

trendScore:85,
adx:30,
rsi:65

}

});

assert.ok(

html.includes(

"Buy Factors"

)

);

assert.ok(

html.includes(

"Risk Factors"

)

);

});

test("Analysis view",()=>{

const v=

createAnalysisView({});

assert.ok(

typeof v.html===

"string"

);

});
