import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs';
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

test('entitlement-only mode stops after exactly one Minute request',async()=>{
  let calls=0;
  const report=await probeJquantsFree({apiKey:'test-key',entitlementOnly:true,fetchImpl:async()=>{calls+=1;return response(200,{data:[{Code:'86970'}]});}});
  assert.equal(calls,2);
  assert.equal(report.authentication.status,'AUTHENTICATED');
  assert.equal(report.minuteEntitlement.status,'AVAILABLE');
  assert.equal(report.pilot.status,'NOT_RUN_ENTITLEMENT_ONLY');
  assert.equal(report.admission.status,'DATASET_NOT_READY_AWAITING_SOURCE_VALIDATION_PILOT');
  assert.equal(report.admission.developmentReleased,false);
});

test('real Free entitlement evidence is frozen and keeps every split sealed',()=>{
  const url=new URL('../research/phase57-selector-jquants-free-entitlement-2026-09-06.json',import.meta.url);
  const bytes=fs.readFileSync(url);
  const evidence=JSON.parse(bytes);
  const expected=fs.readFileSync(new URL('../research/phase57-selector-jquants-free-entitlement-2026-09-06.sha256',import.meta.url),'utf8').trim().split(/\s+/)[0];
  assert.equal(createHash('sha256').update(bytes).digest('hex'),expected);
  assert.equal(evidence.status,'BLOCKED_ENTITLEMENT');
  assert.equal(evidence.observations.authentication.httpStatus,200);
  assert.equal(evidence.observations.minuteStockPrices.httpStatus,403);
  assert.equal(evidence.observations.freeHistoricalFallback.httpStatus,200);
  assert.equal(evidence.observations.freeHistoricalFallback.canConstructFiveMinute,false);
  assert.equal(evidence.secretHandling.secretLogged,false);
  assert.equal(evidence.decision.smallAdmissionPilotExecuted,false);
  assert.equal(evidence.decision.developmentReleased,false);
  assert.equal(evidence.decision.validationReleased,false);
  assert.equal(evidence.decision.untouchedOosReleased,false);
  for(const value of Object.values(evidence.safety))assert.equal(value,false);
});
