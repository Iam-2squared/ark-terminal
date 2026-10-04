"""Independent baseline certification, before opening any new-head scores."""
import ast
from independent_io import *
from independent_stats import quality,conditional,deciles

def main():
    claimed('BASELINE_INDEPENDENT_EXECUTION_CLAIM',[OUT/'BASELINE_INDEPENDENT_CERTIFICATION.json',PRIVATE/'INDEPENDENT_BASELINE_FULL.json.gz'])
    data,saved_dec=source_rows();dec=deciles(data);assert dec==saved_dec
    names=['CORE_H2','CORE_H3','pP','legacy_ML']
    mm={s:quality(data,s) for s in names};cc={t:{s:conditional(data,s,t,dec) for s in names} for t in ['U2','U3']}
    expected={'N':1028,'metrics':mm,'conditional':strip_groups(cc),'new_fits':0,
        'metric_code_sha256':'dd3b59d740835bddcfb8e68f0bab8a9ffff7fb26286d499a66428eab66ae7acb'}
    compact=load(OUT/'BASELINE_METRICS_COMPACT.json');root=load(OUT/'BASELINE_RECOVERY_ROOT.json');identity=load(OUT/'BASELINE_IDENTITY_AUDIT.json')
    errs,maxdiff=difference(compact,expected)
    assert not errs,errs[:20]
    rowsha=hashlib.sha256(b''.join(canon(r) for r in data)).hexdigest()
    ids=hashlib.sha256(('\n'.join(r['entry_id'] for r in data)+'\n').encode()).hexdigest()
    assert identity['canonical_rows_uncompressed_sha256']==rowsha and identity['ordered_entry_ids_sha256']==ids
    assert identity['N']==root['N']==1028 and identity['identity_mismatch_N']==identity['decile_mismatch_N']==0
    assert identity['bucket_counts']==dict(Counter(r['bucket'] for r in data))
    assert identity['positive_counts']=={f'U{u}':sum(r[f'U{u}'] for r in data) for u in [2,3,5,10]}
    assert root['input_sha256']==load(OUT/'BASELINE_RECOVERY_PRECOMMIT.json')['input_sha256']
    assert root['compact_sha256']==sha(OUT/'BASELINE_METRICS_COMPACT.json') and root['identity_audit_sha256']==sha(OUT/'BASELINE_IDENTITY_AUDIT.json')
    assert root['old_Q4_metric_input'] is False and root['old_byte_hash_recovery'] is False
    for a in root['private_artifacts']:
        p=WORK/a['path'];body=gzip.decompress(p.read_bytes())
        assert p.stat().st_size==a['size'] and sha(p)==a['sha256']
        assert len(body)==a['uncompressed_size'] and hashlib.sha256(body).hexdigest()==a['uncompressed_sha256']
        if a['schema']=='canonical JSON':assert body==canon(json.loads(body))
        else:assert body==b''.join(canon(json.loads(s)) for s in body.splitlines())
    full=json.loads(gzip.decompress((PRIVATE/'BASELINE_METRICS_FULL.json.gz').read_bytes()))
    efull={**expected,'conditional':cc};fullerr,fulldiff=difference(full,efull);assert not fullerr
    audit=load(OUT/'BASELINE_ACTUAL_GET_AUDIT.json');assert audit['status']=='PASS'
    needed={'BASELINE_METRICS_COMPACT.json','BASELINE_IDENTITY_AUDIT.json','BASELINE_RECOVERY_ROOT.json'}
    checked={Path(c['path']).name:c for c in audit['actual_GET_checks']}
    for p in needed:
        c=checked[p];assert c['returned_body_exact'] and c['returned_body_parse']=='PASS'
        assert c['sha256']==c['downloaded_body_sha256']==sha(OUT/p)
        assert (OUT/p).read_bytes()==canon(load(OUT/p))
    imports=[]
    for filename in ['independent_baseline.py','independent_io.py','independent_stats.py']:
        for n in ast.walk(ast.parse((CODE/filename).read_text())):
            if isinstance(n,ast.Import):imports += [v.name for v in n.names]
            if isinstance(n,ast.ImportFrom):imports.append(n.module)
    assert not any(x in ['control','sources','baseline_rebuild','metrics','evaluate','train_heads','sklearn'] for x in imports)
    saved=compress(PRIVATE/'INDEPENDENT_BASELINE_FULL.json.gz',efull)
    result={'exact_jst':now(),'status':'PASS','N':1028,'public_compact_mismatch_N':0,'full_group_mismatch_N':0,
        'root_identity_mismatch_N':0,'max_abs_float_difference':max(maxdiff,fulldiff),'float_tolerance':1e-12,
        'primary_builder_metrics_evaluator_imports':0,'ROC':'weighted rank-sum with average ties',
        'PR':'distinct-score threshold grouped average precision','TopK':'independent fixed tie order',
        'conditional':'positive-negative pairwise credit','independent_decile_mismatch_N':0,
        'baseline_actual_GET_verified':True,'new_head_performance_reads':0,'newFits':0,
        'independent_artifact':saved,'source_rows_canonical_sha256':rowsha}
    save(OUT/'BASELINE_INDEPENDENT_CERTIFICATION.json',result)
    checkpoint('R4_BASELINE_INDEPENDENT_CERTIFICATION',result,'R5 may now join completed new-head OOF and audit saved model state; never fit')
    print(json.dumps({'baseline_status':'PASS','compact_mismatch_N':0,'max_float':result['max_abs_float_difference'],'new_head_reads':0}))

if __name__=='__main__':main()
