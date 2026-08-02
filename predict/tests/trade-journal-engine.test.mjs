import test from "node:test";
import assert from "node:assert/strict";

import{

TradeJournal

}

from "../analysis/trade-journal-engine.js";

test(
"Journal add",
()=>{

const j=

new TradeJournal();

const r=

j.add({

symbol:"7203",

action:"BUY",

entryPrice:1000,

exitPrice:1100,

shares:100

});

assert.equal(

r.profit,

10000

);

});

test(
"Summary",
()=>{

const j=

new TradeJournal();

j.add({

entryPrice:100,

exitPrice:120,

shares:10

});

j.add({

entryPrice:100,

exitPrice:90,

shares:10

});

const s=

j.summary();

assert.equal(

s.trades,

2

);

assert.equal(

s.winRate,

50

);

});

test(
"Clear",
()=>{

const j=

new TradeJournal();

j.add({});

j.clear();

assert.equal(

j.all().length,

0

);

});