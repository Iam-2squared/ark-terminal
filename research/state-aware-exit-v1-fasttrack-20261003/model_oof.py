"""One new fixed EXIT head, exactly five temporal fits, no historical EXIT imports."""
import os
os.environ.setdefault('OMP_NUM_THREADS','8');os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import gc, pickle, time, warnings
from sklearn.ensemble import HistGradientBoostingRegressor
from scipy.stats import spearmanr
import sklearn
from exit_common import *

class Preprocessor:
    def fit(self,num,cat,vocabulary):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore');self.median=np.nanmedian(num,axis=0)
        self.median=np.where(np.isfinite(self.median),self.median,0.)
        self.known=[]
        for j,col in enumerate(cat.T):
            known=set(map(int,col))
            for special in ('__MISSING__','__UNKNOWN_HISTORY__','__FORMAL_NULL__'):
                if special in vocabulary[j]:known.add(vocabulary[j].index(special))
            self.known.append(sorted(known))
        self.training_rows=len(num);return self
    def transform(self,num,cat):
        d=num.shape[1];out=np.empty((len(num),2*d+sum(len(x)+1 for x in self.known)),dtype=np.float32)
        for lo in range(0,len(num),2048):
            hi=min(lo+2048,len(num));v=num[lo:hi];missing=~np.isfinite(v)
            out[lo:hi,:d]=np.where(missing,self.median,v);out[lo:hi,d:2*d]=missing;offset=2*d
            for j,known in enumerate(self.known):
                out[lo:hi,offset:offset+len(known)+1]=0
                k=np.asarray(known);idx=np.searchsorted(k,cat[lo:hi,j]);seen=(idx<len(k))&(k[np.minimum(idx,len(k)-1)]==cat[lo:hi,j]);idx=np.where(seen,idx,len(k))
                out[np.arange(lo,hi),offset+idx]=1;offset+=len(k)+1
        return out

