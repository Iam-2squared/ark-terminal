import test from "node:test";
import assert from "node:assert/strict";

import{
 enrichTrade,
 enrichTradeHistory,
}from "../trading/trade-history-enricher.js";

test("trade enrichment",()=>{

 const row=enrichTrade({

  grossPnl:1000,

  commissionCost:100,

  spreadCost:20,

  slippageCost:30,

  maxPrice:110,

  minPrice:95,

 });

 assert.equal(
  row.totalTradingCost,
 150,
 );

 assert.equal(
  row.netPnl,
 850,
 );

 assert.equal(
  row.highestPrice,
 110,
 );

 assert.equal(
  row.lowestPrice,
 95,
 );

});

test("history enrichment",()=>{

 const rows=
 enrichTradeHistory([
  {grossPnl:100},
  {grossPnl:200},
 ]);

 assert.equal(
  rows.length,
 2,
 );

});