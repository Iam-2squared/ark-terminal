import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from scripts.phase57_msh_entry_v2_architecture import OUT, CONTRACT, read, run, sha, mae_bucket, mfe_bucket

class ArchitectureIntegrity(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.d=read(OUT/'diagnostic.json.gz');cls.a=read(OUT/'architecture-decision.json')
 def test_partition_and_joint(self):
  self.assertEqual(len({r['eventId'] for r in self.d['rows']}),277)
  self.assertEqual(sum(sum(v.values()) for v in self.d['jointMatrix'].values()),181)
  self.assertEqual(sum(v['N'] for v in self.d['tailCohorts'].values()),181)
  self.assertEqual(self.d['coverage']['intersectionStrictAndPaired'],158)
  self.assertEqual(self.d['strict181']['tail']['-10']['n'],10)
 def test_user_boundary_inclusions(self):
  self.assertEqual([mae_bucket(v) for v in [-.5,-1,-2,-5,-10]],['SAFE_LOW_ADVERSE','MILD_ADVERSE','MODERATE_ADVERSE','SEVERE_ADVERSE','EXTREME_FAILURE'])
  self.assertEqual([mfe_bucket(v) for v in [0,1,2,3,5]],['LT1','1_TO_2','2_TO_3','3_TO_5','GE5'])
 def test_contribution_reconciles(self):
  c=self.d['concentration'];self.assertAlmostEqual(sum(c['symbolNetPnlJpy'].values()),230530.7,places=5)
  self.assertEqual(c['profitableSymbols']+c['losingSymbols'],c['uniqueAcceptedSymbols'])
  self.assertEqual(c['top1Mechanism']['positiveExits']+c['top1Mechanism']['grossFlatExits'],22)
  self.assertEqual(sum(c['tailCountsBySymbol'].values()),10)
 def test_pins_and_no_changes(self):
  for p,h in read(CONTRACT)['sourcePins'].items():self.assertEqual(sha(p),h,p)
  for p,h in read(OUT/'manifest.json')['sha256'].items():self.assertEqual(sha(p),h,p)
  self.assertTrue(all(v==0 for v in self.d['counters'].values()))
  self.assertEqual(len(self.d['safety']),9);self.assertTrue(all(v is False for v in self.d['safety'].values()))
 def test_causal_projection_and_stop(self):
  forbidden=['mae','mfe','future','reclaim','pnl','outcome','label','exit']
  for r in self.d['rows']:
   self.assertFalse(any(any(f in name.lower() for f in forbidden) for name in r['x']))
  for k in ['modelFamilyFreeze','targetFreeze','featureFreeze','stateFreeze','numericCompletionGates']:self.assertIsNone(self.a[k])
  self.assertEqual(self.a['verdict'],'MSH_ENTRY_LONG_V2_ARCHITECTURE_DIAGNOSTIC_COMPLETE')
  self.assertEqual(self.d['inventoryCounts']['fullyPitCertifiedForDeployment'],0)
  self.assertIn('futureAvailabilityMembership',self.d['inheritedSourceAudit'])
 def test_reproduce_without_model_runtime(self):
  with tempfile.TemporaryDirectory() as td:
   with contextlib.redirect_stdout(io.StringIO()):run(Path(td))
   # Compare semantic JSON: gzip header OS byte differs across supported Python3.12/3.13.
   self.assertEqual(read(Path(td)/'diagnostic.json.gz'),self.d)
   self.assertEqual(sha(Path(td)/'feature-inventory.json'),sha(OUT/'feature-inventory.json'))
 def test_future_bar_and_delayed_availability_cannot_enter_existing_features(self):
  code="""
import assert from 'node:assert/strict';
import {featureAudit} from './predict/long-only/phase57-long-only-entry-preimplementation-feasibility.js';
const t=m=>`2024-10-01T09:${String(m).padStart(2,'0')}:00+09:00`;
const bars=Array.from({length:7},(_,i)=>({timestamp:t(i*5),availableAt:t(i*5+5),open:100,high:120,low:99,close:101+i,volume:100+i}));
const args={bars,decisionTimestamp:t(35),sessionDate:'2024-10-01',rank:1,firstSelectionTimestamp:t(30),priorSelectionCount:1};
const a=featureAudit(args),b=featureAudit({...args,bars:[...bars,{timestamp:t(35),availableAt:t(40),open:900,high:999,low:899,close:998,volume:999999}]});
assert.deepEqual(a,b);
const delayed=bars.map((b,i)=>i===6?{...b,availableAt:t(36)}:b);
assert.equal(featureAudit({...args,bars:delayed}).directionalMomentum3Pct.status,'BLOCKED_BY_GRID');
"""
  subprocess.run(['node','--input-type=module','-e',code],check=True,capture_output=True,text=True)
 def test_inherited_future_membership_limit_is_real(self):
  code="""
import assert from 'node:assert/strict';
import {buildL1CrossSectionDataset as build} from './predict/long-only/phase57-long-only-l1-cross-section.js';
const date='2024-10-01';const bar=(s,e)=>({sessionDate:date,symbol:'TEST',barStartJst:date+'T'+s+':00+09:00',availableAtJst:date+'T'+e+':00+09:00',open:100,high:101,low:99,close:100,volume:100,turnover:10000});
const input={partition:'DEVELOPMENT_A',dailyRows:[{sessionDate:date,symbol:'TEST',segment:'STANDARD',adjustedPreviousClose:100,adjustedClose:100,unadjustedClose:100,adjustmentScale:1,corporateActionFlag:false}],terminalAuctions:[]};
const prefix=[bar('09:25','09:30')];
assert.equal(build({...input,bars5m:prefix}).featureRows.length,0);
assert.ok(build({...input,bars5m:[...prefix,bar('09:30','09:35')]}).featureRows.some(r=>r.decisionTimeJst==='09:30'));
"""
  subprocess.run(['node','--input-type=module','-e',code],check=True,capture_output=True,text=True)
if __name__=='__main__':unittest.main()
