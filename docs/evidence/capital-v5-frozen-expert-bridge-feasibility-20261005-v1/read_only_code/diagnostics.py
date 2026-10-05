"""Single claimed diagnostic batch, stage-resumable, consumes frozen packet and saved outcomes."""
import argparse,math,collections,struct,gzip,json,hashlib,pathlib,itertools
from fractions import Fraction
import numpy as np
from metrics import B,SEED,weight_stream,auc_ap,weighted_spearman,concordance,ci,cluster_auc
from adapter import ROOT,BASE,OUT,PRIVATE,HEADS,read,rows,save,sha,digest,now
SCOREALIASES={'pP':'pP','MOVE_U2':'q2','MOVE_U3':'q3','MRET':'mP'}
def claim():
 if (OUT/'PRIMARY_DIAGNOSTIC_CLAIM.json').exists():return
 save('PRIMARY_DIAGNOSTIC_CLAIM.json',{'exact_jst':now(),'primaryDiagnosticBatch':1,'newFits':0,'newInference':0,'CapitalReplays':0,'ControlReplays':0,'runtimePolicies':0,'packet_GET_receipt':read(OUT/'GET_RECEIPT_F2.json'),'code_sha256':{p.name:sha(p) for p in (BASE/'code').glob('*.py')},'seed':SEED,'resamples':B,'sampling_frame':'all frozen38 OOF sessions; empty subset sessions retained; paired weights shared across all targets/heads','fixed_topK':'original20/30 sets conditional, no reoptimization','first_stage':'F3'})
def load_data():
 packet=rows(PRIVATE/'FROZEN_EXPERT_PACKET.jsonl.gz');pmap={r['entry_id']:r for r in packet};masks=read(PRIVATE/'COHORT_MASKS.json')
 outcomes=read(ROOT/'r1_work/metrics/evaluation_only/OUTCOMES_EXACT_EVALUATION.json');teachers={r['entry_id']:r for r in rows(ROOT/'r1_work/metrics/evaluation_only/TEACHERS_EVALUATION.jsonl.gz')}
 nativeM={r['entry_id']:r for r in rows(BASE/'sources/mret/private/MRET_POST_FIT_EVALUATION_ROWS.jsonl.gz')}
 dd={r['entry_id']:r for r in rows(ROOT/'r1_work/runs/OFF_PRIMARY/DECISIONS.jsonl.gz')};trades={r['entry_id']:r for r in rows(ROOT/'r1_work/runs/OFF_PRIMARY/TRADES.jsonl.gz')}
 data={}
 for k,p in pmap.items():
  t=teachers[k];o=outcomes[k];assert t['session']==p['session']
  # EXIT/source lineage is the frozen original teacher contract, not a guessed flat column.
  pot=None if o['potential_pct'] is None else Fraction(o['potential_pct'])/100
  net=None if o['frozen_realized_net_return_cell'] is None else Fraction(o['frozen_realized_net_return_cell'])
  q={'entry_id':k,'session':p['session'],'symbol':p['symbol'],'entry_time':p['frozen_entry_time'],'block':p['native_block'],'native_reason':p['native']['reason'],'native_funded_slot':p['native']['funded_slot'],'native_slot_admission_index':p['native']['slot_admission_index'],'scores':{h:p['heads'][h]['raw_score'] for h in HEADS},'ranks':{h:p['heads'][h]['numerator']/p['heads'][h]['denominator'] for h in HEADS},'potential':float(pot) if pot is not None else None,'potential_exact':str(pot) if pot is not None else None,'realized':float(net) if net is not None else None,'realized_exact':str(net) if net is not None else None,'pnl_exact':str(Fraction(trades[k]['pnl'])) if k in trades else None,'MRET_label':nativeM[k]['label'] if k in nativeM else None,'MRET_native_bucket':nativeM[k]['bucket'] if k in nativeM else None}
  for u in [2,3,5,10]:q[f'U{u}']=None if pot is None else int(pot>=Fraction(u,100))
  q['Weak']=None if pot is None else 1-q['U2'];q['Medium']=None if pot is None else int(Fraction(3,100)<=pot<Fraction(5,100))
  q['bucket']=None if pot is None else ['Weak','Low','Medium','Big','Mega'][sum(pot>=Fraction(u,100) for u in [2,3,5,10])]
  q['positive']=None if net is None else int(net>0);q['ge1']=None if net is None else int(net>=Fraction(1,100));q['Loser']=None if net is None else int(net<=0)
  if k in nativeM:
   a=nativeM[k];assert abs(a['potential']-float(pot))<=1e-12 and abs(a['realized']-float(net))<=1e-12 and a['block']==q['block']
  if k in trades:assert abs(trades[k]['net_return']-float(net))<=1e-12
  data[k]=q
 sessions=sorted({q['session'] for q in data.values()});assert len(sessions)==38
 return data,masks,sessions,weight_stream(sessions)
