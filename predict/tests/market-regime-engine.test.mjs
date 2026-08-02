import test from "node:test";
import assert from "node:assert/strict";

import{

detectMarketRegime,

MarketRegimeEngine

}

from "../analysis/market-regime-engine.js";

test(
"Bull",
()=>{

const r=

detectMarketRegime({

trendScore:90,

momentum:85,

breadth:80,

vix:15

});

assert.equal(

r.regime,

"BULL"

);

});

test(
"Bear",
()=>{

const r=

detectMarketRegime({

trendScore:20,

momentum:25,

breadth:30

});

assert.equal(

r.regime,

"BEAR"

);

});

test(
"Class API",
()=>{

const e=

new MarketRegimeEngine();

const r=

e.analyze({

trendScore:60

});

assert.ok(

r.score>=0

);

});