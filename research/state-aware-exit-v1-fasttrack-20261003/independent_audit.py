"""Fit-free second implementation: labels, OOF transforms, event ordering and metrics.

Does not import producer teacher/replay/evaluator arithmetic. Pickled Preprocessor
class is resolved for object loading only; its transform is not used here.
"""
import collections, gzip, hashlib, json, math, pickle
from pathlib import Path
import numpy as np
from exit_common import HERE, ENTRY, STATE, SOURCE, now, sha, read, write, lines, SAFETY
from model_oof import Preprocessor  # pickle class binding only; fit calls remain zero

def normalize(rows):
    good=[]
    for r in rows:
        if len(r)!=7 or not all(math.isfinite(float(v)) for v in r):continue
        if not(0<r[3]<=min(r[1],r[4])<=max(r[1],r[4])<=r[2] and r[5]>=0 and r[6]>=0):continue
        good.append(r)
    assert len(good)==len({r[0] for r in good})
    return sorted(good,key=lambda r:r[0])
def regular(day):
    return [x for x in range(541,690)]+[x for x in range(751,900 if day<'2024-11-05' else 925)]
def terminal(day):return 900 if day<'2024-11-05' else 930
def median(values):return float(np.median(values)) if values else None
def close(a,b):
    return (a is None and b is None) or (a is not None and b is not None and abs(float(a)-float(b))<=1e-8)