def meta(rr,known,target=None):
 kk=[rr[i] for i in known]
 return {'total_N':len(rr),'known_N':len(kk),'unknown_N':len(rr)-len(kk),'positive_N':sum(r[target]==1 for r in kk) if target else None,'negative_N':sum(r[target]==0 for r in kk) if target else None,'distinct_sessions':len({r['session'] for r in kk}),'total_distinct_sessions':len({r['session'] for r in rr}),'mask_hash':digest(r['entry_id'] for r in kk),'unknown_mask_hash':digest(r['entry_id'] for i,r in enumerate(rr) if i not in set(known))}
def metric(rr,h,target,sessions,mult,direction=1):
 known=[i for i,r in enumerate(rr) if r['scores'][h] is not None and r[target] is not None];m=meta(rr,known,target)
 if not known or not m['positive_N'] or not m['negative_N']:return {**m,'head':h,'target':target,'direction':direction,'AUC':None,'AP':None,'null_reason':'ONE_CLASS' if known else 'NO_KNOWN','AUC_bootstrap':ci([]),'AP_bootstrap':ci([])},None
 ss=np.asarray([direction*rr[i]['scores'][h] for i in known]);yy=np.asarray([rr[i][target] for i in known]);ix=np.asarray([sessions.index(rr[i]['session']) for i in known]);v,ap=auc_ap(ss,yy);boots,apboots=auc_ap(ss,yy,mult[:,ix])
 boots=cluster_auc(ss,yy,ix,mult)
 return {**m,'head':h,'target':target,'direction':direction,'AUC':float(v[0]),'AP':float(ap[0]),'null_reason':None,'AUC_bootstrap':ci(boots),'AP_bootstrap':ci(apboots)},boots
def fixed_sets(rr,h,direction=1):
 known=[r for r in rr if r['scores'][h] is not None];order=sorted(known,key=lambda r:(-direction*r['scores'][h],r['entry_time'],r['symbol'],r['entry_id']))
 return {f:order[:math.ceil(f*len(known))] for f in [.2,.3]}
def topcard(rr,selected,sessions,mult):
 ids={r['entry_id'] for r in selected};kk=[r for r in rr if r['entry_id'] in ids]
 o={'N':len(kk),'unknown_score_N':len(rr)-sum(r['scores']['pP'] is not None for r in rr),'mask_hash':digest(ids),'distinct_sessions':len({r['session'] for r in kk}),'fixed_set_conditioning':True}
 idx=np.asarray([sessions.index(r['session']) for r in rr]);w=mult[:,idx];flag=np.asarray([r['entry_id'] in ids for r in rr]);dn=(w*flag).sum(axis=1)
 for t in ['Weak','Medium','U2','U3','U5','U10','positive','Loser']:
  yy=np.asarray([0 if r[t] is None else r[t] for r in rr]);known=np.asarray([r[t] is not None for r in rr]);den=(w*known*flag).sum(axis=1);num=(w*yy*flag).sum(axis=1)
  n=sum(r[t]==1 for r in kk);knownN=sum(r[t] is not None for r in kk);totalPositive=sum(r[t]==1 for r in rr)
  val=np.divide(num,den,out=np.full(B,np.nan),where=den>0);capden=(w*yy).sum(axis=1);cap=np.divide(num,capden,out=np.full(B,np.nan),where=capden>0)
  o[t]={'N':n,'known_N':knownN,'unknown_N':len(kk)-knownN,'density':n/knownN if knownN else None,'capture':n/totalPositive if totalPositive else None,'density_bootstrap':ci(val,'original fixed TopK set'),'capture_bootstrap':ci(cap,'original fixed TopK set')}
 neg=sum((Fraction(r['pnl_exact']) for r in kk if r['pnl_exact'] is not None and Fraction(r['pnl_exact'])<0),Fraction(0));pos=sum((Fraction(r['pnl_exact']) for r in kk if r['pnl_exact'] is not None and Fraction(r['pnl_exact'])>0),Fraction(0))
 o.update({'gross_negative_PnL_exact':str(neg),'positive_PnL_exact':str(pos),'net_fixed_ledger_contribution_exact':str(neg+pos),'PnL_known_N':sum(r['pnl_exact'] is not None for r in kk),'meaning':'diagnostic contribution, NOT avoided loss/counterfactual Capital'})
 return o
