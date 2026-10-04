"""One saved-score tournament. No fitting, score regeneration, or Capital replay."""
import math
from collections import Counter
import json
import numpy as np
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, log_loss
from scipy.stats import rankdata
from control import ROOT, INPUTS, OUT, PRIVATE, rows, now, save, sha, gzsave, checkpoint

CURRENT='CURRENT_V4_ML'
MOVE='EXISTING_MOVE_P5'

def ordinal(v):
    return 4 if v>=.10 else 3 if v>=.05 else 2 if v>=.03 else 1 if v>=.02 else 0

def key(r,name):
    if name==CURRENT:
        return (-r['ML'],-r['m5'],-r['m3'],-r['m2'],r['entry_timestamp'],r['symbol'])
    return (-r['pP'],r['entry_timestamp'],r['symbol'])

def metrics(rr,teachers,name):
    score=np.array([r['ML'] if name==CURRENT else r['pP'] for r in rr])
    potential=np.array([teachers[r['entry_id']]['potential_return'] for r in rr])
    y5=np.array([teachers[r['entry_id']]['label_bigwinner5'] for r in rr])
    y10=np.array([teachers[r['entry_id']]['label_bigwinner10'] for r in rr])
    order=sorted(range(len(rr)),key=lambda i:key(rr[i],name))
    ords=np.array([ordinal(v) for v in potential]); gains=np.power(2,ords)-1
    def auc(y):return float(roc_auc_score(y,score)) if len(set(y))==2 else None
    def ap(y):return float(average_precision_score(y,score)) if y.sum() else None
    def top(fraction):
        k=math.ceil(len(rr)*fraction);ii=order[:k]
        return {'K':k,'U5_N':int(y5[ii].sum()),'U10_N':int(y10[ii].sum()),
            'below2_N':int((potential[ii]<.02).sum()),'U5_density':float(y5[ii].mean()),
            'U10_density':float(y10[ii].mean()),'below2_contamination':float((potential[ii]<.02).mean()),
            'U5_capture':float(y5[ii].sum()/y5.sum()),'U10_capture':float(y10[ii].sum()/y10.sum()),
            'ordinal_bucket_N':{str(o):int((ords[ii]==o).sum()) for o in range(5)}}
    def ndcg(fraction):
        k=math.ceil(len(rr)*fraction);denom=np.log2(np.arange(2,k+2))
        ideal=np.sort(gains)[::-1][:k]
        return float(np.sum(gains[order[:k]]/denom)/np.sum(ideal/denom))
    percent=(rankdata(score,method='average')-1)/(len(rr)-1)
    buckets=[]
    for o,label in [(4,'>=10'),(3,'5-<10'),(2,'3-<5'),(1,'2-<3'),(0,'<2')]:
        take=ords==o
        buckets.append({'bucket':label,'ordinal':o,'N':int(take.sum()),
            'mean_score':float(score[take].mean()) if take.any() else None,
            'median_score':float(np.median(score[take])) if take.any() else None,
            'mean_rank_percentile':float(percent[take].mean()) if take.any() else None})
    session=[]
    for day in sorted({r['session'] for r in rr}):
        ids=[i for i in order if rr[i]['session']==day]
        counts={}
        for k in (3,5):
            take=ids[:k]
            counts[str(k)]={'K':len(take),'U5_N':int(y5[take].sum()),'U10_N':int(y10[take].sum())}
        session.append({'session':day,'top':counts})
    session_summary={}
    for k in (3,5):
        n=sum(s['top'][str(k)]['K'] for s in session)
        session_summary[str(k)]={'selected_N':n,'U5_density':sum(s['top'][str(k)]['U5_N'] for s in session)/n,
            'U10_density':sum(s['top'][str(k)]['U10_N'] for s in session)/n,'diagnostic_only':True}
    probability=np.array([r['p5'] if name==CURRENT else r['pP'] for r in rr])
    calibration={'U5_probability_field':'p5 diagnostic head' if name==CURRENT else 'pP diagnostic only',
        'U5_Brier':float(brier_score_loss(y5,probability)),'U5_logloss':float(log_loss(y5,probability,labels=[0,1])),
        'U10_Brier':None,'U10_logloss':None,'U10_reason':'No trained U10 probability head in this saved Rank',
        'main_rank_probability_calibration_claim':False,'selection_primary':False}
    return {'N':len(rr),'U5_N':int(y5.sum()),'U10_N':int(y10.sum()),'U5_AUC':auc(y5),'U5_PR_AUC':ap(y5),
        'U10_AUC':auc(y10),'U10_PR_AUC':ap(y10),'top':{str(int(f*100)):top(f) for f in (.1,.2,.3)},
        'capture_curve':[{'fraction':0,'K':0,'U5_capture':0,'U10_capture':0}]+[
            {'fraction':f/100,**top(f/100)} for f in range(1,101)],
        'ordinal_buckets':buckets,
        'ordinal_mean_rank_strictly_ordered':all(a['mean_rank_percentile']>b['mean_rank_percentile'] for a,b in zip(buckets,buckets[1:]) if a['N'] and b['N']),
        'NDCG':{str(int(f*100)):ndcg(f) for f in (.1,.2,.3)},
        'session_top3_top5':session_summary,'session_details':session,'calibration':calibration,
        'ordered_entry_ids_sha256':__import__('hashlib').sha256(('\n'.join(rr[i]['entry_id'] for i in order)+'\n').encode()).hexdigest()}

