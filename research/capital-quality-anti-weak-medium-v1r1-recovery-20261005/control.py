"""Recovery-only IO, append-only checkpoints and zero-fit execution guards."""
import gzip
import hashlib
import importlib.util
import io
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT.parent / 'quality_r1_work'
PRIVATE = WORK / 'private'
OLD_WORK = ROOT.parent / 'quality_work'
OLD = ROOT / 'docs/evidence/capital-quality-anti-weak-medium-v1-20261005'
OUT = ROOT / 'docs/evidence/capital-quality-anti-weak-medium-v1r1-recovery-20261005'
CODE = Path(__file__).parent
OLD_METRICS = ROOT / 'research/capital-quality-anti-weak-medium-v1-20261005/metrics.py'
OLD_HEAD = 'c3617de4777d6ca0f5adc04e075617bca1899c69'
BRANCH = 'capital-quality-v1r1-recovery-20261005'
METRIC_HASH = 'dd3b59d740835bddcfb8e68f0bab8a9ffff7fb26286d499a66428eab66ae7acb'
NEXT_POLICY = 'Wait until independent Main Allocation Work is closed. If Quality head(s) pass, integrate only in a new precommitted cycle; do not modify Main mid-run.'
SAFETY = {k:False for k in [
    'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
    'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed',
    'transmitted','productionReady','orders','main_merge','force_push','provider','claude',
    'allocator_change','capital_replay','max3_replay','fresh_open']}
COUNTS = {'newFits':0,'refits':0,'auditRefits':0,'reusedCompletedFits':16,
    'CORE_H2_H3_fits':0,'pP_fits':0,'MOVE_U2_fits':0,'MOVE_U3_fits':0,
    'CapitalReplay':0,'MAX3Replay':0,'threshold_sweep':0,'new_model':0,
    'trainer_execution':0,'Fresh_open':0,'orders':0,'main_merge':0,'force_push':0,
    'provider':0,'Claude':0}

def now(): return datetime.now(ZoneInfo('Asia/Tokyo')).isoformat()
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def rows(p):
    with gzip.open(p,'rt',encoding='utf-8') as f: return [json.loads(s) for s in f]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(v):
    return (json.dumps(v,sort_keys=True,allow_nan=False,separators=(',',':'),ensure_ascii=True)+'\n').encode('utf-8')
def save(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(canonical(v))
def textsave(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(v)
def gzsave(p,v,jsonl=False):
    body=b''.join(canonical(r) for r in v) if jsonl else canonical(v)
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:
        with gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0) as z:z.write(body)
    return {'path':str(p.relative_to(WORK)),'size':p.stat().st_size,'sha256':sha(p),
        'uncompressed_size':len(body),'uncompressed_sha256':hashlib.sha256(body).hexdigest(),
        'schema':'canonical JSONL' if jsonl else 'canonical JSON','gzip_mtime':0,'filename_metadata':False}
def key(r): return (r['block'],r['session'],r['entry_timestamp'],r['symbol'],r['entry_id'])
def basis(): return read(WORK/'latest_basis.json')
def counts():
    return {**COUNTS,'baseline_builds_primary':int((OUT/'R3_BASELINE_PRIMARY_REBUILD.json').exists()),
        'baseline_builds_independent':int((OUT/'R4_BASELINE_INDEPENDENT_CERTIFICATION.json').exists()),
        'primary_performance_packages':int((OUT/'R7_ANTI_WEAK_MEDIUM_PRIMARY_EVAL.json').exists()),
        'independent_performance_packages':int((OUT/'R10_FULL_INDEPENDENT_PERFORMANCE_AUDIT.json').exists())}
def checkpoint(name,completed,result,next_policy):
    save(OUT/(name+'.json'),{'exact_jst':now(),'branch':BRANCH,'basis_HEAD_tree':basis(),
        'current_state':name,'status':'COMPLETE','completed':completed,'result':result,
        'next_policy':next_policy,'counts':counts(),'Safety':SAFETY})
def guard_claim(name,outputs):
    p=read(OUT/(name+'.json'))
    assert p['maximum_executions']==1 and p['new_fits']==0
    assert p['committed_before_execution'] and p['actual_GET_before_execution_verified']
    pub=read(WORK/'publications.json')
    assert any(str((OUT/(name+'.json')).relative_to(ROOT)) in x['paths'] for x in pub)
    assert not any(Path(x).exists() for x in outputs),'Existing/ambiguous output: STOP, never rerun'
    for rel,h in p['code_sha256'].items():assert sha(ROOT/rel)==h
    return p
def old_metrics():
    assert sha(OLD_METRICS)==METRIC_HASH
    spec=importlib.util.spec_from_file_location('frozen_quality_v1_metrics',OLD_METRICS)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def compact_conditionals(cc):
    return {t:{s:{k:({a:b for a,b in v.items() if a!='groups'} if isinstance(v,dict) and 'groups' in v else v)
        for k,v in c.items()} for s,c in ss.items()} for t,ss in cc.items()}
def compare(a,b,path='',errors=None,diffs=None):
    errors=[] if errors is None else errors;diffs=[] if diffs is None else diffs
    if isinstance(a,dict):
        if not isinstance(b,dict) or set(a)!=set(b):errors.append(path+':keys');return errors,diffs
        for k in a:compare(a[k],b[k],path+'/'+str(k),errors,diffs)
    elif isinstance(a,list):
        if not isinstance(b,list) or len(a)!=len(b):errors.append(path+':length');return errors,diffs
        for i,(x,y) in enumerate(zip(a,b)):compare(x,y,path+'/'+str(i),errors,diffs)
    elif isinstance(a,(int,float)) and not isinstance(a,bool):
        if not isinstance(b,(int,float)) or isinstance(b,bool):errors.append(path+':type')
        else:
            d=abs(float(a)-float(b));diffs.append(d)
            if d>1e-12:errors.append(path+':float')
    elif a!=b:errors.append(path+':value')
    return errors,diffs
