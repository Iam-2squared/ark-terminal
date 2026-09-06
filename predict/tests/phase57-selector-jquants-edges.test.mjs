import assert from 'node:assert/strict';
import test from 'node:test';
import {inspectEdgeRows,minuteBoundaryMembership,runJquantsEdgeProbe} from '../../scripts/probe_phase57_selector_jquants_edges.mjs';
const query={code:'72030',date:'2025-01-08'};
const row=(Time,extra={})=>({Date:query.date,Code:query.code,Time,O:100,H:101,L:99,C:100,Vo:10,Va:1000,...extra});
const response=(status,payload)=>({status,json:async()=>payload});

test('boundary membership distinguishes hypotheses without normalizing timestamps',()=>{
  for(const [time,start,end,auction] of [['09:00',true,false,false],['09:01',true,true,false],
    ['11:30',false,true,true],['12:30',true,false,false],['12:31',true,true,false],
    ['15:30',false,true,true],['11:45',false,false,false]]){
    assert.deepEqual(minuteBoundaryMembership(time),{barStart:start,barEnd:end,auctionBoundary:auction});
  }
});
test('09:00 non-flat and closing rows falsify uniform BAR_END but cannot prove auction semantics',()=>{
  const result=inspectEdgeRows([row('09:00'),row('11:30',{H:100,L:100})],query);
  assert.equal(result.uniformBarEndFalsified,true);
  assert.equal(result.strictBarStartSessionRangeFalsified,true);
  assert.equal(result.hypothesis,'BAR_START_WITH_TERMINAL_AUCTION_CANDIDATE_NOT_CONFIRMED');
  assert.equal(result.interiorLunchRows,0);
  assert.equal(result.sourceTimestampShiftApplied,false);
  assert.equal(result.corporateActionBasis,'UNKNOWN_NOT_ESTABLISHED_BY_FIELD_NAMES');
});
test('invalid numeric values and query mismatches are counted without logging payloads',()=>{
  const result=inspectEdgeRows([row('11:45',{O:null,Va:null,Code:'67580'})],query);
  assert.equal(result.invalidOhlcCount,1);assert.equal(result.invalidVolumeTurnoverCount,1);
  assert.equal(result.queryMismatchCount,1);assert.equal(result.interiorLunchRows,1);
});
test('edge probe follows pagination, uses fresh source-only sessions and never returns prices or credentials',async()=>{
  let calls=0;const secret='fixture-secret-never-persist';
  const report=await runJquantsEdgeProbe({apiKey:secret,pace:async()=>{},fetchImpl:async(url,options)=>{
    calls++;assert.equal(options.redirect,'error');assert.equal(options.headers['x-api-key'],secret);
    assert.equal(String(url).includes(secret),false);
    const q=new URL(url).searchParams;assert.ok(['2025-01-08','2025-01-09'].includes(q.get('date')));
    const next=q.has('pagination_key');
    return response(200,{data:[row(next?'11:30':'09:00',{Date:q.get('date'),Code:q.get('code')})],
      pagination_key:next?null:'page-next'});
  }});
  assert.equal(calls,8);assert.ok(report.groups.every(g=>g.paginationComplete));
  assert.equal(report.sourceValidationPass,false);assert.equal(report.aggregationPerformed,false);
  assert.equal(report.marketBarCloseIsProviderAvailableAt,false);
  assert.equal(JSON.stringify(report).includes(secret),false);
  assert.equal(JSON.stringify(report).includes('"O":'),false);
  assert.equal(report.untouchedOosReleased,false);
});
test('denial and rate limits stop requests immediately without persisting error text',async()=>{
  for(const status of [401,403,429]){let calls=0;
    const report=await runJquantsEdgeProbe({apiKey:'s',pace:async()=>{},fetchImpl:async()=>{
      calls++;return response(status,{message:'secret s'});
    }});
    assert.equal(calls,1);assert.equal(report.requests[0].httpStatus,status);
    assert.equal(report.sourceValidationPass,false);assert.equal(report.groups.length,0);
  }
});
test('empty HTTP200 is not PASS and no configured secret means no request',async()=>{
  const empty=await runJquantsEdgeProbe({apiKey:'s',fetchImpl:async()=>response(200,{data:[]})});
  assert.equal(empty.status,'PILOT_FAILED_DATA_INTEGRITY');assert.equal(empty.sourceValidationPass,false);
  const missing=await runJquantsEdgeProbe({fetchImpl:async()=>{throw new Error('must not call');}});
  assert.equal(missing.status,'AUTH_REQUIRED');assert.equal(missing.requestCount,0);
});
test('malformed observations stop the audit as integrity failures rather than timestamp uncertainty',async()=>{
  for(const data of [[row('09:00',{Va:null})],[row('11:45')],[row('09:00'),row('09:00')]]){
    let calls=0;
    const report=await runJquantsEdgeProbe({apiKey:'s',pace:async()=>{},fetchImpl:async()=>{
      calls++;return response(200,{data});
    }});
    assert.equal(calls,1);assert.equal(report.status,'PILOT_FAILED_DATA_INTEGRITY');
    assert.equal(report.sourceValidationPass,false);
  }
});
