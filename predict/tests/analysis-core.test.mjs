import test from "node:test";
import assert from "node:assert/strict";

import{

buildAnalysisCore,
buildAnalysisSummary

}from "../analysis/analysis-core.js";

test("Analysis core",()=>{

const result=

buildAnalysisCore({

state:{

analysis:{
technicalScore:90,
totalScore:90,
dataQualityScore:95
},

prediction:{
confidence:88
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
rsi:65,
volatility:15

}

});

assert.equal(

result.dashboard.action,

"STRONG BUY"

);

});

test("Analysis summary",()=>{

const s=

buildAnalysisSummary({

analysis:

buildAnalysisCore()

});

assert.ok(

s.title===

"AI Analysis"

);

});
