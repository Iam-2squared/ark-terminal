import assert from 'node:assert/strict';
import test from 'node:test';
import {inspectReconstructionRows,runMinuteReconstructionPilot,PILOT_DATES,PILOT_CODES} from '../../scripts/pilot_phase57_selector_jquants_minute_reconstruction.mjs';

const sourceRows=(date='2025-01-16',code='72030')=>[
  {Date:date,Code:code,Time:'09:00',O:100,H:101,L:99,C:100,Vo:10,Va:1000},
  {Date:date,Code:code,Time:'09:02',O:100,H:102,L:100,C:101,Vo:20,Va:2020},
  {Date:date,Code:code,Time:'11:30',O:103,H:103,L:103,C:103,Vo:30,Va:3090},
  {Date:date,Code:code,Time:'12:30',O:104,H:105,L:103,C:104,Vo:40,Va:4160},
  {Date:date,Code:code,Time:'15:30',O:106,H:106,L:106,C:106,Vo:50,Va:5300},
];

test('verified adapter classifies terminal auctions and emits deterministic causal regular 5m bars',()=>{
  const result=inspectReconstructionRows(sourceRows(),{date:'2025-01-16',code:'72030'});
  assert.equal(result.status,'PASS');assert.equal(result.terminalAuctionMinuteRows,2);
  assert.equal(result.regularContinuousMinuteRows,3);assert.equal(result.fiveMinuteBars,2);
  assert.equal(result.sameInputDeterministic,true);assert.equal(result.terminalAuctionsExcludedFromRegular5m,true);
  assert.equal(result.noFabricatedMinutes,true);
});

test('a missing closing auction prevents Pilot PASS',()=>{
  const result=inspectReconstructionRows(sourceRows().filter(row=>row.Time!=='15:30'),{date:'2025-01-16',code:'72030'});
  assert.equal(result.status,'FAIL');assert.equal(result.passed,false);
});

test('bounded transport passes four new source-only groups without leaking secret or raw rows',async()=>{
  const secret='hidden';let calls=0;
  const report=await runMinuteReconstructionPilot({apiKey:secret,pace:async()=>{},fetchImpl:async(url,options)=>{
    calls+=1;assert.equal(options.headers['x-api-key'],secret);assert.equal(String(url).includes(secret),false);
    const parsed=new URL(url),date=parsed.searchParams.get('date'),code=parsed.searchParams.get('code');
    assert.ok(PILOT_DATES.includes(date));assert.ok(PILOT_CODES.includes(code));
    return new Response(JSON.stringify({data:sourceRows(date,code)}),{status:200});
  }});
  assert.equal(calls,4);assert.equal(report.status,'SOURCE_VALIDATION_ONLY_PASS');assert.equal(report.sourceValidationPass,true);
  assert.equal(report.formalAcquisitionStarted,false);assert.equal(report.developmentReleased,false);
  assert.equal(report.validationReleased,false);assert.equal(report.untouchedOosReleased,false);
  const encoded=JSON.stringify(report);assert.equal(encoded.includes(secret),false);assert.equal(encoded.includes('"O"'),false);
  assert.ok(Object.values(report.safety).every(value=>value===false));
});

test('auth and entitlement failures remain sealed',async()=>{
  const missing=await runMinuteReconstructionPilot({fetchImpl:async()=>{throw new Error('not called');}});
  assert.equal(missing.status,'AUTH_REQUIRED');
  const denied=await runMinuteReconstructionPilot({apiKey:'x',fetchImpl:async()=>new Response('private',{status:403})});
  assert.equal(denied.status,'BLOCKED_ENTITLEMENT');assert.equal(JSON.stringify(denied).includes('private'),false);
  assert.equal(denied.sourceValidationPass,false);
});
