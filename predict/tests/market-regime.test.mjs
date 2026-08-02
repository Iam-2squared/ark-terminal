import test from "node:test";
import assert from "node:assert/strict";

import{

detectMarketRegime,
regimeRecommendation

}from "../market-context/market-regime.js";

test("Bull regime",()=>{

const r=
detectMarketRegime({

trendScore:85,
adx:30,
rsi:65,
vix:18

});

assert.equal(
r.regime,
"BULL"
);

});

test("Bear regime",()=>{

const r=
detectMarketRegime({

trendScore:20,
adx:28,
rsi:35

});

assert.equal(
r.regime,
"BEAR"
);

});

test("Recommendation",()=>{

const r=
regimeRecommendation({

regime:"BULL"

});

assert.equal(
r.recommendation,
"Trend Following"
);

});
