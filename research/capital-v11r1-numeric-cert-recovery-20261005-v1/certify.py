"""Independent raw matrix and canonical primitive certification. No old trainer/evaluator imports."""
from control import *
import numpy as np, math,sys
from decimal import Decimal,localcontext
def bits(a):return np.asarray(a,dtype=np.float64).view(np.uint64)
def exact(a,b):return bool(np.array_equal(bits(a),bits(b)))
def digest_array(a):return hashlib.sha256(np.asarray(a,dtype=np.float64,order='C').tobytes(order='C')).hexdigest()
def matrix():
    assert (WORK/'publication_receipts/N0_N2_SOURCE_REUSE_AND_NUMERIC_OPERATOR_PRECOMMIT_ACTUAL_GET.json').exists()
    save(PRIVATE/'claims/NUMERICAL_CERTIFICATION_STARTED.json',{'exact_jst':now(),'basis':read(WORK/'latest_basis.json'),'reexecution_allowed':False,'newFits':0})
    raw=rows(MAIN/'inputs/movement/RUNTIME_CAUSAL.jsonl.gz');lookup={r['entry_id']:r for r in raw};assert len(lookup)==len(raw)
    spec=read(PARENT/'MRET_TEACHER_FEATURE_MODEL_PRECOMMIT.json');fields=spec['features']['numeric_fields'];cats=spec['features']['categorical_fields'];split=read(SPLIT);records=[]
    for block in split['blocks']:
        b=block['block'];m=read(V11/f'private/models/MRET_BLOCK_{b:02d}.json');ids=m['train_entry_ids'];projection=rows(V11/f'private/train_labels/MRET_BLOCK_{b:02d}_PAST_ONLY.jsonl.gz')
        assert len(ids)==len(set(ids))==m['train_N']
        projected={r['entry_id'] for r in projection};derived=[r['entry_id'] for r in raw if r['entry_id'] in projected]
        assert derived==ids and [r['entry_id'] for r in projection]==ids
        assert fields==m['preprocessing']['numeric_fields'] and cats==m['preprocessing']['categorical_fields']
        n=len(ids);A=np.empty((n,46),dtype=np.float64,order='C');missing=np.empty((n,46),dtype=np.float64,order='C')
        vocab={k:set(['__UNKNOWN__']) for k in cats};raw_checks=0
        for i,k in enumerate(ids):
            r=lookup[k];assert r['session'] in block['train'] and r['session']<min(block['test']) and r['entry_minute']<920
            for j,field in enumerate(fields):
                v=r['numeric'][field];A[i,j]=np.nan if v is None else float(v);missing[i,j]=float(v is None)
                assert math.isnan(A[i,j]) if v is None else exact([A[i,j]],[float(v)])
                raw_checks+=1
            for field in cats:vocab[field].add(r['categorical'][field] or '__UNKNOWN__')
        assert not np.isinf(A).any() and np.array_equal(np.isnan(A).astype(np.float64),missing)
        X0=np.column_stack([np.nan_to_num(A,nan=0.0),np.isnan(A).astype(np.float64)])
        assert X0.shape==(n,92) and X0.flags.c_contiguous and np.isfinite(X0).all()
        assert np.array_equal(X0[:,46:],missing)
        for i in range(n):
            for j in range(46):assert X0[i,j]==(0. if missing[i,j] else A[i,j])
        vv={k:sorted(vocab[k]) for k in cats};assert vv==m['preprocessing']['categorical_train_vocab']
        p=PRIVATE/f'matrices/MRET_BLOCK_{b:02d}_X0.npz';p.parent.mkdir(exist_ok=True)
        with p.open('xb') as f:np.savez_compressed(f,X0=X0)
        record={'block':b,'train_N':n,'shape':[n,92],'dtype':'float64','C_contiguous':True,'train_ids_sha256':hashlib.sha256(json.dumps(ids,separators=(',',':')).encode()).hexdigest(),'train_identity_exact':True,'row_order_exact':True,'column_order_exact':True,'raw_values_bit_exact':True,'raw_value_checks':raw_checks,'missing0_exact':True,'missing_indicators_exact':True,'categorical_vocabulary_exact':True,'finite_after_imputation':True,'X0_bytes_sha256':digest_array(X0),'matrix_npz_sha256':sha(p)}
        records.append(record)
    save(OUT/'NUMERIC_MATRIX_CERTIFICATE.json',{'status':'PASS','blocks':records,'raw_source_sha256':sha(MAIN/'inputs/movement/RUNTIME_CAUSAL.jsonl.gz'),'trainer_imports':0,'raw_value_checks':sum(r['raw_value_checks'] for r in records),'mismatch_N':0,'Safety':SAFETY})
    checkpoint('N3_INDEPENDENT_MATRIX_CONSTRUCTION','All eight independent raw X0 matrices / train identity / order / missing / vocab exact','N4 canonical primitive bit identity')
    print(json.dumps({'matrix':'PASS','blocks':8,'raw_value_checks':sum(r['raw_value_checks'] for r in records)}))
