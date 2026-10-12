import assert from 'node:assert/strict';
import test from 'node:test';
import {measureOnePct} from '../long-only/phase57-long-only-top5-hit-evaluator.js';

const bar=(start,available,{high=100,close=100}={})=>({barStartJst:`2024-01-10T${start}:00+09:00`,availableAtJst:`2024-01-10T${available}:00+09:00`,high,close});

test('one-percent High touch and Close confirmation stay distinct',()=>{
  const out=measureOnePct({reference:100,decisionTimeJst:'09:30',bars:[bar('09:30','09:35',{high:101.5,close:100.5})]});
  assert.equal(out.highOpportunity1,1);
  assert.equal(out.closeOpportunity1,0);
  assert.equal(out.timeToHigh1Min,5);
  assert.equal(out.timeToClose1Min,null);
});

test('first Close confirmation chooses the earliest causal path',()=>{
  const out=measureOnePct({reference:100,decisionTimeJst:'14:50',bars:[bar('14:50','14:55',{high:101.5,close:101.2})],auctions:[{minute:900,close:102}]});
  assert.equal(out.closeOpportunity1,1);
  assert.equal(out.auctionCloseOpportunity1,1);
  assert.equal(out.timeToClose1Min,5);
});

test('pre-decision bars and absent future paths fail closed',()=>{
  const prior=measureOnePct({reference:100,decisionTimeJst:'09:30',bars:[bar('09:25','09:30',{high:110,close:110})]});
  assert.equal(prior.highOpportunity1,null);
  assert.equal(prior.closeOpportunity1,null);
  assert.deepEqual(measureOnePct({reference:null,decisionTimeJst:'09:30'}),{
    highOpportunity1:null,closeOpportunity1:null,auctionCloseOpportunity1:null,timeToHigh1Min:null,timeToClose1Min:null,
  });
});