def run():
    assert not (HERE/'INDEPENDENT_EXIT_AUDIT.json').exists(),'NO_AUDIT_OVERWRITE'
    issues=[];checks=collections.Counter()
    def check(name,ok,detail=None):
        checks[name]+=1
        if not ok:issues.append({'check':name,'detail':detail})
    identity=read(HERE/'UPSTREAM_IDENTITY_RECEIPT.json')
    for rel,receipt in identity['inputs'].items():check('immutable_upstream_input_hash',sha(HERE.parents[2]/rel)==receipt['sha256'],rel)
    for p in identity['source_checks']:check('exact_latest_RC2_source_hash',sha(STATE/'FROZEN_RC2_SOURCE'/p['path'])==p['sha256'],p['path'])
    feature=read(HERE/'FEATURE_FREEZE.json');entryfeature=read(ENTRY/'FEATURE_FREEZE.json')
    check('P1_feature_manifest_exact',feature['numeric']==entryfeature['P1_numeric'] and feature['categorical']==entryfeature['P1_categorical'])
    check('Legacy_State_feature0',not any('legacy' in x.lower() for x in feature['numeric']+feature['categorical']) and feature['Legacy_State']==0)
    grid=list(lines(ENTRY/'PERSISTENT_GRID.jsonl.gz'));meta=list(lines(ENTRY/'STATE_FEATURE_METADATA.jsonl.gz'));source=read(SOURCE);rows={k:normalize(v['today']) for k,v in source.items()}
    bywatch=collections.defaultdict(list)
    for i,r in enumerate(grid):
        bywatch[r['watch_key']].append(i);t=r['intent_minute'];m=meta[i]
        check('closed_every_observed_minute_cutoff',r['closed_raw_start']==t-1 and r['feature_max_timestamp']<=r['intent_timestamp'],i)
        check('State_timestamp_causal',m['row_index']==i and (m['state_as_of_minute'] is None or m['state_as_of_minute']<=t),i)
        check('lunch_no_decision',t<=690 or 751<=t<=terminal(r['session']),i)
    labels=list(lines(HERE/'TEACHER_LABELS.jsonl.gz'));Y=np.load(HERE/'PRIVATE_INPUTS/targets.npy');independent_y=np.full(len(grid),np.nan)
    for key,idx in bywatch.items():
        day=grid[idx[0]]['session'];a=rows[key];allowed=set(regular(day));last=[r for r in a if r[0]==terminal(day)]
        ops=[(int(r[0]),float(r[1])*.9995) for r in a if r[0] in allowed]
        if last:ops.append((terminal(day),last[-1][4]*.9995))
        mins=np.asarray([x[0] for x in ops]);prices=np.asarray([x[1] for x in ops]);prefix=np.concatenate(([0.],np.cumsum(prices)))
        for i in idx:
            t=grid[i]['intent_minute'];j=int(np.searchsorted(mins,t))
            if last and j<len(ops)-1:
                remaining_sum=prefix[-1]-prefix[j+1];average=remaining_sum/(len(ops)-j-1);raw=100*(average/prices[j]-1);independent_y[i]=min(10,max(-10,raw))
                check('teacher_raw_independent',close(raw,labels[i]['target_raw_pct']),i)
            expected=None if not np.isfinite(independent_y[i]) else float(independent_y[i]);actual=None if not np.isfinite(Y[i]) else float(Y[i])
            check('teacher_target_independent',close(expected,actual) and close(expected,labels[i]['target']),i)
    cfg=read(HERE/'MODEL_POLICY_FREEZE.json');ledger=read(HERE/'FIT_LEDGER.json');splits=read(HERE/'SPLIT_PRECOMMIT.json')['folds'];session=np.asarray([r['session'] for r in grid]);X=np.load(ENTRY/'PRIVATE_INPUTS/features_numeric.npy',mmap_mode='r');C=np.load(ENTRY/'PRIVATE_INPUTS/features_categories.npy',mmap_mode='r');vocab=read(ENTRY/'PRIVATE_INPUTS/category_vocabulary.json')
    check('exact5_new_EXIT_fits',ledger['fits_completed']==ledger['fits_reserved']==ledger['hard_cap']==5 and ledger['Entry_fits']==ledger['Hard1_fits']==0)
    pred=np.full(len(grid),np.nan);fold_of=np.zeros(len(grid),int)
    with np.load(HERE/'PRIVATE_INPUTS/exit_oof.npz') as z:pred[z['row_indices']]=z['predictions'];fold_of[z['row_indices']]=z['fold']
    for f in splits:
        n=f['id'];tr=np.flatnonzero(np.isin(session,f['train'])&np.isfinite(independent_y));te=np.flatnonzero(np.isin(session,f['test']));rec=next(x for x in ledger['runs'] if x['fold']==n)
        check('temporal_split',max(session[tr])<min(session[te]) and not(set(session[tr])&set(session[te])) and f['purge'] not in set(session[tr])|set(session[te]),n)
        check('train_test_eligibility',np.array_equal(tr,np.load(HERE/f'PRIVATE_MODELS/F{n}_train_indices.npy')) and np.array_equal(te,np.load(HERE/f'PRIVATE_MODELS/F{n}_test_indices.npy')),n)
        check('train_target_lineage',np.allclose(independent_y[tr],np.load(HERE/f'PRIVATE_MODELS/F{n}_train_targets.npy'),atol=1e-8,rtol=0),n)
        prep=pickle.loads((HERE/f'PRIVATE_MODELS/F{n}_preprocessor.pkl').read_bytes());model=pickle.loads((HERE/f'PRIVATE_MODELS/F{n}_HOLD_VALUE.pkl').read_bytes())
        check('fixed_model_parameters',all(model.get_params()[k]==v for k,v in cfg['parameters'].items()),n)
        with __import__('warnings').catch_warnings():
            __import__('warnings').simplefilter('ignore');expected=np.nanmedian(X[tr],axis=0)
        expected=np.where(np.isfinite(expected),expected,0.)
        check('train_only_numeric_median',np.array_equal(prep.median,expected) and prep.training_rows==len(tr),n)
        for j in range(C.shape[1]):
            ks=set(map(int,C[tr,j]));ks.update(vocab[j].index(v) for v in ('__MISSING__','__UNKNOWN_HISTORY__','__FORMAL_NULL__') if v in vocab[j]);check('train_only_onehot',prep.known[j]==sorted(ks),(n,j))
        check('model_preprocessor_lineage',sha(HERE/f'PRIVATE_MODELS/F{n}_HOLD_VALUE.pkl')==rec['model_sha256'] and sha(HERE/f'PRIVATE_MODELS/F{n}_preprocessor.pkl')==rec['preprocessor_sha256'],n)
        for lo in range(0,len(te),2048):
            ids=te[lo:lo+2048];num=X[ids];cat=C[ids];missing=~np.isfinite(num);parts=[np.where(missing,prep.median,num),missing.astype(float)]
            for j,ks in enumerate(prep.known):
                mapping={v:k for k,v in enumerate(ks)};a=np.zeros((len(ids),len(ks)+1));a[np.arange(len(ids)),[mapping.get(int(v),len(ks)) for v in cat[:,j]]]=1;parts.append(a)
            actual=model.predict(np.column_stack(parts).astype(np.float32));check('independent_OOF_prediction',np.allclose(actual,pred[ids],atol=1e-10,rtol=0),(n,lo));check('OOF_fold_identity',np.all(fold_of[ids]==n),(n,lo))
    entries={e['watch_key']:e for e in lines(ENTRY/'P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz') if e['entry_status']=='FIRST_ENTRY'};b=list(lines(HERE/'STATE_EXIT_RECORDS.jsonl.gz'));h=list(lines(HERE/'STATE_EXIT_HARD1_RECORDS.jsonl.gz'));pairs=list(lines(HERE/'PAIRED_EXIT_DELTAS.jsonl.gz'));traces={(t['arm'],t['watch_key']):t for t in lines(HERE/'EXIT_DECISION_TRACES.jsonl.gz')}
    check('same_frozen1600_entries',len(entries)==len(b)==len(h)==1600 and set(entries)=={r['watch_key'] for r in b}=={r['watch_key'] for r in h})
    independent_metrics={arm:[] for arm in ['STATE_EXIT','STATE_EXIT_HARD1']}
    for baseline,hard,pair in zip(b,h,pairs):
        key=baseline['watch_key'];e=entries[key];day=e['session'];a=rows[key];allowed=set(regular(day));post=[i for i in bywatch[key] if grid[i]['intent_minute']>e['fill_minute']];previous=None;consecutive=0;decisions=[];intent=None
        for i in post:
            t=grid[i]['intent_minute']
            if previous is None or t-previous!=1 or (previous<=690<t and t>=751):consecutive=0
            consecutive=consecutive+1 if pred[i]<=0 else 0;previous=t;decisions.append(i)
            if consecutive==2:intent=t;break
        if intent is None:intent=900 if day<'2024-11-05' else 925
        opportunities=[r for r in a if r[0] in allowed and r[0]>=intent]
        closing=[r for r in a if r[0]==terminal(day)]
        if opportunities:sellmin=int(opportunities[0][0]);raw=opportunities[0][1]
        elif closing:sellmin=terminal(day);raw=closing[-1][4]
        else:sellmin=None;raw=None
        check('first_two_negative_cross',baseline['exit_intent_minute']==intent and baseline['decision_N']==len(decisions),key)
        check('canonical_next_open_sell5bps',baseline['sell_minute']==sellmin and close(baseline['sell_fill_price'],raw*.9995 if raw is not None else None),key)
        check('exact_baseline_decision_trace',[x['row_index'] for x in traces[('STATE_EXIT',key)]['decisions']]==decisions,key)
        stop=None;line=e['fill_price']*.99
        for r in a:
            m=int(r[0])
            if m<e['fill_minute'] or m not in allowed:continue
            if sellmin is not None and m>=sellmin:break
            if r[1]<=line:stop=(m,r[1],'GAP_OPEN_AT_OR_BELOW_LINE');break
            if r[3]<=line:stop=(m,line,'INTRABAR_LOW_TOUCH');break
        hm,hr,hkind=stop if stop else (sellmin,raw,None)
        check('Hard1_fixed_earliest_touch_and_priority',hard['sell_minute']==hm and hard['Hard1_trigger']==bool(stop) and hard['Hard1_trigger_kind']==hkind and close(hard['sell_fill_price'],hr*.9995 if hr is not None else None),key)
        expected_hdec=[i for i in decisions if (grid[i]['intent_minute']<hm if hkind=='GAP_OPEN_AT_OR_BELOW_LINE' else grid[i]['intent_minute']<=hm)] if stop else decisions
        check('HARD1_trace_prefix_and_stop',[x['row_index'] for x in traces[('STATE_EXIT_HARD1',key)]['decisions']]==expected_hdec,key)
        for r in (baseline,hard):
            check('no_post_sell_decision_no_reentry',r['decision_after_sell']==r['reentry_calls']==0 and r['entry_fold']==e['first_intent']['fold'],(key,r['arm']))
            m=r['sell_minute'];ret=None if m is None else 100*(r['sell_fill_price']/e['fill_price']-1)
            check('realized_return_independent',close(ret,r['realized_return_pct']),(key,r['arm']))
            if m is not None:
                peak=max([e['fill_price']]+[bar[2] for bar in a if e['fill_minute']<bar[0]<m]);giveback=100*(peak/e['fill_price']-1)-ret
                check('held_Peak_Giveback',close(giveback,r['Peak_Giveback_pp']),(key,r['arm']))
                future=[bar[2] for bar in a if bar[0]>m]
                for level in (3,5):check('later_winner_strict_bar',r[f'later_winner_{level}_observed']==bool(future and max(future)>=e['fill_price']*(1+level/100)),(key,r['arm'],level))
                realization=None if e['remaining_upside_pct'] is None or e['remaining_upside_pct']<=0 else 100*ret/e['remaining_upside_pct']
                check('MFE_realization',close(realization,r['MFE_realization_pct']),(key,r['arm']))
            independent_metrics[r['arm']].append({'key':key,'return':ret,'mfe':e['remaining_upside_pct']})
        known=baseline['realized_return_pct'] is not None and hard['realized_return_pct'] is not None
        check('paired_delta',pair['paired_known']==known and close(pair['delta_return_pp'],hard['realized_return_pct']-baseline['realized_return_pct'] if known else None),key)
    ev=read(HERE/'TWO_ARM_EVALUATION.json');ids=[i for i,p in enumerate(pairs) if p['paired_known']]
    check('paired_denominator',len(ids)==ev['paired_primary']['paired_N'])
    for arm in independent_metrics:
        vals=[independent_metrics[arm][i]['return'] for i in ids]
        check('paired_return_summary',close(float(np.mean(vals)),ev['paired_primary'][arm]['metrics']['realized_return_pct']['mean']) and close(median(vals),ev['paired_primary'][arm]['metrics']['realized_return_pct']['median']),arm)
    for level in (3,5):check('Winner_denominator',sum(e['remaining_upside_pct'] is not None and e['remaining_upside_pct']>=level for e in entries.values())==ev['winners'][str(level)]['winner_denominator'],level)
    check('Hard1_trigger_count',sum(r['Hard1_trigger'] for r in h)==ev['Hard1']['trigger_N'])
    check('Hard1_negative_loss_saved_count',sum(p['saved_negative_loss'] for p in pairs)==ev['Hard1']['saved_negative_loss_N'])
    check('safety_and_boundary0',all(v is False for v in ev['safety'].values()) and all(ev[k]==0 for k in ['Entry_refit','old_EXIT_read_or_comparison','Reentry','Capital','Portfolio_Replay','provider','protected','orders']))
    result={'saved_at_jst':now(),'status':'PASS' if not issues else 'FAIL','mismatch_N':len(issues),'mismatches':issues[:100],'checks':dict(checks),'checks_total':sum(checks.values()),'audit_fits':0,'future_causal_leakage_N':sum(x['check'] in ['State_timestamp_causal','closed_every_observed_minute_cutoff','temporal_split'] for x in issues),'OOF_full_prediction_rechecked':True,'teacher_all_rows_independently_recomputed':True,'all1600_two_arm_first_exit_rechecked':True,'Legacy_State_features':0,'old_EXIT_body_read':0,'old_EXIT_replay':0,'Entry_regeneration':0,'Reentry':0,'Capital':0,'orders':0,'limitations':['historical actual arrival UNKNOWN; assumed bar end as frozen upstream','OHLC standing stop proxy, no tick-order certificate','missing source does not prove unobserved stop did not happen'],'safety':SAFETY}
    write(HERE/'INDEPENDENT_EXIT_AUDIT.json',result);print(json.dumps({'status':result['status'],'mismatch_N':len(issues),'checks_total':sum(checks.values()),'audit_fit':0}),flush=True)
    if issues:raise SystemExit(2)
if __name__=='__main__':run()