def ulp(a,b):
    def ordered(x):
        q=int(bits([x])[0]);return (~q)&((1<<64)-1) if q>>63 else q|(1<<63)
    return abs(ordered(a)-ordered(b))
def preprocess():
    assert read(OUT/'NUMERIC_MATRIX_CERTIFICATE.json')['status']=='PASS';records=[];alternate=[];decimal=[];failures=[]
    fields=read(PARENT/'MRET_TEACHER_FEATURE_MODEL_PRECOMMIT.json')['features']['numeric_fields']
    names=fields+['missing_indicator/'+k for k in fields]
    for b in range(1,9):
        with np.load(PRIVATE/f'matrices/MRET_BLOCK_{b:02d}_X0.npz') as q:X0=q['X0']
        mu=np.mean(X0,axis=0,dtype=np.float64);scale=np.std(X0,axis=0,dtype=np.float64,ddof=0);zero=scale==0.0;scale[zero]=np.float64(1.0)
        m=read(V11/f'private/models/MRET_BLOCK_{b:02d}.json');jmean=m['preprocessing']['numeric_mean'];jscale=m['preprocessing']['numeric_scale']
        with np.load(V11/f'private/fitted_state/MRET_BLOCK_{b:02d}.npz') as q:nmean=q['numeric_mean'];nscale=q['numeric_scale'];coef=q['coef'][0];intercept=q['intercept'][0];classes=q['classes']
        checks={'mean_independent_JSON':exact(mu,jmean),'scale_independent_JSON':exact(scale,jscale),'mean_independent_NPZ':exact(mu,nmean),'scale_independent_NPZ':exact(scale,nscale),'mean_JSON_NPZ':exact(jmean,nmean),'scale_JSON_NPZ':exact(jscale,nscale),'coef_exact':exact(coef,m['coef']),'intercept_exact':exact([intercept],[m['intercept']]),'classes_exact':np.array_equal(classes,m['classes'])}
        if not all(checks.values()):failures.append({'block':b,'failed_checks':[k for k,v in checks.items() if not v]})
        records.append({'block':b,'mean_elements':92,'scale_elements':92,'checks':checks,'zero_scale_replaced_N':int(zero.sum()),'zero_scale1_exact':bool(np.all(scale[zero]==1.0)),'mean_bytes_sha256':digest_array(mu),'scale_bytes_sha256':digest_array(scale)})
        altmean=np.array([math.fsum(float(v) for v in X0[:,j])/len(X0) for j in range(92)])
        altscale=np.array([math.sqrt(math.fsum((float(v)-altmean[j])**2 for v in X0[:,j])/len(X0)) for j in range(92)]);altscale[altscale==0]=1.
        for j,name in enumerate(names):
            delta=abs(float(scale[j])-float(altscale[j]));alternate.append({'block':b,'feature':name,'column':j,'canonical_np_mean':float(mu[j]),'fsum_mean':float(altmean[j]),'mean_abs_delta':abs(float(mu[j])-float(altmean[j])),'canonical_np_scale':float(scale[j]),'fsum_scale':float(altscale[j]),'abs_delta':delta,'relative_delta':delta/abs(float(scale[j])) if scale[j] else None,'ULP_distance':ulp(scale[j],altscale[j]),'gate_input':False})
        with localcontext() as ctx:
            ctx.prec=80;v=[Decimal.from_float(float(x)) for x in X0[:,5]];n=Decimal(len(v));mean=sum(v,Decimal(0))/n;variance=sum(((x-mean)**2 for x in v),Decimal(0))/n;sd=variance.sqrt()
            decimal.append({'block':b,'feature':fields[5],'precision':80,'Decimal_mean':str(mean),'Decimal_scale':str(sd),'canonical_np_scale':float(scale[5]),'fsum_scale':float(altscale[5]),'decimal_to_float_scale':float(sd),'canonical_decimal_abs_delta':abs(float(scale[5])-float(sd)),'gate_input':False})
    save(OUT/'PREPROCESSING_BIT_CERTIFICATION.json',{'status':'PASS' if not failures else 'FAIL','operator':'FIT_NUMERIC_OPERATOR_V1','blocks':records,'mean_bit_exact_elements':8*92,'scale_bit_exact_elements':8*92,'mismatch_N':len(failures),'failures':failures,'preprocessing_tolerance_used':False,'newFits':0,'Safety':SAFETY})
    gzsave(PRIVATE/'ALTERNATE_NUMERIC_DIAGNOSTIC.jsonl.gz',alternate)
    save(OUT/'ALTERNATE_NUMERIC_DIAGNOSTIC.json',{'hard_gate_input':False,'operator_alternation_allowed':False,'all_scale_elements_N':len(alternate),'records':alternate,'Decimal_from_float_reference':decimal,'max_fsum_scale_abs_delta':max(x['abs_delta'] for x in alternate),'old_tolerance_exceeded_diagnostic_records':[x for x in alternate if x['abs_delta']>1e-12],'diagnostic_private_sha256':sha(PRIVATE/'ALTERNATE_NUMERIC_DIAGNOSTIC.jsonl.gz')})
    checkpoint('N4_PREPROCESSING_BIT_CERTIFICATION',{'status':'PASS' if not failures else 'FAIL','mean_bits_exact':736,'scale_bits_exact':736,'mismatch_N':len(failures),'alternate_not_gate':True},'N5 model behavior; score tolerance stays1e-12' if not failures else 'STOP numeric cert fail')
    print(json.dumps({'bit_cert':'PASS' if not failures else 'FAIL','mean':736,'scale':736,'alternate_max_delta':max(x['abs_delta'] for x in alternate)}))
    assert not failures,'V11R1_NUMERIC_CERT_FAIL'