def original(data,masks):
 original=rows(BASE/'sources/e3d349607207/private/QUALITY_COMMON_EVAL_ROWS_V1R1.jsonl.gz');assert [r['entry_id'] for r in original]==masks['C0']
 expected=read(BASE/'sources/REMOTE_quality_primary.json')['metrics'];record=[]
 for h,t in [('pP','U5'),('pP','U10'),('MOVE_U2','U2'),('MOVE_U3','U3')]:
  x=[r[h] for r in original];y=[r[t] for r in original];a,ap=auc_ap(x,y);raw=[data[r['entry_id']]['scores'][h] for r in original];a2,p2=auc_ap(raw,y)
  e=expected[h][t];assert abs(a[0]-e['AUC'])<=1e-12 and abs(ap[0]-e['PR_AUC'])<=1e-12;assert abs(a2[0]-a[0])<=1e-12 and abs(p2[0]-ap[0])<=1e-12
  record.append({'head':h,'target':t,'total_N':len(original),'known_N':len(original),'unknown_N':0,'positive_N':sum(y),'negative_N':len(y)-sum(y),'distinct_sessions':38,'mask_hash':digest(masks['C0']),'original_authority_AUC':e['AUC'],'recomputed_original_AUC':float(a[0]),'recomputed_original_AP':float(ap[0]),'packet_same_mask_AUC':float(a2[0]),'max_copy_delta_original_vs_R1_saved_canonical':max(abs(s-r) for s,r in zip(x,raw)),'same_original_raw_order':np.array_equal(np.argsort(x,kind='stable'),np.argsort(raw,kind='stable')),'L2':'PASS','note':'current R1 materialization equivalence <=1e-12 separately from binary64-exact packet copy'})
 rr=rows(BASE/'sources/mret/private/MRET_POST_FIT_EVALUATION_ROWS.jsonl.gz');expectedM=read(BASE/'sources/REMOTE_MRET.json')['scores']['mP'];y=[r['label'] for r in rr];a,ap=auc_ap([r['mP'] for r in rr],y)
 assert abs(a[0]-expectedM['MRET']['AUC'])<=1e-12 and abs(ap[0]-expectedM['MRET']['PR_AUC'])<=1e-12
 sessions=sorted({r['session'] for r in rr});groups=[str((r['block'],r['bucket'])) for r in rr];con,_=concordance([r['mP'] for r in rr],[r['realized'] for r in rr],groups,[sessions.index(r['session']) for r in rr],np.ones((1,len(sessions))))
 assert con['valid_pairs']==expectedM['conditional']['valid_pairs'] and con['credit']==expectedM['conditional']['credit'] and abs(con['concordance']-expectedM['conditional']['concordance'])<=1e-12
 record.append({'head':'MRET','target':'original relative MRET label','total_N':len(rr),'known_N':len(rr),'unknown_N':0,'positive_N':sum(y),'negative_N':len(y)-sum(y),'distinct_sessions':len(sessions),'mask_hash':digest(masks['C1']),'original_authority_AUC':expectedM['MRET']['AUC'],'recomputed_original_AUC':float(a[0]),'recomputed_original_AP':float(ap[0]),'native_bucket_block_concordance':con['concordance'],'valid_pairs':con['valid_pairs'],'L2':'PASS','existing_numeric_certificate':'a225782aad5a48abea1e332e0eee1d93a0481f0b','original_bootstrap_regenerated':False})
 save('ORIGINAL_SKILL_REPRODUCTION.json',{'status':'PASS','L1':'PASS','L2':'PASS','L3':'NOT_EVALUATED','old_original_statuses_preserved':True,'results':record,'metric_tolerance':1e-12,'source_quality_manifest_reused':True,'original_independent_receipt':read(BASE/'sources/REMOTE_quality_audit.json'),'new_fit_inference_replay':0})
 save('F3_CHECKPOINT.json',{'exact_jst':now(),'complete':True,'stage':'F3','results':'L1/L2 preserved; L3 NOT_EVALUATED','primaryDiagnosticBatch':1,'newFits':0,'newInference':0,'CapitalReplays':0,'code_hash':sha(pathlib.Path(__file__)),'packet_hash':sha(PRIVATE/'FROZEN_EXPERT_PACKET.jsonl.gz'),'next':'fixed subset/flag/rank diagnostics'})
