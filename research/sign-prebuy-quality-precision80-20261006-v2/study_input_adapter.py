"""Strip verified intent sidecars to the finite learner's input-only schema.

State unavailability, nonobserved semantics and legacy fill eligibility never
change support or the population. P0 is present at the intent even when the
State kernel has no endpoint. Learned-score/teacher dependency approval is a
separate pinned metadata receipt; the original replay receipt is not changed.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime,timedelta,timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import numpy as np

JST=timezone(timedelta(hours=9))
FIELDS=frozenset(('entry_id','session','intent_minute','numeric','categorical','supported','input_asof'))


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def check_global_receipt(receipt,expected_hash):
    if sha(receipt)!=expected_hash:raise ValueError('GLOBAL_METADATA_RECEIPT_HASH_MISMATCH')
    proof=json.loads(Path(receipt).read_text())
    if (proof.get('status')!='PASS_METADATA_REUSE_WITH_DECLARED_SOURCE_REPLAY_LIMIT'
        or proof.get('P1_row_dependency_errors')!=0 or proof.get('teacher_schema_violations')!=0
        or any(v!=0 for v in proof.get('teacher_clock_provenance_errors',{'missing':1}).values())
        or proof.get('frozen_producer_independent_audit_reused',{}).get('mismatch_N')!=0
        or proof.get('frozen_producer_independent_audit_reused',{}).get('status')!='PASS'):
        raise ValueError('GLOBAL_METADATA_DEPENDENCY_NOT_PASS')
    return {'receipt_sha256':expected_hash,'status':proof['status'],'limits':proof['limits']}


def adapt_row(row,schema):
    key=row['entry_id'];day=row['session'];intent=row['intent_minute'];p=row['provenance']
    if key.split('|',1)[0]!=day or type(intent) is not int or not 0<=intent<1440:
        raise ValueError('ENTRY_IDENTITY_CLOCK')
    decision=datetime.fromisoformat(day).replace(tzinfo=JST)+timedelta(minutes=intent)
    if datetime.fromisoformat(row['intent_timestamp'])!=decision:
        raise ValueError('INTENT_TIMESTAMP_MISMATCH')
    if (p['cutoff_basis']!='FROZEN_FIRST_INTENT' or p['cutoff_minute']!=intent
        or p['original_row_id']!=key+'|'+str(intent) or type(p['original_row_index']) is not int):
        raise ValueError('ORIGINAL_INTENT_IDENTITY')
    numeric_cols=set(schema['STRUCTURE']['numeric']);category_cols=set(schema['STRUCTURE']['categorical'])
    if set(row['numeric'])!=numeric_cols or set(row['categorical'])!=category_cols:
        raise ValueError('INPUT_SCHEMA_KEYS')
    numeric=dict(row['numeric']);categorical=dict(row['categorical'])
    if any(v is not None and (type(v) not in (int,float) or not math.isfinite(v)) for v in numeric.values()):
        raise ValueError('INVALID_NUMERIC_INPUT')
    p0=schema['BASE']['numeric'][:110]
    if len(p0)!=110 or any(not k.startswith('p0/') for k in p0):raise ValueError('ORIGINAL_P0_ORDER')
    vector=np.asarray([np.nan if numeric[k] is None else float(numeric[k]) for k in p0],np.float64)
    if hashlib.sha256(vector.tobytes()).hexdigest()!=p['p0_snapshot_hash']:
        raise ValueError('P0_SNAPSHOT_HASH_MISMATCH')
    if numeric['p0/clockMinute']!=intent:raise ValueError('P0_NOT_AT_INTENT')
    at=p['max_known_minute']
    if at is None:
        if row['source_status']!='SOURCE_UNAVAILABLE':raise ValueError('CONNECTED_STATE_ENDPOINT_MISSING')
        # P0 and Entry score exist at the exact intent; State nulls are retained.
        at=intent
    if type(at) is not int or not 0<=at<=intent:raise ValueError('STATE_ENDPOINT_AFTER_INTENT')
    asof=datetime.fromisoformat(day).replace(tzinfo=JST)+timedelta(minutes=at)
    out={'entry_id':key,'session':day,'intent_minute':intent,'numeric':numeric,'categorical':categorical,
         'supported':True,'input_asof':asof.isoformat()}
    assert set(out)==FIELDS
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input-root',type=Path,required=True)
    p.add_argument('--global-receipt',type=Path,required=True)
    p.add_argument('--global-receipt-sha256',required=True)
    args=p.parse_args();root=args.input_root
    output=root/'study_features.jsonl.gz';audit_path=root/'STUDY_INPUT_BINDING_AUDIT.json'
    if output.exists() or audit_path.exists():raise ValueError('OUTPUT_ALREADY_EXISTS_NO_OVERWRITE')
    gate=check_global_receipt(args.global_receipt,args.global_receipt_sha256)
    provenance=json.loads((root/'provenance.json').read_text())
    schema=json.loads((root/'feature_schema.json').read_text())
    feature=root/'features.jsonl.gz'
    if sha(feature)!=provenance['features_sha256']:raise ValueError('REPLAY_FEATURE_HASH_MISMATCH')
    result=[];state_status=Counter();p0checks=0
    with gzip.open(feature,'rt') as f:
        for line in f:
            row=json.loads(line);result.append(adapt_row(row,schema));p0checks+=1
            state_status[row['source_status']]+=1
    if len(result)!=1600 or len({r['entry_id'] for r in result})!=1600:
        raise ValueError('EXACT1600_POPULATION_REQUIRED')
    if result!=sorted(result,key=lambda r:(r['session'],r['intent_minute'],r['entry_id'])):
        raise ValueError('CANONICAL_INPUT_ORDER')
    with output.open('xb') as f,gzip.GzipFile(fileobj=f,mode='wb',mtime=0) as gz:
        for row in result:gz.write((json.dumps(row,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode())
    audit={'status':'PASS_INPUT_ONLY_STUDY_ADAPTER_GLOBAL_METADATA_BOUND',
           'entry_count':len(result),'supported_entry_count':sum(r['supported'] for r in result),
           'P0_snapshot_hash_checks':p0checks,'identity_clock_checks':len(result),'max_input_asof_after_intent':0,
           'state_source_status_counts':dict(state_status),'quality_or_execution_based_exclusions':0,
           'output_schema_fields':sorted(FIELDS),'source_replay_learned_lineage_flag_unchanged':schema['learned_score_lineage_audited'],
           'fit_allowed_by_adapter':False,'global_metadata_gate':gate,
           'sha256':{'original_replay_features':sha(feature),'original_feature_schema':sha(root/'feature_schema.json'),
                     'original_replay_provenance':sha(root/'provenance.json'),'adapter_code':sha(Path(__file__)),
                     'study_features':sha(output)},
           'model_fits':0,'teacher_sign_values_referenced':0,'teacher_profit_values_referenced':0,'threshold_choices':0,
           'created_utc':datetime.now(timezone.utc).isoformat()}
    with audit_path.open('x') as f:json.dump(audit,f,indent=2,ensure_ascii=False,allow_nan=False)
    print(json.dumps(audit),flush=True)

if __name__=='__main__':main()
