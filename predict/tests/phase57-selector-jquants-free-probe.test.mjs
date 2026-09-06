import assert from 'node:assert/strict';
import test from 'node:test';
import {probeJquantsFree} from '../../scripts/probe_phase57_selector_jquants_free.mjs';

const response=(status,payload)=>({status,ok:status>=200&&status<300,json:async()=>payload});

test('free entitlement rejection is sanitized and fails closed',async()=>{
  const secret='never-log-this-key';let calls=0;
  const report=await probeJquantsFree({apiKey:secret,fetchImpl:async()=>{calls+=1;if(calls===1)return response(200,{data:[{Code:'86970'}]});if(calls===2)return response(403,{message:`denied ${secret}`});return response(200,{data:[{Date:'2025-01-06',Code:'72030'}]});}});
  const serialized=JSON.stringify(report);
  assert.equal(report.authentication.status,'AUTHENTICATED');
  assert.equal(report.minuteEntitlement.status,'BLOCKED_ENTITLEMENT');
  assert.equal(report.admission.status,'BLOCKED_ENTITLEMENT');
  assert.equal(report.pilot.status,'NOT_RUN');
  assert.equal(report.freeFallback.status,'HISTORICAL_DAILY_AVAILABLE_BUT_NOT_INTRADAY');
  assert.equal(report.freeFallback.canConstructFiveMinute,false);
  assert.equal(calls,3);
  assert.equal(serialized.includes(secret),false);
  assert.equal(report.secretValueObserved,false);
  assert.equal(report.secretPersisted,false);
});

test('minute access runs only a bounded SOURCE_VALIDATION_ONLY pilot',async()=>{
  const rows=[{Date:'2025-01-06',Time:'09:00',Code:'72030',O:100,H:102,L:99,C:101,Vo:1000,Va:100500}];
  let calls=0;
  const report=await probeJquantsFree({apiKey:'test-key',fetchImpl:async()=>{calls+=1;return response(200,{data:calls===1?[{Code:'86970'}]:rows});}});
  assert.equal(calls,5);
  assert.equal(report.minuteEntitlement.status,'AVAILABLE');
  assert.equal(report.pilot.requestCount,4);
  assert.equal(report.pilot.status,'PILOT_DATA_OBSERVED_SEMANTICS_NOT_FULLY_PROVEN');
  assert.equal(report.pilot.payloadPersisted,false);
  assert.equal(report.admission.developmentReleased,false);
  assert.equal(report.admission.validationReleased,false);
  assert.equal(report.admission.untouchedOosReleased,false);
  for(const value of Object.values(report.safety))assert.equal(value,false);
});
