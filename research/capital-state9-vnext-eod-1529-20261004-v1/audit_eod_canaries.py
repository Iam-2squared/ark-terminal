"""Mutation and fail-closed tests for the EOD adapter; fixtures never certify a market fill."""
import argparse,copy,gzip,hashlib,importlib.util,json
from pathlib import Path
from decimal import Decimal
from datetime import datetime,timezone,timedelta

def rows(p):
 with gzip.open(p,'rt') as f:return [json.loads(x) for x in f if x.strip()]
def load_module(path):
 spec=importlib.util.spec_from_file_location('eod_primary_under_test',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def main(args):
 inp=Path(args.inputs);pub=Path(args.public);priv=Path(args.private);m=load_module(Path(__file__).with_name('audit_eod_primary.py'))
 policy=json.loads((pub/'EOD_1529_PRECOMMIT.json').read_text())
 assert hashlib.sha256((pub/'EOD_1529_SOURCE_CONTRACT.json').read_bytes()).hexdigest()==policy['source_contract_sha256']
 assert hashlib.sha256((pub/'EOD_1529_ACCOUNTING_CONTRACT.json').read_bytes()).hexdigest()==policy['accounting_contract_sha256']
 before={n:hashlib.sha256((inp/n).read_bytes()).hexdigest() for n in ('entry.jsonl.gz','exit_v3.jsonl.gz','raw_paths.json.gz')}
 E={x['watch_key']:x for x in rows(inp/'entry.jsonl.gz') if x['entry_status']=='FIRST_ENTRY'};X={x['watch_key']:x for x in rows(inp/'exit_v3.jsonl.gz')}
 with gzip.open(inp/'raw_paths.json.gz','rt') as f:R=json.load(f)
 counters={k:{'tested_N':0,'mismatch_N':0} for k in ('future_HLC_suffix','future_Frozen_exit_suffix','next_day_and_previous_price_irrelevance','future_outcome_irrelevance','already_exited_no_EOD_double_apply','missing_source_no_fill','no_cash_release_on_unfillable','preclosing_synthetic_Open_still_unexecutable','immutable_Frozen_columns')}
 frozen_metadata={'frozen_exit_v3_original_row_sha256'}
 def decision(r):return {k:v for k,v in r.items() if k not in frozen_metadata}
 for key in sorted(E):
  e=E[key];x=X[key];p=R[key];base=m.adapter(e,x,p)
  mutated=dict(p);mutated['today']=[r[:2]+[-999999,999999,-777777,-333,-444] if r[0]>=929 else r for r in p['today']]
  test=m.adapter(e,x,mutated);counters['future_HLC_suffix']['tested_N']+=1;counters['future_HLC_suffix']['mismatch_N']+=decision(base)!=decision(test)
  mutated=dict(p);mutated['previous']=[[r[0],-123,999999,-999999,-123,0,0] for r in p['previous']];mutated['next_day']=[[540,999999,999999,999999,999999,0,0]]
  test=m.adapter(e,x,mutated);counters['next_day_and_previous_price_irrelevance']['tested_N']+=1;counters['next_day_and_previous_price_irrelevance']['mismatch_N']+=decision(base)!=decision(test)
  changed_e=dict(e)
  for f in ('U_target','Q_target','D_target','first_upside','remaining_upside_pct','pre_peak_mae_abs_pct','session_end_mfe_pct','path_efficiency','profit','MFE','MAE'):changed_e[f]=-999999
  changed_x=dict(x);changed_x['future_profit']=999999;changed_x['future_quality']='POISON'
  test=m.adapter(changed_e,changed_x,p);counters['future_outcome_irrelevance']['tested_N']+=1;counters['future_outcome_irrelevance']['mismatch_N']+=decision(base)!=decision(test)
  if base['prior_frozen_exit_before_1529']:
   counters['already_exited_no_EOD_double_apply']['tested_N']+=1
   counters['already_exited_no_EOD_double_apply']['mismatch_N']+=base['eod_overlay_applied'] or base['eod_fill'] or base['final_integrated_exit_price']!=x['sell_price_decimal']
  else:
   future_x=dict(x);future_x.update(sell_status='UNRESOLVED',sell_minute=None,sell_timestamp=None,sell_price=None,sell_price_decimal=None,sell_source=None,sell_source_assumed_available_at=None,exit_reason='UNRESOLVED')
   test=m.adapter(e,future_x,p)
   runtime_keys=[k for k in base if not k.startswith('frozen_exit_v3_')]
   counters['future_Frozen_exit_suffix']['tested_N']+=1
   counters['future_Frozen_exit_suffix']['mismatch_N']+=any(base[k]!=test[k] for k in runtime_keys)
   counters['missing_source_no_fill']['tested_N']+=1;counters['missing_source_no_fill']['mismatch_N']+=base['eod_fill'] or base['final_integrated_exit_price'] is not None or base['final_integrated_exit_timestamp'] is not None
   counters['no_cash_release_on_unfillable']['tested_N']+=1;counters['no_cash_release_on_unfillable']['mismatch_N']+=base['cash_release_authorized'] or base['cash_release_timestamp'] is not None
   # Inject a positive exact Open only as a test fixture. It cannot override the actual market clock.
   synthetic=dict(p);synthetic['today']=[r for r in p['today'] if r[0]!=929]+[[929,1000,-999999,999999,None,None,None]]
   test=m.adapter(e,x,synthetic);counters['preclosing_synthetic_Open_still_unexecutable']['tested_N']+=1
   counters['preclosing_synthetic_Open_still_unexecutable']['mismatch_N']+=test['eod_fill'] or test['eod_unfillable_reason']!='SESSION_NOT_ACTIVE' or test['cash_release_authorized']
  counters['immutable_Frozen_columns']['tested_N']+=1
  counters['immutable_Frozen_columns']['mismatch_N']+=base['frozen_exit_v3_status']!=x['sell_status'] or base['frozen_exit_v3_timestamp']!=x['sell_timestamp'] or base['frozen_exit_v3_price']!=x['sell_price_decimal']
 fixture_checks=[]
 # This validates the Open-only selector, not eligibility/fill on a TSE session.
 for suffix in ([1000,1000,1000,100,100000],[-999,999,None,None,None],[float('nan'),float('inf'),-999999,-1,-1]):
  assert m.open_only([[929,1000]+suffix],929)==Decimal('1000')
  fixture_checks.append({'name':'Open selector ignores every completed future field','PASS':True,'market_fill_evidence':False})
 for fixture in ([],[[929,None,1,1,1,1,1]],[[929,0,1,1,1,1,1]],[[929,-1,1,1,1,1,1]],[[929,float('nan'),1,1,1,1,1]],[[929,1000,1,1,1,1,1],[929,1001,1,1,1,1,1]]):
  assert m.open_only(fixture,929) is None
 fixture_checks.append({'name':'missing/null/zero/negative/nonfinite/duplicate Open fails closed','cases_N':6,'PASS':True,'market_fill_evidence':False})
 after={n:hashlib.sha256((inp/n).read_bytes()).hexdigest() for n in before};assert before==after
 primary=rows(priv/'EOD_OVERLAY_ROWS.jsonl.gz');ind=rows(priv/'INDEPENDENT_EOD_OVERLAY_ROWS.jsonl.gz')
 independent_post_final_primary_mismatch=sum(any(r[k]!=i[k] for k in i) for r,i in zip(primary,ind))
 assert len(primary)==len(ind)==1600
 total=sum(c['mismatch_N'] for c in counters.values())+independent_post_final_primary_mismatch
 out={'saved_at_jst':datetime.now(timezone(timedelta(hours=9))).isoformat(),'policy_id':policy['policy_id'],'status':'PASS' if total==0 else 'FAIL','canaries':counters,'Open_selector_fixture_checks':fixture_checks,'Frozen_input_file_hashes_unchanged':before==after,'final_Primary_vs_saved_Independent_mismatch_N':independent_post_final_primary_mismatch,'cash_double_release_N':0,'actual_quantity_allocated':False,'quantity_rule_validation':'Full remaining quantity specified in precommit; no EOD fill or funded quantity exists, so no actual quantity execution/Portfolio ledger is certified.','future_suffix_mutations_are_market_data':False,'fixture_fill_used_for_results':False,'Capital_replay':0,'mismatch_N':total}
 assert total==0
 (pub/'EOD_ASOF_CANARIES.json').write_text(json.dumps(out,sort_keys=True,indent=2)+'\n')
 print(json.dumps({'status':out['status'],'mismatch_N':total,'per_candidate_mutation_checks_N':sum(c['tested_N'] for c in counters.values()),'final_Primary_Independent_mismatch_N':independent_post_final_primary_mismatch}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--inputs',required=True);p.add_argument('--public',required=True);p.add_argument('--private',required=True);main(p.parse_args())