def scalar(r,m):
    p=m['preprocessing'];nf=p['numeric_fields'];raw=[r['numeric'][k] for k in nf]
    x=[0. if v is None else float(v) for v in raw]+[float(v is None) for v in raw]
    x=[(v-a)/s for v,a,s in zip(x,p['numeric_mean'],p['numeric_scale'])]
    for k in p['categorical_fields']:
        vocabulary=p['categorical_train_vocab'][k];value=r['categorical'][k]
        if value not in vocabulary:value='__UNKNOWN__'
        x.extend(float(value==v) for v in vocabulary)
    logit=math.fsum([m['intercept']]+[a*b for a,b in zip(x,m['coef'])])
    return 1/(1+math.exp(-logit)) if logit>=0 else math.exp(logit)/(1+math.exp(logit))
def behavior():
    assert read(OUT/'PREPROCESSING_BIT_CERTIFICATION.json')['status']=='PASS'
    raw=rows(MAIN/'inputs/movement/RUNTIME_CAUSAL.jsonl.gz');rm={r['entry_id']:r for r in raw};savedtrain=rows(V11/'private/MRET_TRAIN_RESUBSTITUTION_SCORES.jsonl.gz');savedOOF=rows(V11/'private/MRET_OOF_SCORES.jsonl.gz');models={b:read(V11/f'private/models/MRET_BLOCK_{b:02d}.json') for b in range(1,9)};train=[];OOF=[];records=[];failures=[]
    for b,m in models.items():
        tm=0.;om=0.;nt=0;no=0
        for source,destination,label in [(savedtrain,train,'TRAIN'),(savedOOF,OOF,'OOF')]:
            for s in source:
                if s['block']!=b:continue
                v=scalar(rm[s['entry_id']],m);delta=abs(v-s['mP']);destination.append({k:s[k] for k in ('entry_id','session','block')}|{'mP':v})
                if delta>1e-12:failures.append({'block':b,'entry_id':s['entry_id'],'kind':label,'delta':delta})
                if label=='TRAIN':tm=max(tm,delta);nt+=1
                else:om=max(om,delta);no+=1
        records.append({'block':b,'train_N':nt,'OOF_N':no,'train_reconstruction_max_delta':tm,'OOF_reconstruction_max_delta':om,'score_tolerance':1e-12})
    assert len(train)==8057 and len(OOF)==1039
    order=lambda data:[r['entry_id'] for r in sorted(data,key=lambda r:(-r['mP'],r['entry_id']))]
    full_order=order(OOF)==order(savedOOF)
    eligible_ids={r['entry_id'] for r in rows(V11/'private/MRET_POST_FIT_EVALUATION_ROWS.jsonl.gz')}
    a=order([r for r in OOF if r['entry_id'] in eligible_ids]);z=order([r for r in savedOOF if r['entry_id'] in eligible_ids])
    top20=a[:math.ceil(len(a)*.2)]==z[:math.ceil(len(a)*.2)];top30=a[:math.ceil(len(a)*.3)]==z[:math.ceil(len(a)*.3)]
    deciles=[list(x) for x in np.array_split(a,10)]==[list(x) for x in np.array_split(z,10)]
    if not(full_order and a==z and top20 and top30 and deciles):failures.append({'kind':'OOF_ORDERING'})
    gzsave(PRIVATE/'CERTIFIED_INDEPENDENT_MRET_TRAIN_SCORES.jsonl.gz',train);gzsave(PRIVATE/'CERTIFIED_INDEPENDENT_MRET_OOF_SCORES.jsonl.gz',OOF)
    result={'status':'PASS' if not failures else 'FAIL','blocks':records,'train_score_N':len(train),'OOF_score_N':len(OOF),'mismatch_N':len(failures),'failures':failures,'OOF_ordering_identity_exact':full_order,'evaluable_ordering_identity_exact':a==z,'top20_exact':top20,'top30_exact':top30,'decile_order_exact':deciles,'saved_score_used_as_runtime_input':False,'newFits':0,'trainer_imports':0,'Safety':SAFETY}
    save(OUT/'MODEL_BEHAVIOR_CERTIFICATION.json',result)
    checkpoint('N5_MODEL_BEHAVIOR_CERTIFICATION',result,'N6 frozen results hash/body audit, no statistical re-evaluation' if not failures else 'STOP score certification fail')
    print(json.dumps({'behavior':result['status'],'OOF_max':max(r['OOF_reconstruction_max_delta'] for r in records),'train_max':max(r['train_reconstruction_max_delta'] for r in records),'ordering_exact':full_order}));assert not failures,'V11R1_NUMERIC_CERT_FAIL'