def bootstrap(rr,teacher,current,move,spec):
    sessions=sorted({r['session'] for r in rr});si={s:i for i,s in enumerate(sessions)}
    row_sessions=np.array([si[r['session']] for r in rr])
    y5=np.array([teacher[r['entry_id']]['label_bigwinner5'] for r in rr])
    y10=np.array([teacher[r['entry_id']]['label_bigwinner10'] for r in rr])
    cs=np.array([current[r['entry_id']]['ML'] for r in rr]);ms=np.array([move[r['entry_id']]['pP'] for r in rr])
    rng=np.random.default_rng(spec['seed']);counts=[];deltas={'U5_AUC':[],'U5_PR_AUC':[],'U10_AUC':[],'U10_PR_AUC':[]}
    for replicate in range(spec['resamples']):
        weights=np.bincount(rng.integers(0,len(sessions),len(sessions)),minlength=len(sessions))
        counts.append({'replicate':replicate,'session_counts':weights.tolist()})
        w=weights[row_sessions]
        if any(sum(w[y==label])==0 for y in (y5,y10) for label in (0,1)):
            continue
        for head,y in [('U5',y5),('U10',y10)]:
            deltas[head+'_AUC'].append(float(roc_auc_score(y,ms,sample_weight=w)-roc_auc_score(y,cs,sample_weight=w)))
            deltas[head+'_PR_AUC'].append(float(average_precision_score(y,ms,sample_weight=w)-average_precision_score(y,cs,sample_weight=w)))
    gzsave(PRIVATE/'BOOTSTRAP_SESSION_DRAWS.jsonl.gz',counts)
    return {'unit':'session cluster; paired same38 sessions','seed':spec['seed'],'requested':spec['resamples'],
        'sessions':sessions,'inputs_sha256':sha(PRIVATE/'BOOTSTRAP_SESSION_DRAWS.jsonl.gz'),
        'delta_candidate_minus_current':{k:{'valid':len(v),'mean':float(np.mean(v)),
            'CI95':np.quantile(v,[.025,.975]).tolist(),'positive_replicate_fraction':float(np.mean(np.array(v)>0))} for k,v in deltas.items()}}

def point_gates(current,move,blocks,boot):
    c,m=current,move
    A={'U5_AUC':m['U5_AUC']>c['U5_AUC'],'U5_PR_AUC':m['U5_PR_AUC']>c['U5_PR_AUC'],
        'top20_U5':m['top']['20']['U5_density']>c['top']['20']['U5_density']}
    B={'U10_AUC':m['U10_AUC']>=c['U10_AUC'],'U10_PR_AUC':m['U10_PR_AUC']>=c['U10_PR_AUC'],
        'top20_U10':m['top']['20']['U10_density']>=c['top']['20']['U10_density']}
    C={'below2':m['top']['20']['below2_contamination']<=c['top']['20']['below2_contamination']}
    improved=sum(b['delta_U5_AUC']>0 for b in blocks)
    catastrophe=[b['block'] for b in blocks if any(b[MOVE][head]<.5<=b[CURRENT][head] and b['delta_'+head]<=-.10 for head in ('U5_AUC','U10_AUC'))]
    D={'U5_improved_blocks_ge5':improved>=5,'no_catastrophic_block_failure':not catastrophe}
    point=all(v for group in (A,B,C,D) for v in group.values())
    lo,hi=boot['delta_candidate_minus_current']['U5_AUC']['CI95']
    status='RANK_VNEXT_STRONG' if point and lo>0 else 'RANK_VNEXT_PROMISING' if point and lo<=0<=hi else 'RANK_VNEXT_NO_GO'
    return {'A':A,'B':B,'C':C,'D':D,'U5_improved_block_N':improved,'catastrophic_blocks':catastrophe,
        'E':'PENDING_INDEPENDENT_AUDIT','preliminary_status':status,'point_gates_PASS':point}

