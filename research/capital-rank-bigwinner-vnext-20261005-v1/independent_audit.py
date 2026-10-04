"""Independent Fraction/scalar audit. Does not import the primary evaluator.

ROC uses concordant weighted pairs; PR uses grouped cumulative precision.
NumPy is used solely to verify the precommitted session RNG, not metrics.
"""
from collections import Counter
from fractions import Fraction
import gzip
import hashlib
from itertools import groupby
import json
import math
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT.parent
OUT=ROOT/'docs/evidence/capital-rank-bigwinner-vnext-20261005-v1'
INPUTS=WORK/'rank_work/inputs'
PRIVATE=WORK/'rank_work/private'
CHECKS=Counter()
MISMATCH=[]
TOL=1e-12

def read(path):
    with gzip.open(path,'rt') as f:return [json.loads(s) for s in f]

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def check(name,ok,detail=None):
    CHECKS[name]+=1
    if not ok:MISMATCH.append({'check':name,'detail':detail})

def close(name,a,b):
    check(name,(a is None and b is None) or (a is not None and b is not None and abs(a-b)<=TOL),[a,b])

def auc_ap(score,y,weights=None):
    w=weights if weights is not None else [1]*len(y)
    ix=sorted(range(len(y)),key=lambda i:score[i])
    groups=[]
    for value,g in groupby(ix,key=lambda i:score[i]):
        ii=list(g);p=sum(w[i] for i in ii if y[i]);n=sum(w[i] for i in ii if not y[i])
        if p+n:groups.append((p,n))
    pos=sum(p for p,n in groups);neg=sum(n for p,n in groups)
    if not pos or not neg:return None,None
    below=0;concordant=0
    for p,n in groups:
        concordant+=p*(2*below+n);below+=n
    auc=concordant/(2*pos*neg)
    tp=0;seen=0;ap=0.
    for p,n in reversed(groups):
        tp+=p;seen+=p+n
        ap+=(p/pos)*(tp/seen)
    return auc,ap

def bucket(v):
    for i,t in [(4,.10),(3,.05),(2,.03),(1,.02)]:
        if v>=t:return i
    return 0

