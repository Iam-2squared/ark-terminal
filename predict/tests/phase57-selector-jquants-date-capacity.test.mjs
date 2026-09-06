import assert from 'node:assert/strict';
import test from 'node:test';
import {profileDateWideCapacity,Phase57DateCapacityInternals} from '../../scripts/profile_phase57_selector_jquants_date_capacity.mjs';

test('date-wide profiler counts paginated capacity without retaining market rows',async()=>{
  const secret='hidden';let calls=0;
  const report=await profileDateWideCapacity({apiKey:secret,pace:async()=>{},fetchImpl:async(url,options)=>{
    calls+=1;assert.equal(options.headers['x-api-key'],secret);assert.equal(String(url).includes(secret),false);
    const page=new URL(url).searchParams.get('pagination_key');
    const data=page?[{Date:Phase57DateCapacityInternals.PROFILE_DATE,Code:'86970',Time:'15:30',O:101,H:101,L:101,C:101,Vo:2,Va:202}]
      :[{Date:Phase57DateCapacityInternals.PROFILE_DATE,Code:'72030',Time:'09:00',O:100,H:100,L:100,C:100,Vo:1,Va:100}];
    return new Response(JSON.stringify(page?{data}:{data,pagination_key:'next'}),{status:200});
  }});
  assert.equal(calls,2);assert.equal(report.status,'DATE_WIDE_CAPACITY_PROFILE_PASS');
  assert.equal(report.pageCount,2);assert.equal(report.rowCount,2);assert.equal(report.uniqueSymbolCount,2);
  assert.equal(report.paginationComplete,true);assert.equal(JSON.stringify(report).includes(secret),false);
  assert.equal(JSON.stringify(report).includes('72030'),false);assert.ok(Object.values(report.safety).every(value=>value===false));
});

test('authorization failures stay sealed',async()=>{
  const report=await profileDateWideCapacity({apiKey:'x',fetchImpl:async()=>new Response('private-market-payload',{status:403})});
  assert.equal(report.status,'BLOCKED_ENTITLEMENT');assert.equal(JSON.stringify(report).includes('private-market-payload'),false);
  assert.equal(report.validationReleased,false);assert.equal(report.untouchedOosReleased,false);
});
