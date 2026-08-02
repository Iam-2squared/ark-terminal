import test from "node:test";
import assert from "node:assert/strict";

import{

AnalysisCache

}from "../analysis/analysis-cache.js";

test("Cache Set/Get",()=>{

const c=

new AnalysisCache();

c.set(

{code:"7203"},

{score:90}

);

assert.deepEqual(

c.get({

code:"7203"

}),

{score:90}

);

});

test("Cache Clear",()=>{

const c=

new AnalysisCache();

c.set(1,2);

c.clear();

assert.equal(

c.size(),

0

);

});

test("Cache Expire",()=>{

const c=

new AnalysisCache();

c.set("A",1);

const item=

c.cache.get('"A"');

item.time-=999999;

assert.equal(

c.get("A",100),

null

);

});