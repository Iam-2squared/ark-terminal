"""Correct only source-calendar eligibility using preserved observed statistics.

The original future High, peak, close variation, raw Q/D and hit timestamps were
arithmetically correct. Restore masked values only where sorted source schedule
is actually complete. Independent audit recalculates all values from raw source.
No model fit and no score/threshold/intent change.
"""
import collections
from common import *
def run():
 archive=HERE/'PRIVATE_PREFIT_LINEAGE';original=archive/'TEACHER_LABELS.jsonl.gz';assert sha(original)==read(archive/'TEACHER_COMPUTATION_RECEIPT.json')['teacher_labels_sha256']
 raw=read(INPUT/'raw_paths_selected.json.gz');Y=np.load(archive/'targets.npy');correct=Y.copy();counts=collections.Counter();last=None
 def records():
  nonlocal last
  for r in lines(original):
   key=r['watch_key'];day=r['session'];i=r['row_index']
   if key!=last:
    last=key;a=clean_array(raw[key]['today']);calendar=np.asarray(source_starts(day));observed=set(map(int,a[:,0]));missing=np.asarray([int(m not in observed) for m in calendar]);prefix=np.r_[0,np.cumsum(missing)]
   if r.get('peak_minute') is not None:
    fill=r['fill_minute'];peak=r['peak_minute'];start=int(np.searchsorted(calendar,fill));end=int(np.searchsorted(calendar,peak));complete=bool(prefix[end+1]-prefix[start]==0);full=bool(prefix[-1]-prefix[start]==0)
    r['pre_peak_path_complete']=complete;r['remaining_source_complete']=full;r['Q_target']=r['observed_path_efficiency'] if complete else None;r['D_target']=float(np.clip(r['observed_pre_peak_mae_abs_pct'],0,5)) if complete else None
    for target,source in [('path_efficiency','observed_path_efficiency'),('pre_peak_mae_abs_pct','observed_pre_peak_mae_abs_pct'),('total_variation_pct','observed_total_variation_pct'),('reversal_count','observed_reversal_count')]:r[target]=r[source] if complete else None
    r['evaluator_status']='COMPLETE_PRE_PEAK_PATH' if complete else 'OBSERVED_HIGH_PARTIAL_PATH'
    for k,hit in r['first_upside'].items():
     if hit['minute'] is not None:
      hm=hit['minute'];he=int(np.searchsorted(calendar,hm));ok=bool(prefix[he+1]-prefix[start]==0);hit['pre_hit_path_complete']=ok;pp=a[(a[:,0]>=fill)&(a[:,0]<=hm)];hit['pre_hit_mae_abs_pct']=float(abs(min(0.,100*(min(pp[:,3])/r['fill_price']-1)))) if ok else None
     else:hit['status']='NO_HIT_CONFIRMED' if full else 'UNKNOWN'
   for h,k in enumerate(['U_target','Q_target','D_target']):
    correct[i,h]=np.nan if r.get(k) is None else r[k]
    if r.get(k) is not None:counts[k]+=1
   counts[r['evaluator_status']]+=1;yield r
 write_lines(HERE/'TEACHER_LABELS.jsonl.gz',records());np.save(HERE/'PRIVATE_INPUTS/targets.npy',correct)
 receipt={'saved_at_jst':now(),'status':'CORRECTED_TEACHER_EVALUATOR_ONLY_MODEL_LINEAGE_BLOCKED','rows':len(correct),'counts':dict(counts),'teacher_labels_sha256':sha(HERE/'TEACHER_LABELS.jsonl.gz'),'original_training_labels_sha256':sha(original),'original_training_targets_sha256':sha(archive/'targets.npy'),'corrected_targets_sha256':sha(HERE/'PRIVATE_INPUTS/targets.npy'),'teacher_contract_sha256':sha(HERE/'CLEAN_UPTREND_TEACHER_CONTRACT.json'),'repair_method':'sorted expected source membership; preserve original observed high/peak/TV/Q/D arithmetic, independent all-row raw recalculation follows','source_provider_requests':0,'model_fits_in_correction':0,'completed_model_fits_total':30,'original_models_not_trained_on_corrected_mask':True,'safety':SAFETY}
 write(HERE/'TEACHER_COMPUTATION_RECEIPT.json',receipt);print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':run()
