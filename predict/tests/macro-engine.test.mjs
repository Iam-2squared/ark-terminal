import test from "node:test";
import assert from "node:assert/strict";

import{
evaluateMacroEnvironment,
buildMacroSummary
}from "../market-context/macro-engine.js";

test("Bull macro",()=>{

const m=
evaluateMacroEnvironment({

nikkei:1.2,
nasdaq:2.1,
sox:3.5,
vix:17

});

assert.equal(
m.sentiment,
"BULLISH"
);

});

test("Bear macro",()=>{

const m=
evaluateMacroEnvironment({

nikkei:-2,
nasdaq:-3,
sox:-4,
vix:38

});

assert.equal(
m.sentiment,
"BEARISH"
);

});

test("Summary",()=>{

const s=
buildMacroSummary({

macro:{
score:82,
sentiment:"BULLISH"
}

});

assert.equal(
s.score,
82
);

});