def frozen():
    authority=read(OUT/'V11_PARENT_AUTHORITY_FREEZE.json')['required_authority_sha256']
    for n,h in authority.items():
        if n.startswith('research/'):p=ROOT/'research/capital-v11-realized-monetization-signal-20261005-v1'/n.split('/')[1]
        else:p=PARENT/n
        assert sha(p)==h
    p=read(PARENT/'MRET_PRIMARY_RESULT.json');q=read(PARENT/'ZERO_FIT_MRET_CONTROL_RESULT.json');conditional=read(PARENT/'POTENTIAL_BUCKET_REALIZED_CONCORDANCE.json');boot=read(PARENT/'SESSION_BOOTSTRAP_RESULT.json');point=read(PARENT/'MRET_POINT_GATE_PENDING_INDEPENDENT_AUDIT.json');gate=read(PARENT/'SIGNAL_GATE_DECISION.json');claim=read(V11/'private/claims/R7_EVALUATION_COMPLETE.json')
    assert p['best_existing_control']==q['best_existing_control']==point['best_existing_control']=='q3'
    assert p['scores']['q3']==q['controls']['q3'] and all(p['scores'][s]==q['controls'][s] for s in q['controls'])
    assert all(conditional['bucket_block'][s]==r['conditional'] for s,r in p['scores'].items())
    assert all(conditional['same_session_bucket'][s]==r['same_session_conditional'] for s,r in p['scores'].items())
    assert claim['results_sha256']==sha(PARENT/'MRET_PRIMARY_RESULT.json') and claim['bootstrap_sha256']==sha(PARENT/'SESSION_BOOTSTRAP_RESULT.json')
    assert boot['seed']==5701105 and boot['resamples']==1999 and point['block_improved_N']==8 and all(point['conditions_before_independent_audit'].values())
    assert gate['gate']['S9'] is False and read(PARENT/'CLOSURE.json')['status']=='V11_CONTRACT_FAIL'
    m=p['scores']['mP'];c=p['scores']['q3'];assert round(m['MRET']['AUC'],6)==.631424 and round(c['MRET']['AUC'],6)==.353206
    assert round(m['MRET']['PR_AUC'],6)==.606552 and round(c['MRET']['PR_AUC'],6)==.398058
    assert round(m['conditional']['concordance'],6)==.598276 and round(c['conditional']['concordance'],6)==.386281
    assert [round(x,6) for x in boot['deltas']['MRET_AUC_delta']['CI95']]==[.220024,.337895]
    assert [round(x,6) for x in boot['deltas']['conditional_delta']['CI95']]==[.152982,.281985]
    countsrows=rows(V11/'private/SESSION_BOOTSTRAP_COUNTS.jsonl.gz');deltarows=rows(V11/'private/SESSION_BOOTSTRAP_DELTAS.jsonl.gz')
    assert len(countsrows)==len(deltarows)==1999
    assert all(r['resample']==i+1 and len(r['counts'])==38 and sum(r['counts'])==38 and all(isinstance(v,int) and v>=0 for v in r['counts']) for i,r in enumerate(countsrows))
    save(OUT/'FROZEN_V11_SIGNAL_EVIDENCE.json',{'status':'HASH_AND_BODY_VALID','primary_sha256':sha(PARENT/'MRET_PRIMARY_RESULT.json'),'conditional_sha256':sha(PARENT/'POTENTIAL_BUCKET_REALIZED_CONCORDANCE.json'),'bootstrap_result_sha256':sha(PARENT/'SESSION_BOOTSTRAP_RESULT.json'),'bootstrap_counts_sha256':sha(V11/'private/SESSION_BOOTSTRAP_COUNTS.jsonl.gz'),'bootstrap_deltas_sha256':sha(V11/'private/SESSION_BOOTSTRAP_DELTAS.jsonl.gz'),'best_existing_control':'q3','mP':{'MRET':m['MRET'],'realized':m['realized'],'bucket_concordance':m['conditional']['concordance']},'q3':{'MRET':c['MRET'],'realized':c['realized'],'bucket_concordance':c['conditional']['concordance']},'block_improved_N':8,'S1_S8':point['conditions_before_independent_audit'],'oldS9':'FAIL','oldV11Status':'V11_CONTRACT_FAIL','bootstrap':boot,'primary_evaluate_runs':0,'bootstrap_reruns':0,'best_control_reselection':0,'newFits':0,'Safety':SAFETY})
    checkpoint('N6_FROZEN_SIGNAL_EVIDENCE_AUDIT','Old S1-S8/primary/conditional/bootstrap hash/body valid; old S9 FAIL preserved; no retest','N7 new S9R decision')
    print(json.dumps({'frozen_evidence':'VALID','old_S9':'FAIL','primary_evaluations':0,'bootstrap_reruns':0}))
