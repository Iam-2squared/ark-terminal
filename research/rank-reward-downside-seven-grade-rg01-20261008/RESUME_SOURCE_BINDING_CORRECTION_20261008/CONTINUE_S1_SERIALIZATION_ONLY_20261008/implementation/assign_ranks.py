"""Frozen formulas only; outcome files cannot be opened by the assignment process."""
import json,gzip,pathlib,math,hashlib,sys,collections
METHODS=['R0_4','U7','G7_FULL','B7_FULL','G7_PRICE','B7_PRICE']
GRADES='SABCDEF'
def grade(v):
    if v is None or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0:return None
    for n,b in enumerate([2.50,2.00,1.50,1.25,1.00,.75]):
        if v>=b:return n
    return 6
def risk_valid(q):
    try:
        q3,q5=q['q3'],q['q5'];b5=q['B0_p5'][0];b3=b5+q['B0_p5'][1]
        return all(math.isfinite(v) for v in [q3,q5,b3,b5]) and 0<=q5<=q3<=1 and b5>0 and b3>=b5
    except (KeyError,IndexError,TypeError,ValueError):return False
def one(r):
    ml=r['ML'];g=grade(ml);native=[-ml,-r['m5'],-r['m3'],-r['m2'],r['entry_timestamp'],r['symbol'],r['entry_id']]
    assert native==r['R0_candidate_order']
    out={'R0_4':{'grade':r['R0_rank'],'grade_index':'SABC'.index(r['R0_rank']),'order_key':native,'reason':'SAVED_R0_UNCHANGED','available':g is not None},'U7':{'grade':GRADES[g] if g is not None else 'RANK_UNAVAILABLE','grade_index':g,'order_key':[g,*native] if g is not None else None,'reason':'UPSIDE_FIXED_BOUNDARIES','available':g is not None}}
    for suf,src in [('FULL','D-FULL'),('PRICE','D-PRICE')]:
        q=r['risk'][src]
        if g is None or not risk_valid(q):
            for family in ['G7','B7']:out[family+'_'+suf]={'grade':'RANK_UNAVAILABLE','grade_index':None,'order_key':None,'reason':'RISK_INPUT_UNAVAILABLE','available':False}
            continue
        b5=q['B0_p5'][0];b3=b5+q['B0_p5'][1];r3=q['q3']/b3;r5=q['q5']/b5
        delta=int((r3>1 or r5>1) if g==0 else (r3>=1.5 and r5>=1.5));ng=min(6,g+delta)
        out['G7_'+suf]={'grade':GRADES[ng],'grade_index':ng,'order_key':[ng,*native],'reason':'S_OR_GT_1_DOWN_ONE' if g==0 and delta else 'NON_S_AND_GE_1_5_DOWN_ONE' if delta else 'UNCHANGED','available':True,'r3':r3,'r5':r5,'downshift':ng-g}
        x3=min(2,max(0,r3-1));x5=min(2,max(0,r5-1));penalty=min(.30,.12*x3+.06*x5);eff=ml*(1-penalty);maxdown=1 if ml>=2 else 2
        bg=min(6,min(grade(eff),g+maxdown))
        if g==0 and (r3>1 or r5>1):bg=max(1,bg)
        out['B7_'+suf]={'grade':GRADES[bg],'grade_index':bg,'order_key':[bg,-eff,*native],'reason':'CONTINUOUS_RISK_PENALTY_WITH_FIXED_DOWNSHIFT_CAP' if bg>g else 'GRADE_UNCHANGED_EFFECTIVE_ML_ORDER','available':True,'r3':r3,'r5':r5,'penalty':penalty,'effective_ML':eff,'downshift':bg-g,'max_downshift':maxdown}
    return out
