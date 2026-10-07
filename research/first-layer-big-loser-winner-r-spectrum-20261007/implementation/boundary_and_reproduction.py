"""Finite artificial boundary tests and exactly one same-input reproduction run."""
import argparse
import importlib.util
import hashlib
import json
import subprocess
import sys
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    a=argparse.ArgumentParser();a.add_argument('--root',required=True);args=a.parse_args()
    root=Path(args.root);deliver=root/'r_spectrum_20261007';pub=deliver/'public';prv=deliver/'private'
    src=root/'inputs/c11_private_selected/c11/private';impl=deliver/'implementation'
    primary=module(impl/'census.py','primary_under_test')
    alternate=module(impl/'independent_audit.py','interval_under_test')
    cases=[];errors=[]
    expected={-5:['L5_PLUS','L5_PLUS','L4_5'],-4:['L4_5','L4_5','L3_4'],
        -3:['L3_4','L3_4','L2_3'],-2:['L2_3','L2_3','L1_2'],-1:['L1_2','L1_2','L0_1'],
        0:['L0_1','ZERO','P0_1'],1:['P0_1','P1_2','P1_2'],2:['P1_2','P2_3','P2_3'],
        3:['P2_3','P3_4','P3_4'],4:['P3_4','P4_5','P4_5'],5:['P4_5','P5_PLUS','P5_PLUS']}
    delta=Decimal('0.000000001')
    for n,labels in expected.items():
        for offset,label in zip([-delta,Decimal(0),delta],labels):
            value=Decimal(n)+offset
            p=primary.bucket(Fraction(value));q=alternate.independent_bin(value)
            ok=p==q==label
            cases.append({'synthetic_R_pct':str(value),'expected':label,'primary':p,'independent':q,'PASS':ok})
            if not ok:errors.append(cases[-1])
    nullcases=[(None,'NULL_R_NATIVE'),('NaN','NAN_R_NATIVE'),('not-a-number','INVALID_R_NATIVE'),('Infinity','NONFINITE_R_NATIVE')]
    for token,reason in nullcases:
        row={'return_available':True,'R_native_fraction_decimal':token,'R_pct_numerator':'0','R_pct_denominator':'1','R_unit':'percent'}
        p=primary.primary_R(row);q=alternate.independently_parse_native(row)
        ok=p==(None,reason) and q==(None,reason)
        cases.append({'synthetic_missing':token,'expected_reason':reason,'primary_reason':p[1],'independent_reason':q[1],'PASS':ok})
        if not ok:errors.append(cases[-1])
    row={'return_available':False,'R_native_fraction_decimal':None}
    p=primary.primary_R(row);q=alternate.independently_parse_native(row)
    ok=p==q==(None,'FORMAL_R_UNAVAILABLE_SOURCE_REASON_UNSPECIFIED')
    cases.append({'synthetic_formal_unavailable':True,'PASS':ok})
    if not ok:errors.append(cases[-1])
    ok=primary.bucket(None)==alternate.independent_bin(None)=='R_UNKNOWN'
    cases.append({'synthetic_unknown_exclusive':True,'PASS':ok})
    if not ok:errors.append(cases[-1])
    receipt={'status':'PASS' if not errors else 'FAIL','synthetic_boundary_values':33,'missing_or_invalid_cases':6,
        'implementation_checks':len(cases)*2,'mismatch_N':len(errors),'artificial_delta_percentage_points':'1e-9',
        'real_R_epsilon_added':False,'real_R_rounded_for_bucket':False,'cases':cases}
    (pub/'BOUNDARY_TESTS.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    if errors:raise SystemExit('ARTIFICIAL_BOUNDARY_FAILURE')
    files=['ENTRY_EXIT_R_DISTRIBUTION.csv','LEGACY_R_BAND_KEEP_DROP.csv','CUMULATIVE_LOSER_WINNER_KEEP_DROP.csv',
        'DROP_COMPOSITION.csv','RETURN_MASS_DECOMPOSITION.csv','ACCOUNTING_IDENTITY_CHECK.csv','ALL_KEEP_REFERENCE.csv',
        'CENSUS_SUMMARY.json','NEW_FIRST_LAYER_STATUS.json','MISSING_EVIDENCE.json']
    source_before={str(p.relative_to(src)):sha(p) for p in src.rglob('*') if p.is_file()}
    check_spec=json.loads((pub/'SPEC_LOCK_RECEIPT.json').read_text())
    assert sha(pub/'R_SPECTRUM_CENSUS_SPEC.json')==check_spec['sha256']
    second=root/'reproduction_once'
    assert not second.exists(),'REPRODUCTION_ALREADY_RUN'
    result=subprocess.run([sys.executable,str(impl/'census.py'),'--inputs',str(src),'--public',str(second/'public'),
        '--private',str(second/'private'),'--spec',str(pub/'R_SPECTRUM_CENSUS_SPEC.json')],text=True,capture_output=True)
    (deliver/'private/REPRODUCTION_STDOUT.txt').write_text(result.stdout+result.stderr)
    assert result.returncode==0,result.stderr
    checks=[]
    for n in files:
        p,q=pub/n,second/'public'/n
        checks.append({'file':n,'primary_sha256':sha(p),'reproduction_sha256':sha(q),'bytes_equal':p.read_bytes()==q.read_bytes()})
    p,q=prv/'ENTRY_R_DECISION_JOIN.jsonl',second/'private/ENTRY_R_DECISION_JOIN.jsonl'
    checks.append({'file':'private/ENTRY_R_DECISION_JOIN.jsonl','primary_sha256':sha(p),'reproduction_sha256':sha(q),'bytes_equal':p.read_bytes()==q.read_bytes()})
    source_after={str(p.relative_to(src)):sha(p) for p in src.rglob('*') if p.is_file()}
    passed=all(c['bytes_equal'] for c in checks) and source_before==source_after
    rep={'status':'PASS' if passed else 'FAIL','reproduction_runs':1,'same_inputs':source_before==source_after,
        'input_file_N':len(source_before),'input_hash_changes':sum(source_before[k]!=source_after[k] for k in source_before),
        'spec_sha256':sha(pub/'R_SPECTRUM_CENSUS_SPEC.json'),'output_N':len(checks),
        'output_mismatch_N':sum(not c['bytes_equal'] for c in checks),'checks':checks,'new_model_or_decision_run':0}
    (pub/'REPRODUCTION_RECEIPT.json').write_text(json.dumps(rep,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'boundary':{k:v for k,v in receipt.items() if k!='cases'},'reproduction':{k:v for k,v in rep.items() if k!='checks'}},ensure_ascii=False))
    if not passed:raise SystemExit(1)

if __name__=='__main__':main()