def audit_metrics(rr,tt,name,expected):
    def sortkey(r):
        if name=='CURRENT_V4_ML':
            return (-r['ML'],-r['m5'],-r['m3'],-r['m2'],r['entry_timestamp'],r['symbol'])
        return (-r['pP'],r['entry_timestamp'],r['symbol'])
    ranked=sorted(rr,key=sortkey)
    score=[r['ML'] if name=='CURRENT_V4_ML' else r['pP'] for r in rr]
    y5=[tt[r['entry_id']]['label_bigwinner5'] for r in rr]
    y10=[tt[r['entry_id']]['label_bigwinner10'] for r in rr]
    check('population_N',len(rr)==expected['N'])
    check('positive_N',sum(y5)==expected['U5_N'] and sum(y10)==expected['U10_N'])
    for head,y in [('U5',y5),('U10',y10)]:
        auc,ap=auc_ap(score,y)
        close('scalar_'+head+'_ROC_AUC',auc,expected[head+'_AUC'])
        close('scalar_'+head+'_PR_AUC',ap,expected[head+'_PR_AUC'])
    h=hashlib.sha256(('\n'.join(r['entry_id'] for r in ranked)+'\n').encode()).hexdigest()
    check('ordering_and_ties_hash',h==expected['ordered_entry_ids_sha256'])
    def top(frac):
        k=math.ceil(frac*len(rr));chosen=ranked[:k]
        p5=sum(tt[r['entry_id']]['label_bigwinner5'] for r in chosen)
        p10=sum(tt[r['entry_id']]['label_bigwinner10'] for r in chosen)
        low=sum(tt[r['entry_id']]['potential_return']<.02 for r in chosen)
        return {'K':k,'U5_N':p5,'U10_N':p10,'below2_N':low,'U5_density':p5/k,
            'U10_density':p10/k,'below2_contamination':low/k,'U5_capture':p5/sum(y5),'U10_capture':p10/sum(y10),
            'ordinal_bucket_N':{str(o):sum(bucket(tt[r['entry_id']]['potential_return'])==o for r in chosen) for o in range(5)}}
    for f in [10,20,30]:
        got=top(f/100);want=expected['top'][str(f)]
        for field,value in got.items():
            if isinstance(value,float):close('top_'+field,value,want[field])
            else:check('top_'+field,value==want[field])
        gains=[2**bucket(tt[r['entry_id']]['potential_return'])-1 for r in ranked]
        dcg=sum(v/math.log2(i+2) for i,v in enumerate(gains[:got['K']]))
        ideal=sum(v/math.log2(i+2) for i,v in enumerate(sorted(gains,reverse=True)[:got['K']]))
        close('NDCG',dcg/ideal,expected['NDCG'][str(f)])
    for point in expected['capture_curve'][1:]:
        got=top(point['fraction'])
        for field in ['K','U5_capture','U10_capture']:
            close('capture_curve_'+field,got[field],point[field])
    session_days=sorted({r['session'] for r in rr})
    for k in (3,5):
        chosen=[r for d in session_days for r in [z for z in ranked if z['session']==d][:k]]
        want=expected['session_top3_top5'][str(k)]
        check('session_top_K',len(chosen)==want['selected_N'])
        for h in ('5','10'):
            close('session_top_U'+h,sum(tt[r['entry_id']]['label_bigwinner'+h] for r in chosen)/len(chosen),want['U'+h+'_density'])
    # Independent average score rank for every ordinal bucket, including ties.
    score_ranks={}
    sorted_score=sorted(range(len(rr)),key=lambda i:score[i]);before=0
    for value,g in groupby(sorted_score,key=lambda i:score[i]):
        ids=list(g);avg=(before+1+before+len(ids))/2
        for i in ids:score_ranks[i]=(avg-1)/(len(rr)-1)
        before+=len(ids)
    means=[]
    for want in expected['ordinal_buckets']:
        ids=[i for i,r in enumerate(rr) if bucket(tt[r['entry_id']]['potential_return'])==want['ordinal']]
        check('ordinal_bucket_N',len(ids)==want['N'])
        mean=sum(score_ranks[i] for i in ids)/len(ids) if ids else None
        close('ordinal_rank_mean',mean,want['mean_rank_percentile'])
        means.append(mean)
    check('ordinal_ordering_status',all(a>b for a,b in zip(means,means[1:]) if a is not None and b is not None)==expected['ordinal_mean_rank_strictly_ordered'])
    prob=[r['p5'] if name=='CURRENT_V4_ML' else r['pP'] for r in rr]
    close('Brier_diagnostic',sum((p-y)**2 for p,y in zip(prob,y5))/len(rr),expected['calibration']['U5_Brier'])
    eps=2.220446049250313e-16
    ll=-sum(y*math.log(min(1-eps,max(eps,p)))+(1-y)*math.log(1-min(1-eps,max(eps,p))) for p,y in zip(prob,y5))/len(rr)
    close('logloss_diagnostic',ll,expected['calibration']['U5_logloss'])
    return {head:auc_ap(score,y) for head,y in [('U5',y5),('U10',y10)]},top(.2)

def quantile(values,q):
    s=sorted(values);at=(len(s)-1)*q;lo=math.floor(at);hi=math.ceil(at)
    return s[lo]+(s[hi]-s[lo])*(at-lo)