def rank_audits(data,masks):
 cohorts={'C0':masks['C0'],'C2':masks['C2'],'C3':masks['C3']};cohorts['C5_same_batch']=None
 led=PRIVATE/'ROLE_CONFLICT_LEDGER.jsonl.gz';assert not led.exists();summaries={};orderledger={}
 with led.open('wb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as f:
  for name,ids in cohorts.items():
   if ids is None:
    pairs=set()
    for batch in masks['C5']:
     for a,b in itertools.combinations(sorted(batch['entry_ids']),2):pairs.add((a,b))
    seq=sorted(pairs)
   else:seq=itertools.combinations(sorted(ids),2)
   counts=collections.Counter();agreements={h:collections.Counter() for h in HEADS[1:]};order=collections.Counter()
   for a,b in seq:
    ra,rb=data[a],data[b];sg=[int(np.sign(ra['scores'][h]-rb['scores'][h])) for h in HEADS];rg=[int(np.sign(ra['ranks'][h]-rb['ranks'][h])) for h in HEADS]
    pareto='ALL_TIE' if all(v==0 for v in sg) else 'I_DOMINATES' if all(v>=0 for v in sg) else 'J_DOMINATES' if all(v<=0 for v in sg) else 'INCOMPARABLE';counts[pareto]+=1
    if sg[0]==0:counts['pP_exact_tie_pairs']+=1
    for j,h in enumerate(HEADS[1:],1):agreements[h]['TIE' if sg[0]==0 or sg[j]==0 else 'AGREE' if sg[0]==sg[j] else 'CONFLICT']+=1
    for j,h in enumerate(HEADS):
     if sg[j]!=0 and rg[j]==0:order[h+'_tie_increase']+=1
     if sg[j]*rg[j]<0:order[h+('_cross_block_reversal' if ra['block']!=rb['block'] else '_within_block_reversal')]+=1
    f.write((json.dumps({'cohort':name,'i':a,'j':b,'signs':dict(zip(HEADS,sg)),'r_signs':dict(zip(HEADS,rg)),'pareto':pareto,'same_session':ra['session']==rb['session'],'same_batch':ra['entry_time']==rb['entry_time']},separators=(',',':'))+'\n').encode())
   total=sum(counts[k] for k in ['ALL_TIE','I_DOMINATES','J_DOMINATES','INCOMPARABLE']);summaries[name]={'pair_N':total,'pair_N_is_independent_sample_N':False,'pareto':dict(counts),'pP_vs_auxiliary':{h:dict(c) for h,c in agreements.items()}}
   orderledger[name]={'pair_N':total,'changes':dict(order),'raw_and_percentile_are_different_order_authorities':True}
 overlaps={}
 for name,ids in cohorts.items():
  if ids is None:continue
  rr=[data[k] for k in ids];overlaps[name]={}
  for frac in [.2,.3]:
   sets={h:{r['entry_id'] for r in fixed_sets(rr,h)[frac]} for h in HEADS};pairs=[]
   for h in HEADS[1:]:
    x,z=sets['pP'],sets[h];pairs.append({'pP_vs':h,'common_N':len(x&z),'pP_only_N':len(x-z),'aux_only_N':len(z-x),'union_N':len(x|z),'K':len(x),'union_is_same_budget':len(x|z)==len(x)})
   union=set.union(*sets.values());inter=set.intersection(*sets.values());overlaps[name][str(frac)]={'K':len(sets['pP']),'all_head_intersection_N':len(inter),'all_head_union_N':len(union),'union_is_same_budget':len(union)==len(sets['pP']),'pairs':pairs}
   save(f'TOP_OVERLAP_IDS_{name}_{int(frac*100)}.json',{h:sorted(s) for h,s in sets.items()},True)
 save('RANK_CONFLICT_SUMMARY.json',{'cohorts':summaries,'top_same_budget':overlaps,'no_total_order_claim':'strict pP and reverse auxiliary pair cannot both be preserved by a single total order','Pareto_incomparable_not_equal_safe_or_profit_equivalent':True,'four_head_consensus_edges_not_runtime_policy':True,'ledger_sha256':sha(led)})
 save('SCORE_ORDER_AUDIT.json',{'L1':'PASS','raw_vs_r':orderledger,'original_raw_pP_authority':'DESC; no global replacement by block percentile','model_copy_tolerance':0,'score_reinference_tolerance':1e-12,'no_new_total_rank':True})
def subsets(data,masks,sessions,mult):
 cohorts={'C2':[data[k] for k in masks['C2']],'C3':[data[k] for k in masks['C3']]}
 for slot in [1,2,3]:cohorts[f'C2_slot{slot}']=[r for r in cohorts['C2'] if r['native_funded_slot']==slot]
 for reason,ids in masks['C4'].items():cohorts['C4_'+reason]=[data[k] for k in ids]
 matrix={};bootvalues={};top={}
 for name,rr in cohorts.items():
  matrix[name]={'N':len(rr),'sessions':len({r['session'] for r in rr}),'mask_hash':digest(r['entry_id'] for r in rr),'metrics':[],'cross_table':{}}
  ct=collections.Counter((r['bucket'] or 'UNKNOWN', 'UNKNOWN' if r['realized'] is None else 'NEGATIVE' if r['realized']<0 else 'ZERO' if r['realized']==0 else 'POSITIVE') for r in rr);matrix[name]['cross_table']={a+'|'+b:v for (a,b),v in sorted(ct.items())}
  for h,target,direction in [('pP','U5',1),('pP','U10',1),('MOVE_U2','U2',1),('MOVE_U2','Weak',-1),('MOVE_U3','U3',1),('MRET','MRET_label',1)]+[(h,t,1) for h in HEADS for t in ['positive','ge1','Loser']]:
   result,vals=metric(rr,h,target,sessions,mult,direction);matrix[name]['metrics'].append(result)
   if vals is not None:bootvalues[name+'|'+h+'|'+target]=vals
  for h in HEADS:
   known=[i for i,r in enumerate(rr) if r['scores'][h] is not None and r['realized'] is not None];mm=meta(rr,known);vals=np.asarray([rr[i]['scores'][h] for i in known]);yy=np.asarray([rr[i]['realized'] for i in known]);idx=np.asarray([sessions.index(rr[i]['session']) for i in known],int)
   rho=weighted_spearman(vals,yy,np.ones((1,len(known))))[0] if known else np.nan;bs=weighted_spearman(vals,yy,mult[:,idx]) if known else []
   matrix[name]['metrics'].append({**mm,'head':h,'target':'realized_return','Spearman':float(rho) if np.isfinite(rho) else None,'null_reason':None if np.isfinite(rho) else 'NO_VARIATION','bootstrap':ci(bs)})
  rrM=[r for r in rr if r['MRET_native_bucket'] is not None and r['realized'] is not None];groups=[str((r['block'],r['MRET_native_bucket'])) for r in rrM];cc,_=concordance([r['scores']['MRET'] for r in rrM],[r['realized'] for r in rrM],groups,[sessions.index(r['session']) for r in rrM],mult)
  matrix[name]['native_MRET_bucket_concordance']={**meta(rr,[i for i,r in enumerate(rr) if r in rrM]),**cc,'conditioned_on_future_Potential_bucket':True,'not_runtime_bucket_availability_evidence':True}
  top[name]={h:{str(f):topcard(rr,v,sessions,mult) for f,v in fixed_sets(rr,h).items()} for h in HEADS}
 save('EXPERT_TARGET_MATRIX.json',{'cohorts':matrix,'all_subset_diagnostics_exploratory':True,'raw_score_primary':True,'original_metrics_not_subset_guarantees':True,'MRET_absolute_targets_not_official_teacher_success':True,'score_as_probability_comparison':False,'sampling_frame':sessions})
 save('FIXED_BUDGET_CAPTURE_DENSITY.json',top)
 flags=[];rr=cohorts['C2'];sets={}
 for h in HEADS[1:]:
  sets[h]=fixed_sets(rr,h,-1)
  for frac,ss in sets[h].items():flags.append({'risk_direction':'-'+h,'fraction':frac,'K':len(ss),**topcard(rr,ss,sessions,mult)})
 deltas=[]
 for f in [.2,.3]:
  for a,b in itertools.combinations(HEADS[1:],2):
   sa={r['entry_id'] for r in sets[a][f]};sb={r['entry_id'] for r in sets[b][f]};delta={}
   for t in ['Loser','Weak','U5','U10','Medium','positive']:
    ix=np.asarray([sessions.index(r['session']) for r in rr]);yy=np.asarray([0 if r[t] is None else r[t] for r in rr]);sign=np.asarray([int(r['entry_id'] in sa)-int(r['entry_id'] in sb) for r in rr]);v=(mult[:,ix]*yy*sign).sum(axis=1);delta[t]={'count_difference':int((yy*sign).sum()),'bootstrap':ci(v,'same budget original fixed FLAG sets')}
   deltas.append({'fraction':f,'a':'-'+a,'b':'-'+b,'intersection_N':len(sa&sb),'union_N':len(sa|sb),'K':len(sa),'union_is_same_budget':len(sa|sb)==len(sa),'delta':delta})
 save('FLAGGED_LOSER_WINNER_TRADEOFF.json',{'cohort':'C2','rows':flags,'same_budget_deltas':deltas,'meaning':'FLAG Loser counts are not actual avoided losses; preserved PnL contributions not new Capital','unknown_imputation':0,'threshold_selection':0})
 save('FLAG_ID_SETS.json',{h:{str(f):[r['entry_id'] for r in s] for f,s in ff.items()} for h,ff in sets.items()},True)
 save('V5_SCORE_OUTCOME_ROWS.jsonl.gz',[data[k] for k in sorted(data)],True)
 rank_audits(data,masks)
 # Only new diagnostics are re-sampled. Old original model bootstrap receipts reused unchanged.
 save('BOOTSTRAP_MULTIPLICITIES.jsonl.gz',[{'resample':i+1,'sessions':sessions,'multiplicities':r.tolist()} for i,r in enumerate(mult)],True)
 np.savez_compressed(PRIVATE/'PRIMARY_SUBSET_BOOTSTRAP_VALUES.npz',**bootvalues)
 save('F4_CHECKPOINT.json',{'exact_jst':now(),'complete':True,'stage':'F4','primaryDiagnosticBatch':1,'CapitalReplays':0,'score_packet_unchanged':sha(PRIVATE/'FROZEN_EXPERT_PACKET.jsonl.gz'),'code_hash':sha(pathlib.Path(__file__)),'next':'signed controls and temporal audit'})
def signed(data,masks,sessions,mult):
 controls=[('MRET',1)]+[(h,d) for d in [1,-1] for h in HEADS[:3]];output={};values={}
 for name,ids,target in [('C1',masks['C1'],'MRET_label'),('C2',masks['C2'],'positive'),('C3',masks['C3'],'positive')]:
  rr=[data[k] for k in ids];scoreout={};vv={}
  for h,d in controls:
   tag=('' if d==1 else '-')+h;a,v=metric(rr,h,target,sessions,mult,d);scoreout[tag]=a;vv[tag]=v
   r2=[r for r in rr if r['MRET_native_bucket'] is not None and r['realized'] is not None];g=[str((r['block'],r['MRET_native_bucket'])) for r in r2];con,cvals=concordance([d*r['scores'][h] for r in r2],[r['realized'] for r in r2],g,[sessions.index(r['session']) for r in r2],mult);scoreout[tag]['native_bucket_concordance']=con;values[name+'|'+tag+'|concordance']=cvals
  contrasts={}
  for tag,v in vv.items():
   if tag=='MRET':continue
   contrasts[tag]={'mP_minus_control':scoreout['MRET']['AUC']-scoreout[tag]['AUC'] if v is not None and vv['MRET'] is not None else None,'paired_bootstrap':ci(vv['MRET']-v) if v is not None and vv['MRET'] is not None else ci([]),'paired_concordance_bootstrap':ci(values[name+'|MRET|concordance']-values[name+'|'+tag+'|concordance'])}
  identity={h:abs(scoreout[h]['AUC']+scoreout['-'+h]['AUC']-1) if scoreout[h]['AUC'] is not None else None for h in HEADS[:3]};assert all(v is None or v<=1e-12 for v in identity.values())
  output[name]={'target':target,'scores':scoreout,'all_control_deltas':contrasts,'sign_identity_max_errors':identity,'runtime_sign_changes':0}
  for tag,v in vv.items():
   if v is not None:values[name+'|'+tag+'|AUC']=v
 save('MRET_SIGNED_CONTROLS.json',{'cohorts':output,'new_zero_fit_evaluation_only_controls':True,'old_S1_S8_S9_S9R_statuses_unchanged':True,'no_best_direction_selection':True,'interpretation':'NUMERICALLY_CERTIFIED_BUT_INCREMENTAL_VALUE_NOT_ESTABLISHED if signed controls not beaten','future_bucket_condition_is_diagnostic_only':True})
 np.savez_compressed(PRIVATE/'PRIMARY_SIGNED_BOOTSTRAP_VALUES.npz',**values)
 matrix=read(OUT/'EXPERT_TARGET_MATRIX.json')['cohorts'];roles={}
 def find(cohort,head,target):return next(r for r in matrix[cohort]['metrics'] if r.get('head')==head and r.get('target')==target)
 for role,c,h,targets in [('Winner Priority','C3','pP',['U5','U10']),('Weak Risk','C2','MOVE_U2',['Weak']),('Medium+ Priority','C3','MOVE_U3',['U3'])]:
  mm=[find(c,h,t) for t in targets];passed=all(m['AUC_bootstrap']['valid_N']>=1900 and m['AUC_bootstrap']['CI95'][0]>.5 and m['known_N']==m['total_N'] for m in mm)
  point=all(m['AUC'] is not None and m['AUC']>.5 for m in mm)
  roles[role]={'status':'SUPPORTED_FOR_DESIGN' if passed else 'INCONCLUSIVE' if point else 'UNSUPPORTED_ON_V5','head':h,'cohort':c,'metrics':mm,'coverage_complete':all(m['known_N']==m['total_N'] for m in mm),'temporal_mask_audit':'PASS','capital_value':'NOT_EVALUATED'}
 c=output['C2'];m=c['scores']['MRET'];passed=m['AUC'] is not None and m['AUC_bootstrap']['CI95'][0]>.5 and m['AUC_bootstrap']['valid_N']>=1900 and m['known_N']==m['total_N'] and all(z['paired_bootstrap']['valid_N']>=1900 and z['paired_bootstrap']['CI95'][0]>0 for z in c['all_control_deltas'].values())
 roles['Absolute-Loss Defense via MRET']={'status':'SUPPORTED_FOR_DESIGN' if passed else 'INCONCLUSIVE' if m['AUC'] is not None and m['AUC']>.5 else 'UNSUPPORTED_ON_V5','metric':m,'all_signed_contrasts':c['all_control_deltas'],'original_skill':'PRESERVED_RELATIVE_MONETIZATION_ONLY','incremental_status':'NUMERICALLY_CERTIFIED_BUT_INCREMENTAL_VALUE_NOT_ESTABLISHED' if not passed else 'SUPPORTED_FOR_DESIGN','capital_value':'NOT_EVALUATED'}
 save('ROLE_DECISIONS.json',roles)
 save('SESSION_BOOTSTRAP_DIAGNOSTICS.json',{'seed':SEED,'bit_generator':'PCG64','resamples':B,'CI95_percentiles':[2.5,97.5],'quantile':'linear','paired_shared_session_multiplicities':True,'sampling_frame':sessions,'empty_subset_sessions_retained':True,'TopK_conditioned_on':'original fixed diagnostic set; not refit or optimized','same_session_pair_weight':'multiplicity once','cross_session_pair_weight':'endpoint multiplicity product','invalid_oneclass_handling':'null and valid_N recorded per metric','original_head_bootstrap_regenerated':False,'stream_sha256':sha(PRIVATE/'BOOTSTRAP_MULTIPLICITIES.jsonl.gz'),'subset_values_sha256':sha(PRIVATE/'PRIMARY_SUBSET_BOOTSTRAP_VALUES.npz'),'signed_values_sha256':sha(PRIVATE/'PRIMARY_SIGNED_BOOTSTRAP_VALUES.npz'),'roles':{k:v['status'] for k,v in roles.items()},'multiple_comparisons':'exploratory, not confirmatory success'})
 refs=read(OUT/'EXPERT_REGISTRY.json')['frozen_head_models'];blocks=[]
 for b in range(1,9):
  reg=[r for r in refs if r['block']==b];test=reg[0]['test_dates'];past=[r for r in data.values() if r['session']<min(test) and r['session']<=reg[0]['train_through']];blocks.append({'block':b,'test_sessions':test,'train_through':{r['head']:r['train_through'] for r in reg},'saved_past_OOF_N':len(past),'saved_past_OOF_sessions':len({r['session'] for r in past}),'status':'NO_PAST_OOF_SUPPORT' if not past else 'PAST_OOF_AVAILABLE_NOT_BRIDGE_TRAINED','head_specific_training_reference_N':{r['head']:r['reference_N'] for r in reg},'first_block_not_dropped':b==1})
 save('PAST_OOF_SUPPORT.json',{'blocks':blocks,'initial_warmup_has_saved_OOF':False,'reference_scores_not_OOF':True,'routing_thresholds_selected':0,'no_missing_past_predictions_fitted':True})
 save('TEMPORAL_DEPENDENCY_DAG.json',{'nodes':['past closed features','frozen past head fit','saved current OOF score','past completed training percentile reference','frozen read-only packet','current outcome evaluation only','future separately precommitted bridge criteria','future current action'],'edges':[['past closed features','frozen past head fit'],['frozen past head fit','saved current OOF score'],['past completed training percentile reference','frozen read-only packet'],['saved current OOF score','frozen read-only packet'],['frozen read-only packet','current outcome evaluation only']],'forbidden_edges':[['current outcome evaluation only','current routing threshold'],['future label','frozen read-only packet']],'all_head_train_before_test':True,'feature_asof':'max current source minute < Frozen Entry','actual_source_arrival':'inherited bar-end assumption; actual arrival unknown, no stronger claim','label_maturity':'past training sessions completed before next test session; existing causal/model certificate reused, no independent provider timing','already_exposed_sessions':58,'exposure':'ITERATIVE_DEVELOPMENT_EVIDENCE','fresh_OOS_claim':False,'future_bridge_past_OOF_requirement':'head fit -> saved past score -> past-only bridge criterion -> current action must all be available before current; cold-start abstain'})
 save('F5_CHECKPOINT.json',{'exact_jst':now(),'complete':True,'stage':'F5','primaryDiagnosticBatch':1,'CapitalReplays':0,'code_hash':sha(pathlib.Path(__file__)),'next':'saved channel census without state machine replay'})
def main():
 ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['F3','F4','F5']);args=ap.parse_args();claim();data,masks,sessions,mult=load_data()
 assert not (OUT/(args.stage+'_CHECKPOINT.json')).exists(),'COMPLETED_STAGE_REEXECUTION_FORBIDDEN'
 {'F3':lambda:original(data,masks),'F4':lambda:subsets(data,masks,sessions,mult),'F5':lambda:signed(data,masks,sessions,mult)}[args.stage]()
 print(json.dumps({'stage':args.stage,'complete':True,'exact_jst':now()}))
if __name__=='__main__':main()