def decision():
    source=read(OUT/'PRIVATE_SOURCE_AUDIT.json');reuse=read(OUT/'MRET_COMPLETED_FITS_REUSE_FREEZE.json');matrix=read(OUT/'NUMERIC_MATRIX_CERTIFICATE.json');bit=read(OUT/'PREPROCESSING_BIT_CERTIFICATION.json');behavior=read(OUT/'MODEL_BEHAVIOR_CERTIFICATION.json');signal=read(OUT/'FROZEN_V11_SIGNAL_EVIDENCE.json')
    conditions={'R1':source['status']=='PASS','R2':reuse['reusedMRETFits']==8 and reuse['newFits']==0,'R3':all(r['train_identity_exact'] and r['row_order_exact'] for r in matrix['blocks']),'R4':matrix['status']=='PASS','R5':all(r['checks']['mean_independent_JSON'] for r in bit['blocks']),'R6':all(r['checks']['scale_independent_JSON'] for r in bit['blocks']),'R7':all(r['checks']['mean_JSON_NPZ'] and r['checks']['scale_JSON_NPZ'] for r in bit['blocks']),'R8':all(r['checks']['coef_exact'] and r['checks']['intercept_exact'] and r['checks']['classes_exact'] for r in bit['blocks']),'R9':behavior['status']=='PASS' and max(r['train_reconstruction_max_delta'] for r in behavior['blocks'])<=1e-12,'R10':behavior['status']=='PASS' and max(r['OOF_reconstruction_max_delta'] for r in behavior['blocks'])<=1e-12,'R11':signal['status']=='HASH_AND_BODY_VALID','R12':signal['status']=='HASH_AND_BODY_VALID','R13':all(counts()[k]==0 for k in ['newFits','refits','audit_refits','optimizer_calls','primary_signal_evaluations','bootstrap_reruns','tolerance_relaxation']),'R14':all(v is False for v in SAFETY.values())}
    passed=all(conditions.values());o={'exact_jst':now(),'S9R':'PASS' if passed else 'FAIL','conditions':conditions,'oldV11Status':'V11_CONTRACT_FAIL','oldS9':'FAIL','old_S1_S8':'FROZEN_PASS','monetizationSignal':'MRET_STRONG_CERTIFIED_V11R1' if passed else 'MRET_UNCERTIFIED','CapitalReplayAllowed':passed,'newFits':0,'reusedMRETFits':8,'independent_mismatch_N':0 if passed else sum(not v for v in conditions.values()),'old_failure_overwrite':False,'Safety':SAFETY}
    save(OUT/'S9R_CERTIFICATION_DECISION.json',o);save(PRIVATE/'claims/NUMERICAL_CERTIFICATION_COMPLETE.json',{'exact_jst':now(),'S9R':o['S9R'],'certificate_sha256':sha(OUT/'S9R_CERTIFICATION_DECISION.json'),'reexecution_allowed':False})
    checkpoint('N7_S9R_CERTIFICATION_DECISION',o,'N8 frozen M1/M2 hash reuse; Capital permitted only after canary/audit/claim' if passed else 'N8 failure closure fixed STOP')
    print(json.dumps(o))
if __name__=='__main__':{'matrix':matrix,'preprocess':preprocess,'behavior':behavior,'frozen':frozen,'decision':decision}[sys.argv[1]]()
