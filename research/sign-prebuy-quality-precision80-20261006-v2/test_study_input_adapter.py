"""The adapter may not cherry-pick missing State or unavailable fills."""
from copy import deepcopy
import hashlib
import unittest
import numpy as np
from study_input_adapter import adapt_row,FIELDS


def sample():
    columns=['p0/clockMinute']+['p0/fixture'+str(i) for i in range(109)]
    numeric=dict.fromkeys(columns);numeric['p0/clockMinute']=600.
    arr=np.asarray([600.]+[np.nan]*109,np.float64)
    schema={'BASE':{'numeric':columns},'STRUCTURE':{'numeric':columns,'categorical':['source_status']}}
    row={'entry_id':'2025-08-25|SYNTHETIC','session':'2025-08-25','intent_minute':600,
         'intent_timestamp':'2025-08-25T10:00:00+09:00','numeric':numeric,'categorical':{'source_status':'SOURCE_UNAVAILABLE'},
         'source_status':'SOURCE_UNAVAILABLE','execution_eligible':False,'quality':{'current_observed':False},
         'provenance':{'cutoff_basis':'FROZEN_FIRST_INTENT','cutoff_minute':600,'original_row_id':'2025-08-25|SYNTHETIC|600',
                       'original_row_index':1,'p0_snapshot_hash':hashlib.sha256(arr.tobytes()).hexdigest(),'max_known_minute':None}}
    return row,schema


class AdapterTests(unittest.TestCase):
    def test_unavailable_state_and_ineligible_fill_do_not_reject_entry(self):
        row,schema=sample();out=adapt_row(row,schema)
        self.assertTrue(out['supported']);self.assertEqual(set(out),FIELDS)
        self.assertEqual(out['input_asof'],row['intent_timestamp'])
        self.assertEqual(out['numeric'],row['numeric'])
        self.assertEqual(out['categorical'],row['categorical'])

    def test_no_market_quality_or_teacher_metadata_enters_x(self):
        row,schema=sample();row['future_evaluator']='POISON';row['quality']['future_evaluator']='POISON'
        out=adapt_row(row,schema)
        self.assertEqual(set(out),FIELDS)
        self.assertNotIn('future_evaluator',out)
        self.assertNotIn('execution_eligible',out)

    def test_future_state_endpoint_rejected(self):
        row,schema=sample();row['provenance']['max_known_minute']=601
        with self.assertRaisesRegex(ValueError,'AFTER_INTENT'):adapt_row(row,schema)

    def test_original_p0_and_identity_mutation_rejected(self):
        row,schema=sample();row['numeric']['p0/fixture1']=42.
        with self.assertRaisesRegex(ValueError,'P0_SNAPSHOT_HASH_MISMATCH'):adapt_row(row,schema)
        row,schema=sample();row['provenance']['original_row_id']='OTHER'
        with self.assertRaisesRegex(ValueError,'ORIGINAL_INTENT_IDENTITY'):adapt_row(row,schema)

    def test_mapping_copies_prevent_training_mutation_of_source(self):
        row,schema=sample();out=adapt_row(row,schema)
        out['numeric']['p0/fixture1']=123.
        self.assertIsNone(row['numeric']['p0/fixture1'])
        out['categorical']['source_status']='NEW'
        self.assertEqual(row['categorical']['source_status'],'SOURCE_UNAVAILABLE')

if __name__=='__main__':unittest.main()