def assign(rows):
    allowed={'entry_id','session','symbol','block','entry_minute','entry_timestamp','p2','p3','p5','base2','base3','base5','m2','m3','m5','ML','R0_rank','R0_candidate_order','first_intent_t_x','first_intent_minute','intent_row_id','t_rank','upside_feature_asof','H_source','downside_train_cutoff','risk','asof_status','actual_arrival'}
    assert len(rows)==1039 and len({r['entry_id'] for r in rows})==1039
    out=[]
    for r in rows:
        assert set(r)==allowed,'COMPOSE_FIELD_ALLOWLIST'
        out.append({k:r[k] for k in ['entry_id','session','symbol','block','entry_timestamp','first_intent_t_x','asof_status']})
        out[-1]['methods']=one(r)
    for m in METHODS:
        active=[r for r in out if r['methods'][m]['available']];ordered=sorted(active,key=lambda r:r['methods'][m]['order_key']);bn=collections.Counter()
        for n,r in enumerate(ordered,1):bn[r['block']]+=1;r['methods'][m]['global_order']=n;r['methods'][m]['block_order']=bn[r['block']]
    assert [r['entry_id'] for r in sorted(out,key=lambda r:r['methods']['R0_4']['global_order'])]==[r['entry_id'] for r in sorted(out,key=lambda r:r['methods']['U7']['global_order'])]
    for r in out:
        for m in METHODS[2:]:
            d=r['methods'][m];assert d['grade_index']>=r['methods']['U7']['grade_index'];assert d['downshift']<=(1 if next(x for x in rows if x['entry_id']==r['entry_id'])['ML']>=2 else (1 if m.startswith('G') else 2))
    return sorted(out,key=lambda r:r['entry_id'])
def bytes_for(rows):return gzip.compress((''.join(json.dumps(r,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n' for r in rows)).encode(),mtime=0)
def pin(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}
def main():
    mode=sys.argv[1];base=pathlib.Path(__file__).resolve().parents[1];inp=base/'private/COMPOSE_ONLY_INPUTS.jsonl.gz';pre=base/'public/PRECOMMIT_RG01.json';gate=base/'cache/PRECOMMIT_ACTUAL_GET_PASS.json'
    destination=base/('reproduction' if mode=='reproduce' else 'private');destination.mkdir(parents=True,exist_ok=True);dst=destination/'SEALED_RANK_ASSIGNMENTS.jsonl.gz';seal=destination/'RANK_ASSIGNMENT_SEAL.json'
    if mode=='assign':assert not dst.exists(),'PRIMARY_ASSIGNMENT_ALREADY_EXISTS'
    reads={inp.resolve(),pre.resolve(),gate.resolve()};writes={dst.resolve(),seal.resolve()}
    def hook(event,args):
        if event=='open':
            p=args[0]
            if isinstance(p,(str,bytes)):
                path=pathlib.Path(p).resolve();assert path in reads|writes,'ASSIGN_OPEN_DENIED: '+str(path)
    sys.addaudithook(hook)
    denied=False
    try:open(base/'private/DENY_CANARY_FUTURE_R_U.json').read()
    except AssertionError:denied=True
    assert denied
    g=json.loads(gate.read_text());assert g['status']=='EXACT_GET_PASS'
    contract=json.loads(pre.read_text());assert pin(pre.read_bytes())==g['precommit_pin']
    b=inp.read_bytes();assert pin(b)==contract['compose_pin'];rows=[json.loads(x) for x in gzip.decompress(b).splitlines()];a=assign(rows);payload=bytes_for(a);dst.write_bytes(payload)
    seal.write_text(json.dumps({'status':'ASSIGNMENT_SEALED_LOCAL','Entry_N':len(a),'method_N':6,'method_assignments_N':len(a)*6,'campaign':1,'mode':mode,'assignment_pin':pin(payload),'compose_pin':pin(b),'precommit_pin':pin(pre.read_bytes()),'counts':{m:dict(collections.Counter(r['methods'][m]['grade'] for r in a)) for m in METHODS},'deny_canary_blocked':denied,'outcome_file_opens':0,'model_fit':0,'score_reinference':0,'asof_mode':'HISTORICAL_MIXED_ASOF_RESEARCH_ONLY'},sort_keys=True,indent=2)+'\n')
    print(json.dumps({'status':'ASSIGNED','assignment_pin':pin(payload),'counts':{m:dict(collections.Counter(r['methods'][m]['grade'] for r in a)) for m in METHODS}}))
if __name__=='__main__':main()
