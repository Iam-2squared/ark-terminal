"""48-fit maximum fixed session-forward incremental test. Not a Capital ranker."""
from datetime import datetime,timedelta,timezone
import hashlib,json,pickle,sys
from pathlib import Path
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler,OneHotEncoder
from sklearn.linear_model import Ridge
from sklearn.metrics import roc_auc_score

def main():
    root=Path(sys.argv[1]);out=root/'svnext_private';data=np.load(out/'CAUSAL_DIAGNOSTIC_PRIVATE.npz')
    X=[data[k] for k in ['A','B','C']];cats=[None,data['catsB'],data['catsC']];Y=data['Y'];sessions=data['sessions'];days=sorted(set(sessions))
    pred=np.full((len(sessions),3,4),np.nan);records=[];models=[];references={};fits=0
    for fold in range(4):
        lo=18+fold*10;hi=lo+10;train_days=days[:lo-1];test_days=days[lo:hi]
        tr=np.isin(sessions,train_days);te=np.isin(sessions,test_days)
        for target in range(4):
            use=tr&np.isfinite(Y[:,target]);n=int(use.sum())
            if n<100:
                records.append({'fold':fold,'target':target,'status':'TRAIN_SUPPORT_INSUFFICIENT','train_N':n});continue
            for arm in range(3):
                imp=SimpleImputer(strategy='median',add_indicator=True,keep_empty_features=True)
                scale=StandardScaler();a=scale.fit_transform(imp.fit_transform(X[arm][use]));b=scale.transform(imp.transform(X[arm][te]))
                encoder=None
                if cats[arm] is not None:
                    encoder=OneHotEncoder(handle_unknown='ignore',sparse_output=False)
                    a=np.column_stack([a,encoder.fit_transform(cats[arm][use])]);b=np.column_stack([b,encoder.transform(cats[arm][te])])
                model=Ridge(alpha=10);model.fit(a,Y[use,target]);pred[te,arm,target]=model.predict(b);fits+=1
                train_predictions=model.predict(a);references[str((fold,arm,target))]=np.sort(train_predictions).tolist()
                blob=pickle.dumps({'imputer':imp,'scaler':scale,'onehot':encoder,'model':model,'train_days':train_days,'test_days':test_days},protocol=5)
                path=out/f'diagnostic_model_F{fold}_A{arm}_T{target}.pkl';path.write_bytes(blob)
                models.append({'fold':fold,'arm':arm,'target':target,'sha256':hashlib.sha256(blob).hexdigest(),'train_N':n,'prior_only':True})
                records.append({'fold':fold,'arm':arm,'target':target,'train_N':n,'test_N':int(te.sum()),'status':'FIT_ONCE'})
    def compare(old,new):
        targets=[];fold_lifts=[];session_lifts={d:0.0 for d in days[18:]}
        for target in range(4):
            mask=np.isfinite(Y[:,target])&np.isfinite(pred[:,old,target])&np.isfinite(pred[:,new,target])
            if not mask.any():targets.append({'target':target,'support_N':0,'mse_old':None,'mse_new':None,'relative_improvement':None});continue
            a=(Y[mask,target]-pred[mask,old,target])**2;b=(Y[mask,target]-pred[mask,new,target])**2
            mse=float(a.mean());lift=float(1-b.mean()/mse) if mse>0 else 0.0
            auc_old=auc_new=None
            if target==0 and len(np.unique(Y[mask,target]))==2:
                auc_old=float(roc_auc_score(Y[mask,target],pred[mask,old,target]));auc_new=float(roc_auc_score(Y[mask,target],pred[mask,new,target]))
            targets.append({'target':target,'support_N':int(mask.sum()),'positive_N':int((Y[mask,target]==1).sum()) if target==0 else None,'mse_old':mse,'mse_new':float(b.mean()),'relative_improvement':lift,'auc_old':auc_old,'auc_new':auc_new})
            for day in days[18:]:
                m=mask&(sessions==day)
                if m.any():session_lifts[day]+=float(np.mean((Y[m,target]-pred[m,old,target])**2-(Y[m,target]-pred[m,new,target])**2)/max(mse,1e-15))
        for fold in range(4):
            mfold=np.isin(sessions,days[18+10*fold:28+10*fold]);lifts=[]
            for target in range(4):
                m=mfold&np.isfinite(Y[:,target])&np.isfinite(pred[:,old,target])&np.isfinite(pred[:,new,target])
                if m.any():
                    a=np.mean((Y[m,target]-pred[m,old,target])**2);b=np.mean((Y[m,target]-pred[m,new,target])**2)
                    if a>0:lifts.append(float(1-b/a))
            fold_lifts.append(float(np.mean(lifts)) if lifts else None)
        improvements=[t['relative_improvement'] for t in targets if t['relative_improvement'] is not None]
        mean=float(np.mean(improvements)) if improvements else None
        positives=[max(0,v) for v in session_lifts.values()];share=max(positives)/sum(positives) if sum(positives)>0 else 1.0
        auc_delta=targets[0]['auc_new']-targets[0]['auc_old'] if targets[0].get('auc_new') is not None else None
        gates={'mean_relative_MSE_improvement_ge1pct':mean is not None and mean>=.01,
               'min2_targets_improved':sum(v>0 for v in improvements)>=2,
               'winner_auc_decline_not_gt2pp':auc_delta is not None and auc_delta>=-.02,
               'positive3_of4_folds':sum(x is not None and x>0 for x in fold_lifts)>=3,
               'single_session_positive_lift_share_le40pct':share<=.40}
        return {'targets':targets,'mean_relative_improvement':mean,'fold_mean_improvement':fold_lifts,'max_positive_session_lift_share':share,'winner_auc_delta':auc_delta,'gates':gates,'pass':all(gates.values())},session_lifts
    state,slift=compare(0,1);path,plift=compare(1,2)
    join=json.loads((out/'STATE9_JOIN_AUDIT.json').read_text());support=join['observed_current_primary_N']>=400 and join['causal_observed_sessions']>=20
    state['support_gate_pass']=support;state['pass']=state['pass'] and support
    path['support_gate_pass']=support;path['pass']=path['pass'] and support
    result={'jst':datetime.now(timezone(timedelta(hours=9))).isoformat(),'status':'STATE9_INCREMENTAL_VALUE_DEMONSTRATED' if state['pass'] else 'CAPITAL_STATE9_INCREMENTAL_VALUE_NOT_DEMONSTRATED',
            'fits_consumed':fits,'fits_max':48,'threshold_sweeps':0,'hyperparameter_sweeps':0,'folds':records,
            'full_teacher_complete_N':np.isfinite(Y).sum(axis=0).tolist(),'State9_current_vs_A':state,'StatePath_vs_B':path,
            'StatePath_promotable':bool(state['pass'] and path['pass']),
            'winner_prediction_semantics':'Ridge binary-teacher regression / ranking diagnostic, not calibrated probability or Brier.',
            'outcome_censoring_caution':'Winner negative and MAE require complete saved source;317/301 support is selective. All arms use identical target-wise populations; no missing teacher=0.',
            'Development_only':True,'fresh_oos_opened':0,'capital_performance_evidence':False,'policy_parameter_retuning':False}
    (out/'STATE9_INCREMENTAL_RESULTS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    (out/'DIAGNOSTIC_MODEL_RECEIPTS_PRIVATE.json').write_text(json.dumps(models,indent=2)+'\n')
    (out/'DIAGNOSTIC_TRAIN_REFERENCE_PRIVATE.json').write_text(json.dumps(references)+'\n')
    (out/'DIAGNOSTIC_SESSION_LIFTS_PRIVATE.json').write_text(json.dumps({'state':slift,'path':plift},indent=2)+'\n')
    np.save(out/'DIAGNOSTIC_OOF_PREDICTIONS_PRIVATE.npy',pred)
    print(json.dumps({k:v for k,v in result.items() if k!='folds'},ensure_ascii=False))

if __name__=='__main__':main()
