import test from 'node:test';import assert from 'node:assert/strict';
import {sessionClustering,buildDiagnostics} from '../lib/phase57-baseline-diagnostics.mjs';
test('perfect within-session clustering reduces effective N to cluster count',()=>{const c=sessionClustering([['a',1],['a',1],['b',5],['b',5]]);assert.equal(c.icc,1);assert.equal(c.effectiveN,2);});
test('constant outcomes and one cluster do not fabricate effective N',()=>{assert.equal(sessionClustering([['a',1],['a',1],['b',1],['b',1]]).effectiveN,null);assert.equal(sessionClustering([['a',1],['a',2]]).icc,null);});
test('negative ICC is retained but not used to inflate effective N',()=>{const c=sessionClustering([['a',0],['a',10],['b',0],['b',10]]);assert.ok(c.icc<0);assert.equal(c.effectiveN,4);});
test('empty diagnostic has null precision and zero labels',()=>{const d=buildDiagnostics([]);assert.equal(d.eventLevel.ALL.coverage,null);assert.equal(d.eventLevel.ALL.horizons[1].hitRate,null);assert.equal(d.labelCompletenessAllSelections[12].complete,0);});
import fs from 'node:fs';import {createHash} from 'node:crypto';import {gunzipSync} from 'node:zlib';
const root='predict/research/phase57-entry-baseline-real-gates-2026-09-09',hash=b=>createHash('sha256').update(b).digest('hex');
test('real gate evidence pins all17 sessions and remains pre-outcome',()=>{
 const g=JSON.parse(fs.readFileSync(`${root}/gates.json`));
 assert.deepEqual(['gate1','gate2','gate3','gate4'].map(k=>g[k]),['GO','GO','GO','GO']);assert.equal(g.eligibleSessions.length,17);assert.equal(g.baselineOutcomeViewed,false);assert.equal(g.protectedNewlyOpened,0);assert.equal(g.protectedNewOutcomeViewed,0);
 assert.equal(hash(fs.readFileSync('predict/research/phase57-entry-baseline-measurement-policy-v1.json')),g.policySha256);
 const raw=gunzipSync(fs.readFileSync(`${root}/archive-inventory.json.gz`));assert.equal(hash(raw),g.archiveInventorySha256);const a=JSON.parse(raw);
 assert.deepEqual(a.inventory.map(r=>r.sessionDate),g.eligibleSessions);assert.ok(a.inventory.every(r=>r.sessionDate>='2026-08-13'&&r.sessionDate<='2026-09-04'));assert.equal(a.receiptFilesVerified,7410);
 assert.equal(hash(fs.readFileSync(`${root}/prior-audit-before-selection.json`)),g.priorAuditSha256);assert.equal(hash(fs.readFileSync(`${root}/real-adapter-parity.json`)),g.realParitySha256);
});
test('constant prior pack has no protected or baseline dates',()=>{
 const p=JSON.parse(fs.readFileSync(`${root}/prior-audit-before-selection.json`));assert.ok(p.uniqueSessionDates.every(d=>d>'2026-06-11'&&d<'2026-08-13'));assert.ok(p.latestOutcomeTimestamp<'2026-08-13T00:00:00.000Z');assert.equal(p.futureOutcomeViolations,0);
});