def run():
    cfg=read(HERE/'MODEL_POLICY_FREEZE.json');assert cfg['parameters']==PARAMS and cfg['new_EXIT_fits']==5
    grid=list(lines(ENTRY/'PERSISTENT_GRID.jsonl.gz'));sessions=np.asarray([r['session'] for r in grid]);folds=read(HERE/'SPLIT_PRECOMMIT.json')['folds']
    X=np.load(ENTRY/'PRIVATE_INPUTS/features_numeric.npy',mmap_mode='r');C=np.load(ENTRY/'PRIVATE_INPUTS/features_categories.npy',mmap_mode='r');Y=np.load(HERE/'PRIVATE_INPUTS/targets.npy');vocab=read(ENTRY/'PRIVATE_INPUTS/category_vocabulary.json')
    pred=np.full(len(grid),np.nan);fold_id=np.zeros(len(grid),int);ledger=read(HERE/'FIT_LEDGER.json');start=time.time()
    assert ledger['fits_reserved']==ledger['fits_completed'], 'RESERVED_FIT_CANNOT_BE_RETRIED'
    for fold in folds:
        f=fold['id'];train_all=np.flatnonzero(np.isin(sessions,fold['train']));tr=train_all[np.isfinite(Y[train_all])];te=np.flatnonzero(np.isin(sessions,fold['test']))
        assert len(tr)>40 and max(sessions[tr])<min(sessions[te]) and not(set(sessions[tr])&set(sessions[te]))
        old=next((r for r in ledger['runs'] if r['fold']==f),None)
        modelp=HERE/f'PRIVATE_MODELS/F{f}_HOLD_VALUE.pkl';prepp=HERE/f'PRIVATE_MODELS/F{f}_preprocessor.pkl'
        if old:
            assert old['status']=='COMPLETED' and sha(modelp)==old['model_sha256']
            pred[te]=np.load(HERE/f'PRIVATE_MODELS/F{f}_test_predictions.npy');fold_id[te]=f;continue
        prep=Preprocessor().fit(X[tr],C[tr],vocab);prepp.write_bytes(pickle.dumps(prep,protocol=5))
        np.save(HERE/f'PRIVATE_MODELS/F{f}_train_indices.npy',tr);np.save(HERE/f'PRIVATE_MODELS/F{f}_test_indices.npy',te)
        np.save(HERE/f'PRIVATE_MODELS/F{f}_train_targets.npy',Y[tr])
        rec={'fold':f,'head':'HOLD_CONTINUATION_VALUE','family':'EXACT_RC2_STATE_PRICE_VOLUME_PATH','reserved_at_jst':now(),'train_N':len(tr),'train_context_N':len(train_all),'test_N':len(te),'test_known_label_N':int(np.isfinite(Y[te]).sum()),'train_sessions':fold['train'],'test_sessions':fold['test'],'purge':fold['purge'],'parameters':PARAMS,'preprocessor_sha256':sha(prepp),'train_indices_sha256':sha(HERE/f'PRIVATE_MODELS/F{f}_train_indices.npy'),'test_indices_sha256':sha(HERE/f'PRIVATE_MODELS/F{f}_test_indices.npy'),'train_target_lineage_sha256':sha(HERE/f'PRIVATE_MODELS/F{f}_train_targets.npy'),'teacher_receipt_sha256':sha(HERE/'TEACHER_RECEIPT.json'),'status':'RESERVED','fit_ordinal':ledger['fits_reserved']+1}
        ledger['runs'].append(rec);ledger['fits_reserved']+=1;assert ledger['fits_reserved']<=5;write(HERE/'FIT_LEDGER.json',ledger)
        a=prep.transform(X[tr],C[tr]);model=HistGradientBoostingRegressor(**PARAMS);model.fit(a,Y[tr]);del a;gc.collect()
        modelp.write_bytes(pickle.dumps(model,protocol=5));b=prep.transform(X[te],C[te]);p=model.predict(b);del b;gc.collect();pred[te]=p;fold_id[te]=f
        np.save(HERE/f'PRIVATE_MODELS/F{f}_test_predictions.npy',p)
        good=np.isfinite(Y[te]);rho=float(spearmanr(p[good],Y[te[good]]).statistic)
        rec.update(status='COMPLETED',completed_at_jst=now(),model_sha256=sha(modelp),prediction_sha256=sha(HERE/f'PRIVATE_MODELS/F{f}_test_predictions.npy'),OOF_MAE=float(np.mean(abs(p[good]-Y[te[good]]))),OOF_Spearman=rho if math.isfinite(rho) else None)
        ledger['fits_completed']+=1;write(HERE/'FIT_LEDGER.json',ledger)
        print(json.dumps({'fit_completed':ledger['fits_completed'],'fold':f,'train_N':len(tr),'test_N':len(te),'seconds':round(time.time()-start,1)}),flush=True)
        del model,prep;gc.collect()
    primary=np.flatnonzero([r['canonical'] for r in grid]);assert np.isfinite(pred[primary]).all() and (fold_id[primary]>0).all()
    assert ledger['fits_completed']==ledger['fits_reserved']==5
    np.savez_compressed(HERE/'PRIVATE_INPUTS/exit_oof.npz',row_indices=primary,predictions=pred[primary],fold=fold_id[primary])
    write_lines(HERE/'OOF_EXIT_PREDICTIONS.jsonl.gz',({'row_index':int(i),'row_id':grid[i]['row_id'],'watch_key':grid[i]['watch_key'],'session':grid[i]['session'],'decision_minute':grid[i]['intent_minute'],'fold':int(fold_id[i]),'predicted_hold_continuation_value_pct':float(pred[i]),'feature_max_timestamp':grid[i]['feature_max_timestamp'],'future_evaluator_fields_used':False} for i in primary))
    write(HERE/'OOF_LINEAGE_RECEIPT.json',{'saved_at_jst':now(),'fits':5,'hard_cap':5,'Hard1_extra_fits':0,'OOF_rows':len(primary),'OOF_sha256':sha(HERE/'OOF_EXIT_PREDICTIONS.jsonl.gz'),'oof_npz_sha256':sha(HERE/'PRIVATE_INPUTS/exit_oof.npz'),'feature_freeze_sha256':sha(HERE/'FEATURE_FREEZE.json'),'split_sha256':sha(HERE/'SPLIT_PRECOMMIT.json'),'teacher_receipt_sha256':sha(HERE/'TEACHER_RECEIPT.json'),'model_policy_sha256':sha(HERE/'MODEL_POLICY_FREEZE.json'),'sklearn_version':sklearn.__version__,'train_preprocessing_scope':'finite-label training rows only','HARD1_reuses_identical_OOF':True,'frozen_Entry_fits':0,'safety':SAFETY})
if __name__=='__main__':run()