def main():
    result=json.loads((OUT/'STAGE_A_RESULT.json').read_text())
    spec=json.loads((OUT/'TOURNAMENT_PRECOMMIT.json').read_text())
    check('tolerance_precommitted',spec['float_tolerance']==TOL)
    recovery=json.loads((OUT/'INPUT_BYTE_RECOVERY.json').read_text())
    for record in recovery['checks']:
        check('saved_original_artifact_hash',digest(WORK/record['local_relative'])==record['sha256'])
    manifest=json.loads((OUT/'COMMON_EVAL_MASK_FREEZE.json').read_text())
    mask=read(PRIVATE/'COMMON_EVAL_MASK.jsonl.gz');ledger=read(PRIVATE/'TEACHER_SUPPORT_LEDGER.jsonl.gz')
    check('common_mask_hash',digest(PRIVATE/'COMMON_EVAL_MASK.jsonl.gz')==manifest['mask_sha256']==result['mask_sha256'])
    teacher_audit=json.loads((OUT/'TEACHER_CONTRACT_AUDIT.json').read_text())
    check('teacher_support_ledger_hash',digest(PRIVATE/'TEACHER_SUPPORT_LEDGER.jsonl.gz')==teacher_audit['ledger_sha256'])
    current=read(INPUTS/'v4/capital_staircase_v4_private/UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz')
    move=read(INPUTS/'movement/MOVE_P5_SCORE_STREAM.jsonl.gz')
    runtime=read(INPUTS/'movement/RUNTIME_CAUSAL.jsonl.gz')
    tt={r['entry_id']:r for r in read(INPUTS/'v4/inputs/v3/capital_v2_private/TEACHERS_EVALUATION.jsonl.gz')}
    books={r['entry_id']:r for r in read(INPUTS/'v4/inputs/v3/bigwinner_private/MARKET_EXECUTION_BOOK_V2.jsonl.gz')}
    frozen={r['watch_key']:r for r in read(INPUTS/'v4/inputs/v3/work_inputs/exit_v2/FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz') if r['entry_status']=='FIRST_ENTRY'}
    rt={r['entry_id']:r for r in runtime};cc={r['entry_id']:r for r in current};mm={r['entry_id']:r for r in move}
    check('candidate_identity_sets',set(rt)==set(tt)==set(books)==set(frozen) and set(cc)==set(mm))
    audit_rows={r['entry_id']:r for r in ledger};maskrows={r['entry_id']:r for r in mask}
    support_counts=Counter();nohigh=[]
    for key,r in rt.items():
        b=books[key];f=frozen[key];record=audit_rows[key]
        check('exact_entry_identity',(r['session'],r['symbol'],r['entry_minute'],r['entry_timestamp'])==(f['session'],f['symbol'],f['fill_minute'],f['fill_timestamp']))
        check('raw_entry_reference',abs(Fraction(r['raw_reference'])*Fraction(2001,2000)-Fraction(str(f['fill_price'])))<=Fraction(1,10**8))
        check('actual_entry_source',b['entry_actual_source']['O']==r['raw_reference'])
        source=b.get('source') or {};complete=bool(b['capture_complete'] and source.get('terminal_pagination_proven') and source.get('date_scope_complete'))
        check('capture_authority',complete==record['capture_complete']==tt[key]['capture_complete'])
        later=[]
        for z in b['market']:
            if not r['entry_minute']<z['minute']<920:continue
            v={k:Fraction(z[k]) for k in ('O','H','L','C','Vo','Va')}
            good=bool(z.get('lineage')) and all(vv>0 for vv in v.values()) and v['L']<=min(v['O'],v['C'])<=max(v['O'],v['C'])<=v['H']
            if good:later.append(v['H'])
        if not later:nohigh.append(key)
        value=max(later)/Fraction(r['raw_reference'])-1 if later else Fraction(0) if complete else None
        check('strict_later_high_support',len(later)==record['strict_later_actual_high_N'])
        for head,threshold in [('U5',Fraction(1,20)),('U10',Fraction(1,10))]:
            if r['entry_minute']>=920:status='NOT_MATURE';y=None
            elif value is not None and later and value>=threshold:status='KNOWN_POSITIVE';y=1
            elif complete:status='KNOWN_NEGATIVE_COMPLETE_CAPTURE';y=0
            elif not source:status='SOURCE_UNAVAILABLE';y=None
            else:status='UNSUPPORTED_UNKNOWN';y=None
            check('teacher_known_unknown',status==record['status_'+head] and y==record['label_'+head])
            support_counts[head+'_'+status]+=1
            if y is not None:check('teacher_label_identity',y==tt[key]['label_bigwinner'+head[1:]])
        if value is not None:close('potential_teacher_exact_raw_high',float(value),tt[key]['potential_return'])
        p=r['provenance'];m=r['movement_provenance']
        check('core_asof',p['max_known_minute'] is None or p['max_known_minute']<=r['entry_minute'])
        check('movement_asof',m['current_max_source_minute'] is None or m['current_max_source_minute']<r['entry_minute'])
        check('prior_dates_asof',all(d<r['session'] for d in m['prior20_calendar_dates']+m['prior5_calendar_dates']))
        check('no_runtime_teacher_feature',not any(k in r['numeric'] for k in ['future_high','realized_net_return','frozen_exit','potential_return']))
        if key in cc:
            expected=(r['entry_minute']<920 and record['label_U5'] is not None and record['label_U10'] is not None)
            check('OOF_mask_membership',maskrows[key]['included']==expected)
            check('common_score_identity',all(cc[key][k]==mm[key][k]==r[k] for k in ['entry_id','session','symbol','entry_timestamp','entry_minute','raw_reference']))
            close('saved_current_ML_formula',cc[key]['ML'],(cc[key]['m2']+cc[key]['m3']+cc[key]['m5'])/(cc[key]['base2']+cc[key]['base3']+cc[key]['base5']))
            close('saved_MOVE_score_relation',mm[key]['liftP'],mm[key]['pP']/mm[key]['baseP'])
    check('54_contract_resolution',len(nohigh)==54 and sum(rt[k]['entry_minute']<920 for k in nohigh)==32)
    accepted=[r['entry_id'] for r in current if maskrows[r['entry_id']]['included']]
    check('ordered_common_identity_hash',hashlib.sha256(('\n'.join(accepted)+'\n').encode()).hexdigest()==manifest['ordered_identity_sha256'])
    check('primary_mask_N',len(accepted)==1028)
    for block in range(1,9):
        model=json.loads((INPUTS/f'movement/models/MOVE_P_BLOCK_{block:02d}.json').read_text())
        training=[rt[k] for k in model['train_entry_ids']]
        check('OOF_training_identity_unique',len(training)==len({r['entry_id'] for r in training})==model['train_N'])
        check('OOF_strict_past_training',all(r['session']<min(model['test_dates']) and r['entry_minute']<920 for r in training))
        check('OOF_training_complete_known',all(audit_rows[r['entry_id']]['label_U5'] is not None for r in training))
        check('OOF_original_positive_count',sum(tt[r['entry_id']]['label_bigwinner5'] for r in training)==model['train_positive_N'])
        check('OOF_feature_manifest',len(model['preprocessing']['numeric_fields'])==46 and len(model['preprocessing']['categorical_fields'])==7)
        for r in [r for r in move if r['block']==block]:
            check('saved_score_model_lineage',r['P_model_sha256']==digest(INPUTS/f'movement/models/MOVE_P_BLOCK_{block:02d}.json'))
            check('OOF_test_membership',r['session'] in model['test_dates'] and r['entry_id'] not in model['train_entry_ids'])
    cr=[cc[k] for k in accepted];mr=[mm[k] for k in accepted]
    audit_metrics(current,tt,'CURRENT_V4_ML',result['LEGACY_CURRENT'])
    c,ctop=audit_metrics(cr,tt,'CURRENT_V4_ML',result['rank_metrics']['CURRENT_V4_ML'])
    m,mtop=audit_metrics(mr,tt,'EXISTING_MOVE_P5',result['rank_metrics']['EXISTING_MOVE_P5'])
    deltas=[];catastrophe=[]
    for b in result['blocks']:
        block=b['block']
        bc,_=audit_metrics([r for r in cr if r['block']==block],tt,'CURRENT_V4_ML',b['CURRENT_V4_ML'])
        bm,_=audit_metrics([r for r in mr if r['block']==block],tt,'EXISTING_MOVE_P5',b['EXISTING_MOVE_P5'])
        d=bm['U5'][0]-bc['U5'][0];deltas.append(d)
        close('block_U5_delta',d,b['delta_U5_AUC'])
        close('block_U10_delta',bm['U10'][0]-bc['U10'][0],b['delta_U10_AUC'])
        if any(bm[h][0]<.5<=bc[h][0] and bm[h][0]-bc[h][0]<=-.10 for h in ('U5','U10')):catastrophe.append(block)
    draws=read(PRIVATE/'BOOTSTRAP_SESSION_DRAWS.jsonl.gz')
    check('bootstrap_saved_input_hash',digest(PRIVATE/'BOOTSTRAP_SESSION_DRAWS.jsonl.gz')==result['bootstrap']['inputs_sha256'])
    sessions=sorted({r['session'] for r in cr});check('bootstrap_cluster_identity',sessions==result['bootstrap']['sessions'])
    rng=np.random.default_rng(spec['bootstrap']['seed'])
    y5=[tt[r['entry_id']]['label_bigwinner5'] for r in cr];y10=[tt[r['entry_id']]['label_bigwinner10'] for r in cr]
    ss={d:i for i,d in enumerate(sessions)};row_si=[ss[r['session']] for r in cr]
    cs=[r['ML'] for r in cr];ms=[r['pP'] for r in mr]
    boot={k:[] for k in ['U5_AUC','U5_PR_AUC','U10_AUC','U10_PR_AUC']}
    for i,draw in enumerate(draws):
        got=np.bincount(rng.integers(0,len(sessions),len(sessions)),minlength=len(sessions)).tolist()
        check('bootstrap_RNG_input_sequence',draw['replicate']==i and got==draw['session_counts'])
        w=[got[j] for j in row_si]
        if any(sum(w[i] for i,yy in enumerate(y) if yy==label)==0 for y in (y5,y10) for label in (0,1)):continue
        for head,y in [('U5',y5),('U10',y10)]:
            ac,pc=auc_ap(cs,y,w);am,pm=auc_ap(ms,y,w)
            boot[head+'_AUC'].append(am-ac);boot[head+'_PR_AUC'].append(pm-pc)
    for metric,vals in boot.items():
        want=result['bootstrap']['delta_candidate_minus_current'][metric]
        check('bootstrap_valid_N',len(vals)==want['valid'])
        for q,v in zip([.025,.975],want['CI95']):close('bootstrap_CI',quantile(vals,q),v)
        close('bootstrap_mean',sum(vals)/len(vals),want['mean'])
        close('bootstrap_direction',sum(v>0 for v in vals)/len(vals),want['positive_replicate_fraction'])
    gates={'A':{'U5_AUC':m['U5'][0]>c['U5'][0],'U5_PR_AUC':m['U5'][1]>c['U5'][1],
        'top20_U5':mtop['U5_density']>ctop['U5_density']},
        'B':{'U10_AUC':m['U10'][0]>=c['U10'][0],'U10_PR_AUC':m['U10'][1]>=c['U10'][1],
        'top20_U10':mtop['U10_density']>=ctop['U10_density']},
        'C':{'below2':mtop['below2_contamination']<=ctop['below2_contamination']},
        'D':{'U5_improved_blocks_ge5':sum(d>0 for d in deltas)>=5,'no_catastrophic_block_failure':not catastrophe}}
    for letter,g in gates.items():check('selection_point_gate',g==result['gates'][letter])
    point=all(v for g in gates.values() for v in g.values())
    lo,hi=[quantile(boot['U5_AUC'],q) for q in [.025,.975]]
    status='RANK_VNEXT_STRONG' if point and lo>0 else 'RANK_VNEXT_PROMISING' if point and lo<=0<=hi else 'RANK_VNEXT_NO_GO'
    check('final_rank_status',status==result['gates']['preliminary_status'])
    check('selected_candidate',result['selectedRankCandidate']==('EXISTING_MOVE_P5' if point else None))
    check('Stage_B_not_executed',not list((PRIVATE/'models').glob('*')) and not list(PRIVATE.glob('*P10*')))
    output={'exact_jst':datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(),'method':'Separate Fraction identity/teacher audit + scalar grouped ROC/AP/top/NDCG/bootstrap; primary evaluator not imported',
        'float_tolerance':TOL,'count_order_identity_tolerance':0,'checks_N':sum(CHECKS.values()),'checks_by_family':dict(CHECKS),
        'mismatch_N':len(MISMATCH),'mismatches':MISMATCH,'independently_selected_status':status if not MISMATCH else 'AUDIT_BLOCKED',
        'candidate':'EXISTING_MOVE_P5' if point and not MISMATCH else None,'U5_improved_blocks':sum(d>0 for d in deltas),
        'catastrophic_blocks':catastrophe,'train_percentile_and_BIGWIN_DUAL':'NOT_APPLICABLE; Stage B skipped at Stage A winner',
        'primary_evaluator_sha256':digest(Path(__file__).parent/'evaluate.py'),
        'auditor_sha256':digest(Path(__file__)),'STAGE_A_RESULT_sha256':digest(OUT/'STAGE_A_RESULT.json'),
        'shared_IO_limitation':'Frozen upstream sources, archive artifacts and session RNG API are shared. This tests independent computation; it does not certify external source truth or live as-of arrivals.',
        'new_fits':0,'capital_replays':0,'protected_fresh_opened':0}
    with (OUT/'INDEPENDENT_AUDIT.json').open('x') as f:f.write(json.dumps(output,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'checks':sum(CHECKS.values()),'mismatch_N':len(MISMATCH),'status':output['independently_selected_status'],'first_mismatches':MISMATCH[:5]}))
    if MISMATCH:raise SystemExit('INDEPENDENT_AUDIT_MISMATCH_STOP')

if __name__=='__main__':main()
