import json
import sys
import tempfile
import unittest
from pathlib import Path
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from test_native_completion import fixture
from preopen_native_source import NativeStore
from preopen_build_cache import install_build_cache,indexed_read_copies
from build_preopen_native_bundle import snapshot_rows,features_with_source_metadata
from preopen_io import sha_file
from preopen_selector import PreopenError
from run_preopen_selector import preflight_bundle,training_binding


CALENDAR=['2024-10-01','2024-10-02','2024-10-03','2024-10-04',
          '2024-10-07','2024-10-08','2024-10-09','2024-10-10']


class CausalReadCache(unittest.TestCase):
    def test_market_train_and_predict_reject_report_label_inputs_before_open(self):
        from preopen_selector import CONTRACT
        bundle={'contract':CONTRACT,'plan':{'mode':'AUTHORIZED_DEVELOPMENT'},
                'inputs':{'report_labels':{'path':'/unmounted/report-labels.json'}}}
        for stage in ('train','predict'):
            with self.assertRaisesRegex(PreopenError,'REPORT_LABEL_INPUTS_FORBIDDEN'):
                preflight_bundle(bundle,Path('/unmounted/output'),stage=stage)

    def test_training_binding_checks_learning_inputs_after_report_is_added(self):
        bundle={'contract':'TEST','privateRoot':'/private','plan':{'split':'FIXED'},
                'sourceRequestHash':'1'*64,'inputs':{'fit_snapshots':{'sha256':'2'*64}}}
        expected=training_binding(bundle)
        bundle['trainingBindingHash']=expected
        bundle['inputs']['report_labels']={'sha256':'3'*64}
        self.assertEqual(training_binding(bundle),expected)
        bundle['inputs']['fit_snapshots']['sha256']='4'*64
        with self.assertRaisesRegex(PreopenError,'TRAINING_BINDING_HASH_DRIFT'):
            training_binding(bundle)

    def mounted(self,root):
        request=fixture(root);request['exchangeSessions']=CALENDAR
        store=NativeStore(root/'source',private_root=root,request=request)
        for source in request['sources']:store.ingest(source)
        return request,store

    def test_complete_snapshots_features_and_missingness_equal_uncached_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            request,store=self.mounted(Path(tmp))
            dates=['2024-10-08','2024-10-09','2024-10-10']
            expected=list(snapshot_rows(store,dates,CALENDAR,Counter()))
            rows=[features_with_source_metadata(r) for r in expected]
            install_build_cache(store,CALENDAR)
            actual=list(snapshot_rows(store,dates,CALENDAR,Counter()))
            self.assertEqual(expected,actual)
            self.assertEqual(rows,[features_with_source_metadata(r) for r in actual])
            earlier=list(snapshot_rows(store,[dates[0]],CALENDAR,Counter()))
            self.assertEqual(earlier,expected[:45])
            store.close()

    def test_later_history_extends_by_closed_sessions_without_future_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            request,store=self.mounted(Path(tmp));cache=install_build_cache(store,CALENDAR)
            first=cache.daily_history('10000','2024-10-08')
            self.assertEqual(first[-1]['Date'],'2024-10-07')
            calls=[];reader=cache.reader
            def guarded(dataset,**kwargs):
                calls.append(kwargs)
                if dataset=='DAILY':self.assertIsNone(kwargs.get('before'))
                yield from reader(dataset,**kwargs)
            cache.reader=guarded
            later=cache.daily_history('10000','2024-10-10')
            self.assertEqual([r['Date'] for r in later],CALENDAR[:-1])
            self.assertEqual([r['session'] for r in calls],['2024-10-08','2024-10-09'])
            store.close()

    def test_changed_price_identity_is_rejected_and_partial_null_is_not_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            request,store=self.mounted(Path(tmp));cache=install_build_cache(store,CALENDAR)
            raw=next(store.records('DAILY',code='10000',session='2024-10-01'))
            cache.price(raw)
            with self.assertRaisesRegex(PreopenError,'IMMUTABLE_PRICE_RECORD_CHANGED'):
                cache.price({**raw,'Va':None})
            with self.assertRaisesRegex(PreopenError,'PARTIAL_NULL'):
                cache.price({**raw,'_ordinal':99999,'Va':None})
            store.close()

    def test_index_copy_keeps_original_hash_and_logical_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);request,store=self.mounted(root);store.close()
            original=root/'source/sources.sqlite';before=sha_file(original)
            output=root/'output';output.mkdir()
            directory,new_request,entry=indexed_read_copies(root/'source',request,output)
            self.assertEqual(before,sha_file(original))
            derived=NativeStore(directory,private_root=root,request=new_request)
            other=NativeStore(root/'source',private_root=root,request=request)
            self.assertEqual(list(other.records('DAILY',session='2024-10-07')),
                             list(derived.records('DAILY',session='2024-10-07')))
            self.assertTrue(json.loads(Path(entry['path']).read_text())['databases'][0]['logicalSourceRecordsChanged'] is False)
            derived.close();other.close()


if __name__=='__main__':unittest.main()
