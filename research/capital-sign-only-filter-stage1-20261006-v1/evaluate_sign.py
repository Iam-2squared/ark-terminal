"""Only sign labels enter performance, thresholds and termination decisions."""
import numpy as np
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, log_loss
from sign_io import *
from sign_policy import filter_metrics, gate, div

def binary_metrics(preds, target):
    known=[p for p in preds if target[p['entry_id']]['y_neg'] is not None]
    valid=[p for p in known if p['model_prediction_valid'] and p['score_neg'] is not None]
    y=np.array([target[p['entry_id']]['y_neg'] for p in valid],dtype=int)
    s=np.array([p['score_neg'] for p in valid]);n=(s>=.5).astype(int)
    nn=int(sum((y==1)&(n==1)));np_=int(sum((y==1)&(n==0)))
    pp=int(sum((y==0)&(n==0)));pn=int(sum((y==0)&(n==1)))
    nr=div(nn,nn+np_);pr=div(pp,pp+pn)
    both=len(set(y))==2
    return {'known_N':len(known),'scorable_N':len(valid),'model_prediction_coverage_known':div(len(valid),len(known)),
      'model_prediction_coverage_all':div(sum(p['model_prediction_valid'] for p in preds),len(preds)),
      'missing_or_unavailable_known_N':len(known)-len(valid),
      'actual_NEG_pred_NEG':nn,'actual_NEG_pred_POS':np_,'actual_POS_pred_POS':pp,'actual_POS_pred_NEG':pn,
      'accuracy':div(nn+pp,len(valid)),'balanced_accuracy':(nr+pr)/2 if nr is not None and pr is not None else None,
      'negative_precision':div(nn,nn+pn),'negative_recall':nr,'positive_precision':div(pp,pp+np_),'positive_recall':pr,
      'AUROC_neg':float(roc_auc_score(y,s)) if both else None,
      'AP_neg':float(average_precision_score(y,s)) if both else None,
      'AP_pos':float(average_precision_score(1-y,1-s)) if both else None,
      'Brier':float(brier_score_loss(y,s)) if len(y) else None,
      'log_loss':float(log_loss(y,s,labels=[0,1])) if len(y) else None,
      'strict_binary_threshold':0.5,'score_orientation':'higher = NEGATIVE; no posthoc inversion'}

