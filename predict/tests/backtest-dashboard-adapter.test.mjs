import test from "node:test";
import assert from "node:assert/strict";

import{
 createBacktestDashboardModel,
 mergeDashboardModel,
}from "../trading/backtest-dashboard-adapter.js";

test("dashboard model",()=>{

 const dashboard=
 createBacktestDashboardModel({

  result:{
   signal:{
    analytics:{
      tradeCount:5,
      winCount:3,
      lossCount:2,
      expectancy:120,
      averageWin:500,
      averageLoss:-250,
    },
   },
  },

 });

 assert.equal(
  dashboard.summary.tradeCount,
  5,
 );

 assert.ok(
  dashboard.cards.length>0,
 );

});

test("prediction merge",()=>{

 const merged=
 mergeDashboardModel(
  {summary:{}},
  {score:82},
 );

 assert.equal(
  merged.prediction.score,
  82,
 );

 assert.ok(
  merged.generatedAt,
 );

});