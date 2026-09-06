import assert from 'node:assert/strict';
import test from 'node:test';
import {profileDateWideCapacity,Phase57DateCapacityInternals} from '../../scripts/profile_phase57_selector_jquants_date_capacity.mjs';

test('date-wide profiler counts paginated capacity without retaining market rows',async()=>{
  const secret='hidden';let calls=0;
  const report=await profileDateWideCapacity({apiKey:secret,pace:async()=>{},fetchImpl:async(url,options)=>{
    calls+=1;assert.equal(options.headers['x-api-key'],secret);assert.equal(String(url).includes(secret),false);
    const page=new URL(url).searchParams.get('pagination_key');
    const data=page?[{Date:Phase57DateCapacityInternals.PROFILE_DATE,Code:'130A',Time:'15:30',O:101,H:101,L:101,C:101,Vo:2,Va:202}]
      :[{Date:Phase57DateCapacityInternals.PROFILE_DATE,Code:'72030',Time:'09:00',O:100,H:100,L:100,C:100,Vo:1,Va:100}];
    return new Response(JSON.stringify(page?{data}:{data,pagination_key:'next'}),{status:200});
  }});
  assert.equal(calls,2);assert.equal(report.status,'DATE_WIDE_CAPACITY_PROFILE_PASS');
  assert.equal(report.pageCount,2);assert.equal(report.rowCount,2);assert.equal(report.uniqueSymbolCount,2);
  assert.equal(report.paginationComplete,true);assert.equal(JSON.stringify(report).includes(secret),false);
  assert.equal(JSON.stringify(report).includes('72030'),false);assert.ok(Object.values(report.safety).every(value=>value===false));
  assert.equal(Phase57DateCapacityInternals.ISSUE_CODE.test('130A'),true);
});

test('date-wide profiler classifies invalid schema fields without retaining rows',async()=>{
  const date=Phase57DateCapacityInternals.PROFILE_DATE;
  const report=await profileDateWideCapacity({apiKey:'hidden',pace:async()=>{},fetchImpl:async()=>new Response(JSON.stringify({data:[
    {Date:date,Code:'72030',Time:'09:00',O:null,H:101,L:99,C:100,Vo:1,Va:100},
    {Date:date,Code:'bad',Time:'09:00',O:100,H:101,L:99,C:100,Vo:1},
  ]}),{status:200})});
  assert.equal(report.status,'DATE_WIDE_CAPACITY_PROFILE_FAIL');
  assert.equal(report.invalidRows,2);
  assert.deepEqual(report.invalidReasonCounts,{date:0,code:1,time:0,O:1,H:0,L:0,C:0,Vo:0,Va:1});
  assert.equal(JSON.stringify(report).includes('72030'),false);
});

test('authorization failures stay sealed',async()=>{
  const report=await profileDateWideCapacity({apiKey:'x',fetchImpl:async()=>new Response('private-market-payload',{status:403})});
  assert.equal(report.status,'BLOCKED_ENTITLEMENT');assert.equal(JSON.stringify(report).includes('private-market-payload'),false);
  assert.equal(report.validationReleased,false);assert.equal(report.untouchedOosReleased,false);
});
