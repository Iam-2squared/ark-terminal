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
parser.add_argument('--native-receipt',required=True)
parser.add_argument('--monthly-receipt',required=True)
args=parser.parse_args()
receipt=json.loads(Path(args.synthetic_receipt).read_text())
assert receipt['code_hash']==code_hash()
assert receipt['schema_hash']==digest(registry())
assert receipt['synthetic_budget_used']=={'base_fits':2,'calibration_optimizations':2}
assert receipt['market_estimator_fits']==receipt['market_calibration_optimizations']==0
assert receipt['separate_train_forecast_evaluate_processes'] is True
assert receipt['restore_prediction_max_abs_diff']==0
native=json.loads(Path(args.native_receipt).read_text())
assert native['entrypoint']=='SIX_NORMAL_STAGE_CLI_SUBCOMMANDS_WITH_ISOLATED_HOST_AUTHORITY'
assert native['test_only'] is True and native['market_approval_established'] is False
assert native['code_hash']==code_hash() and native['schema_hash']==digest(registry())
assert native['isolated_fit_starts']==native['isolated_calibration_starts']==2
assert native['isolated_candidate_reservations']==1 and native['tree_count']==1080
assert native['restore_prediction_difference']==0
assert native['market_candidates']==native['market_fits']==native['market_calibrations']==0
monthly=json.loads(Path(args.monthly_receipt).read_text())
assert monthly['test_only'] is True and monthly['market_approval_established'] is False
assert monthly['code_hash']==code_hash() and monthly['schema_hash']==digest(registry())
assert monthly['separate_stage_processes']==6 and monthly['durable_independent_pin_count']>=40
assert monthly['isolated_fit_starts']==monthly['isolated_calibration_starts']==2
assert monthly['isolated_candidate_reservations']==1 and monthly['restore_prediction_difference']==0
assert monthly['market_candidates']==monthly['market_fits']==monthly['market_calibrations']==0
print(json.dumps({'schema':'ARK_V2_CURRENT_HEAD_CI_RECEIPT_V1','workflow':'Preopen Selector V2 - Synthetic Only',
                  'event':args.event,'head_sha':args.head,'run_id':args.run,'code_hash':code_hash(),
                  'feature_schema_hash':digest(registry()),'engineering':'PASS','native_route_test':'PASS','native_validation':native['validation_status'],'native_final':native['final_status'],'market_fits':0,
                  'monthly_host_test':'PASS','separate_monthly_stage_processes':6,'productionReady':False},sort_keys=True))
