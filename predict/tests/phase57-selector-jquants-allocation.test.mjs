import assert from 'node:assert/strict';
import test from 'node:test';
import {buildFreshAllocation} from '../../scripts/allocate_phase57_selector_jquants_fresh_sessions.mjs';
import {planPhase57MinimalHybridFrozen120Split} from '../daytrade/phase57-selector-minimal-hybrid-dataset-guard.js';

function calendar(count=150){
  const rows=[];let cursor=Date.parse('2024-10-01T00:00:00Z');
  while(rows.length<count){const day=new Date(cursor).getUTCDay();if(day!==0&&day!==6)rows.push({Date:new Date(cursor).toISOString().slice(0,10),HolDiv:'1'});cursor+=86_400_000;}
  return rows;
}
const sessions=dates=>dates.map(date=>({sessionDate:date,crossSectionAtomic:true,decisionCutoffs:[`${date}T00:15:00.000Z`]}));

test('allocation fixes 72/24/24 usable sessions with one purge at each boundary',()=>{
  const report=buildFreshAllocation(calendar());assert.equal(report.status,'FRESH_120_ALLOCATION_CANDIDATE');
  assert.equal(report.allocatedSessionCount,122);assert.equal(report.allocatedUsableSessionCount,120);
  assert.equal(report.split.development.length,72);assert.equal(report.split.validation.length,24);assert.equal(report.split.untouchedOos.length,24);
  assert.equal(report.split.purgeDevelopmentValidation.length,1);assert.equal(report.split.purgeValidationOos.length,1);
  const all=[...report.split.development,...report.split.purgeDevelopmentValidation,...report.split.validation,...report.split.purgeValidationOos,...report.split.untouchedOos];
  assert.equal(new Set(all).size,122);assert.equal(all.includes('2025-01-16'),false);assert.equal(all.includes('2025-01-17'),false);
  const guarded=planPhase57MinimalHybridFrozen120Split(sessions(all));
  assert.deepEqual(guarded.development,report.split.development);assert.deepEqual(guarded.validation,report.split.validation);
  assert.deepEqual(guarded.untouchedOos,report.split.untouchedOos);assert.equal(guarded.untouchedOosReleased,false);
  assert.ok(Object.values(report.safety).every(value=>value===false));
});

test('insufficient or invalid calendars fail closed before allocation',()=>{
  assert.equal(buildFreshAllocation(calendar(100)).status,'ALLOCATION_NOT_READY');
  assert.equal(buildFreshAllocation([{Date:'bad',HolDiv:'1'}]).status,'ALLOCATION_NOT_READY');
});
