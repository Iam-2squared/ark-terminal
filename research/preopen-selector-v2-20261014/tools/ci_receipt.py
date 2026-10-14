"""Print a non-reconstructive receipt binding only THIS dedicated job and head."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from ark_selector_v2.contracts import code_hash,digest,registry

parser=argparse.ArgumentParser()
parser.add_argument('--head',required=True)
parser.add_argument('--run',required=True)
parser.add_argument('--event',required=True)
parser.add_argument('--synthetic-receipt',required=True)
args=parser.parse_args()
receipt=json.loads(Path(args.synthetic_receipt).read_text())
assert receipt['code_hash']==code_hash()
assert receipt['schema_hash']==digest(registry())
assert receipt['synthetic_budget_used']=={'base_fits':2,'calibration_optimizations':2}
assert receipt['market_estimator_fits']==receipt['market_calibration_optimizations']==0
assert receipt['separate_train_forecast_evaluate_processes'] is True
assert receipt['restore_prediction_max_abs_diff']==0
print(json.dumps({'schema':'ARK_V2_CURRENT_HEAD_CI_RECEIPT_V1','workflow':'Preopen Selector V2 - Synthetic Only',
                  'event':args.event,'head_sha':args.head,'run_id':args.run,'code_hash':code_hash(),
                  'feature_schema_hash':digest(registry()),'engineering':'PASS','market_fits':0,
                  'productionReady':False},sort_keys=True))
