import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import test from 'node:test';

const JSON_URL=new URL('../research/phase57-selector-minimal-hybrid-source-resolution-2026-09-06.json',import.meta.url);
const SHA_URL=new URL('../research/phase57-selector-minimal-hybrid-source-resolution-2026-09-06.sha256',import.meta.url);

test('source resolution is frozen without opening training or sealed splits',()=>{
  const bytes=fs.readFileSync(JSON_URL);
  const report=JSON.parse(bytes);
  const expected=fs.readFileSync(SHA_URL,'utf8').trim().split(/\s+/)[0];
  assert.equal(createHash('sha256').update(bytes).digest('hex'),expected);
  assert.equal(report.status,'DATASET_NOT_READY');
  assert.equal(report.oneMinuteBarsRequired,false);
  assert.equal(report.requiredResearchIntervalMinutes,5);
  assert.equal(report.trainingStarted,false);
  assert.equal(report.featureSelectionStarted,false);
  assert.equal(report.validationReleased,false);
  assert.equal(report.untouchedOosReleased,false);
  assert.equal(report.smallAdmissionPilot.executed,false);
  assert.equal(report.prospectivePlan.status,'PLAN_FIXED_NOT_STARTED');
  for(const [key,value] of Object.entries(report.safety))assert.equal(value,false,key);
});

test('Yahoo interpretation preserves the frozen identity ancestry and period guards',()=>{
  const report=JSON.parse(fs.readFileSync(JSON_URL));
  const interpretation=report.frozenContractInterpretation;
  assert.equal(interpretation.phaseAContractChanged,false);
  assert.equal(interpretation.providerWideYahooBan,false);
  assert.equal(interpretation.forbiddenDatasetId,'PHASE57_SELECTOR_YAHOO_5M_24626FD37F8633F4');
  assert.equal(interpretation.forbiddenFirstSession,'2026-06-12');
  assert.equal(interpretation.forbiddenLastSession,'2026-09-04');
  assert.equal(interpretation.unusedYahooObservationsAdmittedNow,false);
  assert.ok(interpretation.rejectedFreshnessClaims.includes('DESCENDANT_OR_PARENT_ANCESTRY_OF_CONSUMED_EVIDENCE'));
});

test('no historical source is mislabeled GO and prospective data stays sealed',()=>{
  const report=JSON.parse(fs.readFileSync(JSON_URL));
  assert.ok(report.sourceDecisionMatrix.length>=6);
  assert.equal(report.sourceDecisionMatrix.some(row=>row.decision==='GO'),false);
  assert.equal(report.sourceDecisionMatrix.find(row=>row.source==='MARKETSPEED_II_RSS_READ_ONLY').decision,'PROSPECTIVE_PRIMARY_PENDING_PILOT');
  assert.equal(report.prospectivePlan.formalAccumulationStarts,'ONLY_AFTER_PILOT_PASS_WITH_PILOT_SESSIONS_EXCLUDED');
  assert.equal(report.prospectivePlan.validationReleased,false);
  assert.equal(report.prospectivePlan.untouchedOosReleased,false);
});