def main():
    spec=json.loads((OUT/'TOURNAMENT_PRECOMMIT.json').read_text())
    assert spec['stage']=='A' and spec['new_fit_budget']==0
    current=rows(INPUTS/'v4/capital_staircase_v4_private/UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz')
    move=rows(INPUTS/'movement/MOVE_P5_SCORE_STREAM.jsonl.gz')
    teacher={r['entry_id']:r for r in rows(INPUTS/'v4/inputs/v3/capital_v2_private/TEACHERS_EVALUATION.jsonl.gz')}
    mask=rows(PRIVATE/'COMMON_EVAL_MASK.jsonl.gz');accepted={r['entry_id'] for r in mask if r['included']}
    cm={r['entry_id']:r for r in current};mm={r['entry_id']:r for r in move}
    legacy=metrics(current,teacher,CURRENT)
    expected=json.loads((ROOT/'docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/HEAD_DIAGNOSTICS.json').read_text())['ML']
    assert abs(legacy['U5_AUC']-expected['cross_target_AUC']['U5'])<=spec['float_tolerance']
    assert abs(legacy['U10_AUC']-expected['cross_target_AUC']['U10'])<=spec['float_tolerance']
    for field,k in [('U5_density','U5'),('U10_density','U10')]:
        assert legacy['top']['20'][field]==expected['top20_rates'][k]
    assert legacy['top']['20']['below2_contamination']==expected['top20_below2_contamination']
    cr=[r for r in current if r['entry_id'] in accepted];mr=[mm[r['entry_id']] for r in cr]
    c=metrics(cr,teacher,CURRENT);m=metrics(mr,teacher,MOVE)
    block_metrics=[]
    for block in range(1,9):
        bc=metrics([r for r in cr if r['block']==block],teacher,CURRENT)
        bm=metrics([r for r in mr if r['block']==block],teacher,MOVE)
        block_metrics.append({'block':block,CURRENT:bc,MOVE:bm,
            'delta_U5_AUC':bm['U5_AUC']-bc['U5_AUC'],'delta_U10_AUC':bm['U10_AUC']-bc['U10_AUC']})
    boot=bootstrap(cr,teacher,cm,mm,spec['bootstrap'])
    gates=point_gates(c,m,block_metrics,boot)
    result={'exact_jst':now(),'stage':'A','rank_metrics':{CURRENT:c,MOVE:m},'LEGACY_CURRENT':legacy,
        'SUPPORTED_ONLY_CURRENT':c,'blocks':block_metrics,'bootstrap':boot,'gates':gates,
        'PRR':'NOT_COMPARABLE both heads; no forced join',
        'mask_sha256':sha(PRIVATE/'COMMON_EVAL_MASK.jsonl.gz'),'precommit_sha256':sha(OUT/'TOURNAMENT_PRECOMMIT.json'),
        'fits':0,'replays':0,'selectedRankCandidate':MOVE if gates['point_gates_PASS'] else None,
        'selection_pending_independent_audit':True}
    save(OUT/'STAGE_A_RESULT.json',result)
    checkpoint('R5_EXISTING_SCORE_TOURNAMENT_RESULT','STAGE_A_FIXED_RESULTS_PENDING_INDEPENDENT_AUDIT',
        ['Current1039 exact legacy reference reproduced','Current and MOVE compared on same1028 candidate identities','Session bootstrap computed on same38 clusters'],
        {'preliminary_status':gates['preliminary_status'],'point_gates':gates,'fits':0,'replays':0},
        'If point gates pass, independent audit then fix Rank candidate and skip Stage B; otherwise only precommitted MOVE_P10 eight fits permitted')
    print(json.dumps({'supported_current':{k:c[k] for k in ['U5_AUC','U5_PR_AUC','U10_AUC','U10_PR_AUC']},
        'MOVE':{k:m[k] for k in ['U5_AUC','U5_PR_AUC','U10_AUC','U10_PR_AUC']},
        'top20':{CURRENT:c['top']['20'],MOVE:m['top']['20']},'gates':gates,'bootstrap':boot['delta_candidate_minus_current']}))

if __name__=='__main__':main()
