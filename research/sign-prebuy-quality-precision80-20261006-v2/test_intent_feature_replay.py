"""Meaningful synthetic clock, suffix, reset and original-source tests."""
from copy import deepcopy
import hashlib
import unittest
import numpy as np
import intent_feature_replay as replay


def fixture():
    replay.initialize()
    day='2025-08-25';key=day+'|SYNTHETIC';cutoff=580
    clock=lambda d,t:d+f'T{t//60:02d}:{t%60:02d}:00+09:00'
    intent={'intent_minute':cutoff,'intent_timestamp':clock(day,cutoff),'row_id':key+'|580',
            'row_index':123,'score':.8,'threshold':.7}
    entry={'watch_key':key,'session':day,'symbol':'SYNTHETIC','first_intent':intent,
           'selector_minute':550,'selector_to_intent_active_delay':30}
    nums={'p0/'+name:None for name in replay._KERNEL.P0_NAMES if name not in ('clockMinute','activeMinutesSinceSelector')}
    nums.update({'entry/intent_clock':cutoff,'selector/to_intent_active_delay':30})
    values=[cutoff if name=='clockMinute' else 30 if name=='activeMinutesSinceSelector' else None for name in replay._KERNEL.P0_NAMES]
    matrix=np.asarray([np.nan if v is None else float(v) for v in values],np.float64)
    runtime={'entry_id':key,'session':day,'symbol':'SYNTHETIC','numeric':nums,'categorical':{},
             'p0_snapshot_hash':hashlib.sha256(matrix.tobytes()).hexdigest(),
             'p0_snapshot_row_id':intent['row_id'],'p0_snapshot_row_index':123,
             'execution_eligible':False}
    today=[[540+i,100+i*.25,100.3+i*.25,99.9+i*.25,100.2+i*.25,100,10002] for i in range(40)]
    previous=[];native=[]
    for i in range(40):
        price=100+i*.01;m=540+i
        previous.append([m,price,price+.1,price-.1,price+.02,100,10000])
        native.append({'Date':'2025-08-22','Time':f'{m//60:02d}:{m%60:02d}',
                       'O':str(price),'H':str(price+.1),'L':str(price-.1),'C':str(price+.02),
                       'Vo':'100','Va':'10000','_source':str(i)})
    raw={'today':today,'previous':previous}
    source={'previous':native,'previous_daily':{'AdjFactor':'1','ExRT':None},'previous_session':'2025-08-22'}
    return (0,entry,runtime,raw,source)


class ForbiddenFutureRow(list):
    def __getitem__(self,index):
        if index!=0:raise AssertionError('future market field inspected')
        return super().__getitem__(index)


class IntentReplayTests(unittest.TestCase):
    def test_suffix_market_values_never_accessed_and_output_invariant(self):
        job=fixture();a=replay.one_replay(job)
        changed=deepcopy(job)
        changed[3]['today'].extend([ForbiddenFutureRow([580]),ForbiddenFutureRow([600])])
        b=replay.one_replay(changed)
        self.assertEqual(a,b)
        self.assertLessEqual(a['provenance']['max_known_minute'],580)

    def test_future_price_extremes_and_later_pm_do_not_change_intent(self):
        job=fixture();a=replay.one_replay(job)
        changed=deepcopy(job)
        changed[3]['today'].extend([[580,1e8,1e9,.01,1e7,1e9,1e12],[750,1e-8,1e-7,1e-9,1e-8,1,1]])
        b=replay.one_replay(changed)
        self.assertEqual(a['numeric'],b['numeric'])
        self.assertEqual(a['categorical'],b['categorical'])
        self.assertEqual(a['provenance']['prefix_sha256'],b['provenance']['prefix_sha256'])

    def test_p0_snapshot_hash_and_original_columns_preserved(self):
        job=fixture();out=replay.one_replay(job)
        self.assertEqual(out['numeric']['p0/clockMinute'],580.)
        self.assertEqual(out['numeric']['p0/activeMinutesSinceSelector'],30.)
        self.assertIsNone(out['numeric']['p0/return20'])
        changed=deepcopy(job);changed[2]['numeric']['p0/return20']=99.
        with self.assertRaisesRegex(ValueError,'P0_SNAPSHOT_HASH_MISMATCH'):replay.one_replay(changed)

    def test_scheduled_missing_minute_remains_gap_and_resets(self):
        job=fixture();job[3]['today']=[r for r in job[3]['today'] if r[0]!=566]
        out=replay.one_replay(job)
        self.assertGreater(out['numeric']['projection/path/segment_breaks_total'],0)
        self.assertGreater(out['numeric']['projection/path/observation_losses_total'],0)
        self.assertLess(out['quality']['connected_prefix_rows'],40)
        self.assertEqual(out['provenance']['state_reader_receipt']['kernel_steps'],40)

    def test_noncontinuous_previous_basis_remains_unavailable(self):
        job=fixture();job[4]['previous_daily']['AdjFactor']='.5'
        out=replay.one_replay(job)
        self.assertEqual(out['source_status'],'SOURCE_UNAVAILABLE')
        self.assertIsNone(out['numeric']['state/close_u'])
        self.assertEqual(out['categorical']['source_status'],'SOURCE_UNAVAILABLE')
        self.assertFalse(out['quality']['current_observed'])
        self.assertEqual(out['provenance']['state_reader_receipt']['kernel_steps'],0)

    def test_original_full_grid_and_single_intent_have_same_state_history(self):
        job=fixture();out=replay.one_replay(job)
        _,entry,runtime,raw,source=job
        watch={'watch_key':entry['watch_key'],'session':entry['session'],
               'selector_minute':entry['selector_minute'],'selector_price':100.,'refresh_minutes':[550]}
        _,num,cat,meta,receipt=replay._KERNEL.state_task((0,watch,raw,source))
        for name,value in zip(replay._KERNEL.P1_NUM,num[-1,110:]):
            expected=None if np.isnan(value) else float(value)
            self.assertEqual(out['numeric'][name],expected)
        self.assertEqual([out['categorical'][k] for k in replay._KERNEL.P1_CAT],cat[-1])
        self.assertEqual(receipt['kernel_steps'],out['provenance']['state_reader_receipt']['kernel_steps'])

    def test_source_imports_and_monkey_patch_are_restored(self):
        job=fixture();replay.one_replay(job)
        self.assertIs(replay._KERNEL.Engine,replay._ORIGINAL_ENGINE)
        self.assertIs(replay._KERNEL.PathBuilder,replay._ORIGINAL_PATH)
        self.assertIs(replay._KERNEL.compute,replay._ORIGINAL_COMPUTE)

    def test_schema_keeps_all_original_fields_and_unique_structure(self):
        fixture();schema=replay.schema(replay._KERNEL)
        self.assertEqual(len(schema['BASE']['numeric']),151)
        self.assertEqual(len(schema['BASE']['categorical']),15)
        self.assertEqual(len(schema['STRUCTURE']['numeric']),191)
        self.assertEqual(len(schema['STRUCTURE']['categorical']),22)
        self.assertEqual(len(set(schema['STRUCTURE']['numeric'])),191)
        self.assertFalse(schema['fit_allowed'])
        self.assertFalse(schema['full_original_matrix_byte_parity_claimed'])

if __name__=='__main__':unittest.main()
