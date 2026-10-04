"""Independent authentication/join/comparison/IO; imports no primary code."""
from collections import Counter
from decimal import Decimal
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import gzip
import hashlib
import json
import math

ROOT=Path(__file__).resolve().parents[2]
CODE=Path(__file__).parent
WORK=ROOT.parent/'quality_r1_work'
OLD_WORK=ROOT.parent/'quality_work'
OLD=ROOT/'docs/evidence/capital-quality-anti-weak-medium-v1-20261005'
OUT=ROOT/'docs/evidence/capital-quality-anti-weak-medium-v1r1-recovery-20261005'
PRIVATE=WORK/'private'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rows(p):
    with gzip.open(p,'rt',encoding='utf-8') as z:return [json.loads(s) for s in z]
def canon(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def save(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as z:z.write(canon(v))
def compress(p,v,jsonl=False):
    body=b''.join(canon(x) for x in v) if jsonl else canon(v)
    with Path(p).open('xb') as f:
        with gzip.GzipFile(filename='',fileobj=f,mode='wb',mtime=0) as z:z.write(body)
    return {'sha256':sha(p),'uncompressed_sha256':hashlib.sha256(body).hexdigest()}
def now():return datetime.now(ZoneInfo('Asia/Tokyo')).isoformat()
def source_rows():
    contract=load(OUT/'BASELINE_RECOVERY_PRECOMMIT.json')
    for rel,h in contract['input_sha256'].items():assert sha(OLD_WORK/rel)==h
    scores=rows(OLD_WORK/'private/COMMON_SAVED_SCORES.jsonl.gz')
    teacher=rows(OLD_WORK/'private/QUALITY_TEACHERS_EVAL.jsonl.gz')
    mask=rows(OLD_WORK/'inputs/COMMON_EVAL_MASK.jsonl.gz');dec=rows(OLD_WORK/'private/P_P_DECILES_OUTCOME_FREE.jsonl.gz')
    d={x['entry_id']:x for x in dec};t={x['entry_id']:x for x in teacher};m={x['entry_id']:x for x in mask}
    assert len(scores)==len({r['entry_id'] for r in scores})==1028
    assert len(t)==len(teacher)==1600 and len(m)==len(mask)==1039 and len(d)==len(dec)==1028
    ids={r['entry_id'] for r in scores}
    assert ids==set(d)=={r['entry_id'] for r in mask if r['included']}=={r['entry_id'] for r in teacher if r['included_common_OOF']}
    data=[]
    for s in scores:
        eid=s['entry_id'];tt=t[eid];mm=m[eid];dd=d[eid]
        assert s['session']==tt['session']==mm['session']==dd['session'] and s['block']==mm['block']==dd['block']
        assert s['entry_timestamp']==tt['entry_timestamp'] and tt['entry_minute']<920
        assert tt['capture_complete'] and tt['status']=='SUPPORTED_COMPLETE_CAPTURE'
        p=Decimal(tt['potential_decimal']);labels={f'U{u}':int(p>=Decimal(u)/100) for u in [2,3,5,10]}
        assert all(tt[k]==v for k,v in labels.items()) and tt['WEAK2']==1-labels['U2']
        bucket='Q4_MEGA' if labels['U10'] else 'Q3_BIG' if labels['U5'] else 'Q2_MEDIUM' if labels['U3'] else 'Q1_LOW' if labels['U2'] else 'Q0_WEAK'
        assert bucket==tt['bucket'];data.append({**s,**tt})
    data.sort(key=lambda r:(r['block'],r['session'],r['entry_timestamp'],r['symbol'],r['entry_id']))
    assert Counter(r['bucket'] for r in data)=={'Q0_WEAK':596,'Q1_LOW':135,'Q2_MEDIUM':127,'Q3_BIG':103,'Q4_MEGA':67}
    assert [sum(r[f'U{u}'] for r in data) for u in [2,3,5,10]]==[432,297,170,67]
    assert len({r['session'] for r in data})==38
    return data,{eid:r['pP_decile'] for eid,r in d.items()}
def strip_groups(cc):
    result={}
    for t,table in cc.items():
        result[t]={}
        for s,v in table.items():
            result[t][s]={k:({a:b for a,b in x.items() if a!='groups'} if isinstance(x,dict) and 'groups' in x else x) for k,x in v.items()}
    return result
def difference(a,b,path=''):
    errors=[];floats=[]
    def walk(x,y,p):
        if isinstance(x,dict):
            if not isinstance(y,dict) or set(x)!=set(y):errors.append(p+':keys');return
            for k in x:walk(x[k],y[k],p+'/'+str(k))
        elif isinstance(x,list):
            if not isinstance(y,list) or len(x)!=len(y):errors.append(p+':list');return
            for i,(xx,yy) in enumerate(zip(x,y)):walk(xx,yy,p+'/'+str(i))
        elif isinstance(x,(int,float)) and not isinstance(x,bool):
            if not isinstance(y,(int,float)) or isinstance(y,bool) or not math.isfinite(y):errors.append(p+':number');return
            d=abs(float(x)-float(y));floats.append(d)
            if d>1e-12:errors.append(p+':float')
        elif x!=y:errors.append(p+':value')
    walk(a,b,path);return errors,max(floats or [0.])
def claimed(name,outputs):
    c=load(OUT/(name+'.json'));assert c['maximum_executions']==1 and c['new_fits']==0
    assert not any(Path(p).exists() for p in outputs),'Ambiguous execution: STOP'
    pubs=load(WORK/'publications.json')
    assert any(str((OUT/(name+'.json')).relative_to(ROOT)) in p['paths'] for p in pubs)
    for p,h in c['code_sha256'].items():assert sha(ROOT/p)==h
    return c
def checkpoint(name,result,next_policy):
    pre=load(OLD/'FEATURE_MODEL_SPLIT_PRECOMMIT.json')
    count={'newFits':0,'refits':0,'auditRefits':0,'reusedCompletedFits':16,'CapitalReplay':0,'MAX3Replay':0,
        'baseline_builds_primary':1,'baseline_builds_independent':1,
        'primary_performance_packages':int((OUT/'R7_ANTI_WEAK_MEDIUM_PRIMARY_EVAL.json').exists()),
        'independent_performance_packages':int(name.startswith('R10'))}
    save(OUT/(name+'.json'),{'exact_jst':now(),'branch':'capital-quality-v1r1-recovery-20261005',
        'basis_HEAD_tree':load(WORK/'latest_basis.json'),'current_state':name,'status':'COMPLETE',
        'completed':['Independent implementation without primary trainer/evaluator/baseline/metrics imports'],
        'result':result,'next_policy':next_policy,'counts':count,'Safety':pre['Safety']})
