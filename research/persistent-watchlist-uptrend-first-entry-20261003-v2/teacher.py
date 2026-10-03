"""Future-only clean-uptrend teachers and evaluator. Never imported by scorer."""
import argparse,collections,time
from common import *
def future_metrics(day,a,fill_minute,fill_price):
 a=clean_array(a);starts=np.asarray(source_starts(day));a=a[np.isin(a[:,0],starts)]
 later=np.flatnonzero(a[:,0]>fill_minute)
 base={'fill_minute':int(fill_minute),'fill_price':float(fill_price),'remaining_upside_pct':None,'U_target':None,'Q_target':None,'D_target':None,'path_efficiency':None,'pre_peak_mae_abs_pct':None,'total_variation_pct':None,'reversal_count':None,'time_to_peak_active_min':None,'terminal_return_pct':None,'session_end_mfe_pct':None,'session_end_mae_pct':None,'peak_minute':None,'peak_bar_close':None,'pre_peak_path_complete':False,'remaining_source_complete':False,'intrabar_peak_low_order':'UNKNOWN; peak-bar Low conservatively included','first_upside':{str(k):{'minute':None,'pre_hit_mae_abs_pct':None,'status':'UNKNOWN'} for k in range(1,6)}}
 if not len(later):base['evaluator_status']='NO_STRICTLY_LATER_OBSERVED_HIGH';return base
 peak_i=int(later[np.argmax(a[later,2])]);peak=a[peak_i];future=a[later];path=a[(a[:,0]>=fill_minute)&(a[:,0]<=peak[0])];remaining=a[a[:,0]>=fill_minute]
 expected=starts[(starts>=fill_minute)&(starts<=peak[0])];complete=np.array_equal(path[:,0],expected)
 full=np.array_equal(remaining[:,0],starts[starts>=fill_minute])
 closes=np.r_[fill_price,path[:,4]];diff=np.diff(closes);tv=float(100*np.abs(diff).sum()/fill_price);net=float(100*(peak[4]/fill_price-1));q=float(max(net,0)/tv) if tv else 0.;q=min(1.,max(0.,q))
 mae=float(abs(min(0.,100*(min(path[:,3])/fill_price-1)))) if len(path) else None
 upside=float(100*(peak[2]/fill_price-1));signs=np.sign(diff);signs=signs[signs!=0];rev=int(np.sum(signs[1:]!=signs[:-1]))
 base.update(remaining_upside_pct=upside,U_target=float(np.clip(upside,0,10)),Q_target=q if complete else None,D_target=float(np.clip(mae,0,5)) if complete else None,path_efficiency=q if complete else None,pre_peak_mae_abs_pct=mae if complete else None,total_variation_pct=tv if complete else None,reversal_count=rev if complete else None,observed_path_efficiency=q,observed_pre_peak_mae_abs_pct=mae,observed_total_variation_pct=tv,observed_reversal_count=rev,time_to_peak_active_min=active_elapsed(day,fill_minute,int(peak[0])),peak_minute=int(peak[0]),peak_bar_close=float(peak[4]),pre_peak_path_complete=bool(complete),remaining_source_complete=bool(full),session_end_mfe_pct=upside,session_end_mae_pct=float(abs(min(0.,100*(min(remaining[:,3])/fill_price-1)))),terminal_return_pct=float(100*(a[-1,4]/fill_price-1)) if a[-1,0]==close_minute(day) else None,observed_terminal_return_pct=float(100*(a[-1,4]/fill_price-1)),evaluator_status='COMPLETE_PRE_PEAK_PATH' if complete else 'OBSERVED_HIGH_PARTIAL_PATH')
 for k in range(1,6):
  hits=np.flatnonzero(future[:,2]>=fill_price*(1+k/100))
  if len(hits):
   hit=int(future[hits[0],0]);pp=a[(a[:,0]>=fill_minute)&(a[:,0]<=hit)];ok=np.array_equal(pp[:,0],starts[(starts>=fill_minute)&(starts<=hit)])
   base['first_upside'][str(k)]={'minute':hit,'pre_hit_mae_abs_pct':float(abs(min(0.,100*(min(pp[:,3])/fill_price-1)))) if ok else None,'status':'HIT_CONFIRMED','pre_hit_path_complete':bool(ok)}
  else:base['first_upside'][str(k)]={'minute':None,'pre_hit_mae_abs_pct':None,'status':'NO_HIT_CONFIRMED' if full else 'UNKNOWN'}
 return base
def next_fill(day,a,intent):
 eligible=a[np.isin(a[:,0],regular_starts(day))&(a[:,0]>=intent)&~np.isin(a[:,0],[540,750])]
 if not len(eligible):return None
 x=eligible[0];return int(x[0]),float(x[1]*1.0005)
def run():
 assert read(HERE/'CLEAN_UPTREND_TEACHER_CONTRACT.json')['before_teacher_computation']
 ws=list(lines(HERE/'WATCH_RECORDS.jsonl.gz'));raw=read(INPUT/'raw_paths_selected.json.gz');ranges=np.load(HERE/'PRIVATE_INPUTS/watch_row_ranges.npy');N=int(ranges[-1,1]);Y=np.full((N,3),np.nan);counts=collections.Counter();t0=time.time()
 def records():
  for wi,w in enumerate(ws):
   a=clean_array(raw[w['watch_key']]['today']);tt=[int(x[0])+1 for x in a if int(x[0]) in set(regular_starts(w['session'])) and x[0]+1>=w['selector_minute']];lo,hi=ranges[wi];assert hi-lo==len(tt)
   cached={}
   for j,t in enumerate(tt):
    fill=next_fill(w['session'],a,t)
    if fill is None:m={'evaluator_status':'NO_NEXT_REGULAR_OPEN','U_target':None,'Q_target':None,'D_target':None}
    else:
     if fill[0] not in cached:cached[fill[0]]=future_metrics(w['session'],a,*fill)
     m=cached[fill[0]]
    r={'row_index':int(lo+j),'row_id':w['watch_key']+'|'+str(t),'watch_key':w['watch_key'],'session':w['session'],'intent_minute':t,**m}
    for k,h in enumerate(('U_target','Q_target','D_target')):
     if m.get(h) is not None:Y[lo+j,k]=m[h];counts[h]+=1
    counts[m['evaluator_status']]+=1;yield r
   if wi%250==0:print(json.dumps({'teacher_watches':wi+1,'teacher_rows':int(hi),'seconds':round(time.time()-t0,1),'new_fits':0}),flush=True)
 write_lines(HERE/'TEACHER_LABELS.jsonl.gz',records());np.save(HERE/'PRIVATE_INPUTS/targets.npy',Y)
 write(HERE/'TEACHER_COMPUTATION_RECEIPT.json',{'saved_at_jst':now(),'rows':N,'counts':dict(counts),'teacher_contract_sha256':sha(HERE/'CLEAN_UPTREND_TEACHER_CONTRACT.json'),'teacher_labels_sha256':sha(HERE/'TEACHER_LABELS.jsonl.gz'),'future_fields_used_by_decision':0,'model_fits':0,'safety':SAFETY})
if __name__=='__main__':run()
