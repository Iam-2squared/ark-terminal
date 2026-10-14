import copy,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from preopen_state_source import admitted_previous_state
from preopen_io import write_json
from preopen_selector import PreopenError


class PriorStateLineage(unittest.TestCase):
    def setup_store(self,root,row):
        entry=write_json(root/'states.json',{'schema':'ARK_PREOPEN_PRIOR_STATE_LEDGER_V1','rows':[row]})
        return SimpleNamespace(private_root=root,sources_by_hash={'1'*64:{}},
            request={'previousStateContract':{'reviewed':True,'evidenceReference':'FROZEN_RC2_ORIGINAL_HASHES',
                'cutoffPolicy':'D_MINUS_1_CONTINUOUS_CLOSE_FORMAL_OBSERVED','ledger':entry,
                'contractSha256':'2'*64,'artifactSha256':'3'*64,'profileSha256':'4'*64}})

    def row(self):
        return {'session':'2024-11-13','symbol':'13010','primary':'RISE','formalObserved':True,
                'knownAt':'2024-11-13T16:30:00+09:00','observedAt':'2024-11-13T15:25:00+09:00',
                'sourceHashes':['1'*64],'upstreamLineage':{'requiresFit':False,
                  'kind':'DETERMINISTIC_FROZEN_RULES','profileSha256':'4'*64,
                  'contractSha256':'2'*64,'artifactSha256':'3'*64}}

    def test_deterministic_frozen_rules_need_no_fabricated_fit_period(self):
        with tempfile.TemporaryDirectory() as t:
            store=self.setup_store(Path(t),self.row())
            state,reason=admitted_previous_state(store,'2024-11-13','13010','2024-11-14')
            self.assertEqual(state['primary'],'RISE');self.assertIsNone(reason)

    def test_carried_display_and_future_fitted_profile_are_not_formal_observation(self):
        with tempfile.TemporaryDirectory() as t:
            row=self.row();row['formalObserved']=False;row['missingReason']='CARRIED_NOT_OBSERVED'
            store=self.setup_store(Path(t),row)
            self.assertEqual(admitted_previous_state(store,'2024-11-13','13010','2024-11-14'),
                             (None,'CARRIED_NOT_OBSERVED'))
        with tempfile.TemporaryDirectory() as t:
            row=self.row();row['upstreamLineage'].update(requiresFit=True,lastFitSession='2025-01-01')
            store=self.setup_store(Path(t),row)
            with self.assertRaisesRegex(PreopenError,'FUTURE_UPSTREAM_FIT'):
                admitted_previous_state(store,'2024-11-13','13010','2024-11-14')

    def test_unmounted_or_other_manifest_state_cannot_be_silently_admitted(self):
        with tempfile.TemporaryDirectory() as t:
            row=self.row();row['sourceHashes']=['9'*64];store=self.setup_store(Path(t),row)
            with self.assertRaisesRegex(PreopenError,'SOURCE_NOT_IN_ADMITTED'):
                admitted_previous_state(store,'2024-11-13','13010','2024-11-14')


if __name__=='__main__':unittest.main()