def main():
    preds=rows(PRIVATE/'INITIAL_OOF_PREDICTIONS.jsonl.gz');actions=rows(PRIVATE/'SIGN_FILTER_ACTIONS.jsonl.gz')
    target={r['entry_id']:validate_sign(r) for r in rows(PRIVATE/'SIGN_LABEL_VIEW.jsonl.gz')}
    runtime=rows(PRIVATE/'INPUT_ROWS.jsonl.gz');rm={r['entry_id']:r for r in runtime}
    members={r['entry_id']:r for r in rows(PRIVATE/'AUXILIARY_MEMBERSHIP.jsonl.gz')};split=read(SPLIT)
    recipes=['B0','HL0','OLD_D1','OLD_D2']+RECIPES
    eligible={k for k,r in rm.items() if r['session'] in split['OOF38'] and r['execution_eligible']}
    masks={'FROZEN_ENTRY_EXECUTION_ELIGIBLE':eligible,'ALL_ENTRY':{k for k,r in rm.items() if r['session'] in split['OOF38']},
           'RANK_PASS':{k for k in eligible if members[k]['rank_pass']},'OLD_V5_PURCHASED':{k for k in eligible if members[k]['old_V5_purchased']}}
    binary=[];filters=[];blocks=[];metrics={}
    for recipe in recipes:
        ps=[p for p in preds if p['recipe']==recipe]
        assert len(ps)==len({p['entry_id'] for p in ps})==1039
        for mask,ids in masks.items():
            chosen=[p for p in ps if p['entry_id'] in ids]
            bm=binary_metrics(chosen,target);binary.append({'recipe':recipe,'population':mask,**bm})
            metrics.setdefault(recipe,{})[mask]={'binary_0.5':bm,'filters':{}}
            for alpha in ALPHAS:
                values=[{**a,**target[a['entry_id']]} for a in actions if a['recipe']==recipe and a['alpha']==alpha and a['entry_id'] in ids]
                fm=filter_metrics(values);filters.append({'recipe':recipe,'population':mask,'alpha':alpha,'scope':'ALL_OOF_INCLUDING_OFF',**fm})
                metrics[recipe][mask]['filters'][alpha]=fm
                if mask=='FROZEN_ENTRY_EXECUTION_ELIGIBLE':
                    for block in split['blocks']:
                        bv=[r for r in values if r['block']==block['block']]
                        snapshot=read(OUT/'SIGN_ONLY_THRESHOLD_SNAPSHOTS'/f'BLOCK_{block["block"]:02d}.json')['thresholds'][recipe][alpha]
                        bp=[p for p in chosen if p['block']==block['block']]
                        blocks.append({'recipe':recipe,'block':block['block'],'alpha':alpha,'threshold_status':snapshot['status'],
                                       'tau':snapshot['tau'],'CAL_support_met':snapshot['support_met'],
                                       'CAL_N':snapshot['CAL_N'],'CAL_sessions':snapshot['CAL_sessions'],
                                       **filter_metrics(bv),'binary_balanced_accuracy':binary_metrics(bp,target)['balanced_accuracy'],
                                       'model_prediction_coverage':binary_metrics(bp,target)['model_prediction_coverage_all']})
                    active=[r for r in values if r['threshold_status']=='ACTIVE']
                    filters.append({'recipe':recipe,'population':mask,'alpha':alpha,'scope':'ACTIVE_ONLY_AUXILIARY',**filter_metrics(active)})
    values=[{**target[k],'action':'PASS_UNASSESSED_NO_FILTER'} for k in sorted(eligible)]
    nofilter=filter_metrics(values);filters.insert(0,{'recipe':'NO_FILTER','population':'FROZEN_ENTRY_EXECUTION_ELIGIBLE','alpha':None,'scope':'ALL_OOF_INCLUDING_OFF',**nofilter})
    references=[]
    for name,score in [('ALL_POSITIVE',0.0),('ALL_NEGATIVE',1.0)]:
        references.append({'recipe':name,'population':'FROZEN_ENTRY_EXECUTION_ELIGIBLE',**binary_metrics([{'entry_id':k,'score_neg':score,'model_prediction_valid':True} for k in sorted(eligible)],target)})
    binary+=references
    primary=metrics['SF_D_UNION']['FROZEN_ENTRY_EXECUTION_ELIGIBLE']['filters']['0.10']
    coverage=metrics['SF_D_UNION']['FROZEN_ENTRY_EXECUTION_ELIGIBLE']['binary_0.5']['model_prediction_coverage_all']
    qualifying=[r for r in blocks if r['recipe']=='SF_D_UNION' and r['alpha']=='0.10']
    # Evaluation remains provisional until the independent process audits it.
    decision=gate(primary,coverage,qualifying,True)
    save(OUT/'SIGN_METRICS.json',{'metrics':metrics,'no_filter':nofilter,'uninformative_binary_references':references,
         'primary_recipe':'SF_D_UNION','primary_alpha':'0.10','primary_population':'FROZEN_ENTRY_EXECUTION_ELIGIBLE',
         'primary_scope':'ALL38_OOF_SESSIONS_INCLUDING_OFF','provisional_gate':decision,'gate_requires_independent_audit':True,
         'coverage_counts':{'ALL_ENTRY_N':1039,'execution_eligible_N':len(eligible),'ineligible_N':1039-len(eligible),
                            'eligible_sign_known_N':sum(target[k]['y_neg'] is not None for k in eligible),
                            'eligible_UNKNOWN_N':sum(target[k]['sign_status']=='UNKNOWN' for k in eligible),
                            'eligible_EXACT_ZERO_N':sum(target[k]['sign_status']=='EXACT_ZERO' for k in eligible)},
         'evaluation_weights':'all1','money_or_return_magnitude_metrics':None,'CI':'NOT_COMPUTED; not used to rescue gate'})
    write_csv(OUT/'BINARY_CONFUSION.csv',binary);write_csv(OUT/'FILTER_COUNTS.csv',filters);write_csv(OUT/'BLOCK_METRICS.csv',blocks)
    gzsave(PRIVATE/'OOF_PASS_HANDOFF.jsonl.gz',[{'entry_id':a['entry_id'],'session':a['session'],'block':a['block'],'action':a['action'],
            'filter_recipe':a['recipe'],'alpha':a['alpha'],'threshold_snapshot_sha256':sha(OUT/'SIGN_ONLY_THRESHOLD_SNAPSHOTS'/f'BLOCK_{a["block"]:02d}.json')}
            for a in actions if a['recipe']=='SF_D_UNION' and a['alpha']=='0.10' and a['entry_id'] in eligible and a['action']!='REJECT'],exclusive=True)
    print(canonical({'primary_sign_counts':primary,'provisional_gate':decision}))

if __name__=='__main__':main()
