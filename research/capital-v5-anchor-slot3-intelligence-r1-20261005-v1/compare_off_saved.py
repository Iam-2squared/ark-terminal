"""Independent saved-ledger OFF comparison. Never imports/executes a replay."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from decimal import Decimal
from collections import Counter
import argparse,gzip,json,hashlib,math

PROFILE='CAPITAL_MAX3_SLOT_RESERVE_V1'
MONETARY={'cash','equity','exposure','starting_cash','ending_cash','cash_min','debit','credit','pnl',
 'buy_effective','sell_effective','raw_reference','recycled_cash_used','equity_cap','lot_debit','desired',
 'batch_equity','batch_budget','budget_unspent','native_debit','native_would_fund_debit'}
# Only fixed score/continuous native gate fields inherit the saved V5 1e-12
# inference tolerance. Money, quantity, IDs, ratios, summaries are exact here.
SCORE_FLOATS={'ML','capital_score','m2','m3','m5','p2','p3','p5','training_B_median','training_B_p75',
 'remaining_Aplus_probability','remaining_Aplus_ge2_probability','expected_remaining_Aplus'}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def rows(p):
    with gzip.open(p,'rt') as f:return [json.loads(line) for line in f if line.strip()]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--actual-dir',default='/workspace/scratch/f3d0aa747c89/r1_work/runs/OFF_PRIMARY')
    parser.add_argument('--native-dir',default='/workspace/scratch/f3d0aa747c89/r1_work/inputs/v5/capital_v5_slot_private')
    parser.add_argument('--output',default='/workspace/scratch/f3d0aa747c89/r1_work/spec_review/OFF_INDEPENDENT_SAVED_COMPARISON.json')
    args=parser.parse_args();actual=Path(args.actual_dir);native=Path(args.native_dir);out=Path(args.output)
    assert not out.exists(),'IMMUTABLE_COMPARISON_RECEIPT_EXISTS'
    for p in [actual/'COMPLETE.json',actual/'RESULT.json',native/f'{PROFILE}_RESULT.json']:
        assert p.exists(),str(p)
    complete=read(actual/'COMPLETE.json');assert complete['arm']=='OFF' and complete['replay_count']==1
    failures=[];checks=Counter();extras=Counter();tolerated=[]
    def compare(expected,observed,path,category):
        key=path[-1] if path else ''
        if isinstance(expected,dict):
            checks[category+'/dict']+=1
            if not isinstance(observed,dict):failures.append({'path':path,'reason':'TYPE_EXPECTED_DICT'});return
            for k,v in expected.items():
                if k not in observed:failures.append({'path':path+[k],'reason':'MISSING_ORIGINAL_FIELD'});continue
                compare(v,observed[k],path+[k],category)
            for k in set(observed)-set(expected):extras[category+'/'+k]+=1
        elif isinstance(expected,list):
            checks[category+'/list']+=1
            if not isinstance(observed,list):failures.append({'path':path,'reason':'TYPE_EXPECTED_LIST'});return
            if len(expected)!=len(observed):failures.append({'path':path,'reason':'ROW_COUNT','expected':len(expected),'observed':len(observed)})
            for i,(a,b) in enumerate(zip(expected,observed)):compare(a,b,path+[i],category)
        else:
            checks[category+'/scalar']+=1
            # Preserve bool/null types and identity strings without coercion.
            if isinstance(expected,bool) or expected is None:
                match=observed is expected
            elif key in MONETARY:
                try:match=Decimal(str(expected))==Decimal(str(observed))
                except Exception:match=False
            elif isinstance(expected,float):
                if not isinstance(observed,(int,float)) or isinstance(observed,bool):match=False
                elif not math.isfinite(expected) or not math.isfinite(float(observed)):match=False
                elif expected==observed:match=True
                elif key in SCORE_FLOATS:
                    delta=abs(expected-observed);match=delta<=1e-12
                    if match:tolerated.append({'path':path,'delta':delta,'fixed_tolerance':1e-12})
                else:match=False
            else:match=type(observed) is type(expected) and observed==expected
            if not match:failures.append({'path':path,'reason':'VALUE_MISMATCH','expected':expected,'observed':observed})

    artifacts={};ledger_map={'DECISIONS':'DECISIONS','TRADES':'TRADES','CURVE':'CURVES','INTENTS':'INTENTS'}
    for label,actual_label in ledger_map.items():
        expected_path=native/f'{PROFILE}_{label}.jsonl.gz';observed_path=actual/f'{actual_label}.jsonl.gz'
        expected=rows(expected_path);observed=rows(observed_path)
        compare(expected,observed,[label],label)
        artifacts[label]={'original_rows':len(expected),'actual_rows':len(observed),'original_sha256':sha(expected_path),'actual_sha256':sha(observed_path)}
    saved=read(native/f'{PROFILE}_RESULT.json');observed=read(actual/'RESULT.json')
    compare(saved,observed,['RESULT'],'RESULT')
    compare(saved['daily_series'],rows(actual/'DAILY.jsonl.gz'),['DAILY'],'DAILY')

    # Independently derive exact paired window ratios and Slot1/2/3 identities
    # directly from saved/current records. No float display gate or reset paths.
    from fractions import Fraction
    old_daily=saved['daily_series'];new_daily=rows(actual/'DAILY.jsonl.gz')
    exact_windows=[]
    if len(old_daily)==len(new_daily)==38:
        for i in range(19):
            a,z=old_daily[i:i+20],new_daily[i:i+20]
            old_id=(a[0]['session'],a[-1]['session']);new_id=(z[0]['session'],z[-1]['session'])
            old_growth=Fraction(Decimal(a[-1]['ending_cash']))/Fraction(Decimal(a[0]['starting_cash']))
            new_growth=Fraction(Decimal(z[-1]['ending_cash']))/Fraction(Decimal(z[0]['starting_cash']))
            checks['exact_rolling20']+=1
            if old_id!=new_id or old_growth!=new_growth:failures.append({'path':['exact_rolling20',i],'reason':'EXACT_WINDOW_MISMATCH'})
            exact_windows.append({'start_session':old_id[0],'end_session':old_id[1],'numerator':old_growth.numerator,'denominator':old_growth.denominator,'actual_exact_match':old_id==new_id and old_growth==new_growth})
    else:failures.append({'path':['daily'],'reason':'FULL38_REQUIRED'})
    od=rows(native/f'{PROFILE}_DECISIONS.jsonl.gz');nd=rows(actual/'DECISIONS.jsonl.gz')
    slot_identities={}
    for slot in (1,2,3):
        a=[r['entry_id'] for r in od if r['reason']=='FUNDED' and r.get('funded_slot')==slot]
        b=[r['entry_id'] for r in nd if r['reason']=='FUNDED' and r.get('funded_slot')==slot]
        checks['funded_slot_identity']+=1
        if a!=b:failures.append({'path':['slot_ids',slot],'reason':'FUNDED_IDENTITY_MISMATCH'})
        slot_identities[str(slot)]={'N':len(a),'identities':a,'ordered_identity_exact':a==b}
    for key,item in complete['artifacts'].items():
        p=Path(item['path']);checks['complete_receipt_artifact_hash']+=1
        expected=item.get('sha256',item.get('compressed_sha256'))
        if sha(p)!=expected:failures.append({'path':['COMPLETE',key],'reason':'ARTIFACT_HASH_MISMATCH'})
    report={'schema':'R1_OFF_INDEPENDENT_SAVED_LEDGER_COMPARISON_V1','JST':datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(),
      'status':'PASS' if not failures else 'FAIL','original_missing_fields_permitted':False,'original_money_and_quantity_tolerance':0,
      'native_score_float_tolerance':1e-12,'other_FLOAT_SUMMARY_comparison':'exact; original function/source inputs unchanged',
      'mismatch_N':len(failures),'mismatch':failures,'check_N':sum(checks.values()),'checks':dict(checks),'additional_diagnostic_fields_ignored':dict(extras),
      'score_tolerance_used_N':len(tolerated),'score_tolerated_deltas':tolerated,'artifacts':artifacts,'exact_paired19_windows':exact_windows,'slot_identity':slot_identities,
      'result_original_sha256':sha(native/f'{PROFILE}_RESULT.json'),'result_actual_sha256':sha(actual/'RESULT.json'),
      'complete_receipt_sha256':sha(actual/'COMPLETE.json'),'comparator_code_sha256':sha(__file__),
      'counts':{'OFFReplaysByComparator':0,'candidateReplaysByComparator':0,'newFits':0,'modelInference':0,'scorePnLJoins':0,'protectedOpened':0},
    }
    with out.open('x') as f:json.dump(report,f,sort_keys=True,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({'status':report['status'],'mismatch_N':len(failures),'check_N':sum(checks.values()),'first_mismatches':failures[:3]}))
    if failures:raise SystemExit(1)

if __name__=='__main__':main()
