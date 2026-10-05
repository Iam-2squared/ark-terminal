"""Standalone verification from saved originals; no primary adapter/evaluator/metric imports.

Shared sources, NumPy/SciPy and one researcher are disclosed. Not blind external independence.
"""
import ast,collections,datetime,gzip,hashlib,json,pathlib,math,struct,argparse
from fractions import Fraction
import numpy as np
from scipy.stats import spearmanr
ROOT=pathlib.Path('/workspace/scratch/f3d0aa747c89');W=ROOT/'bridge_work';E=W/'evidence';P=W/'private';H=['pP','MOVE_U2','MOVE_U3','MRET'];R=1999
def get(p):return json.loads(pathlib.Path(p).read_text())
def lines(p):
 with gzip.open(p,'rt') as f:return [json.loads(l) for l in f]
def hashfile(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def mask(ids):return hashlib.sha256(json.dumps(sorted(ids),separators=(',',':')).encode()).hexdigest()
def emit(name,obj):
 p=E/name;assert not p.exists();p.write_text(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n')
def interval(a):
 a=np.asarray(a);valid=a[np.isfinite(a)];return np.quantile(valid,[.025,.975],method='linear').tolist() if len(valid) else None
def independent_auc(s,y,idx=None,M=None):
 # Positive-negative pair credit, accumulated by endpoint sessions. Same-session m once.
 s=np.asarray(s);y=np.asarray(y);pos=np.flatnonzero(y==1);neg=np.flatnonzero(y==0)
 if not len(pos) or not len(neg):return None,np.full(R,np.nan)
 credit=.5+.5*np.sign(s[pos,None]-s[neg]);point=float(credit.sum()/(len(pos)*len(neg)))
 if M is None:return point,None
 n=M.shape[1];C=np.zeros((n,n));D=np.zeros((n,n))
 for j,i in enumerate(pos):
  np.add.at(C,(np.full(len(neg),idx[i]),idx[neg]),credit[j]);np.add.at(D,(np.full(len(neg),idx[i]),idx[neg]),1)
 diagonalC=np.diag(C).copy();diagonalD=np.diag(D).copy();np.fill_diagonal(C,0);np.fill_diagonal(D,0)
 # This is not an independent pair bootstrap: cluster multiplicities are shared.
 a=(M@(C+D*0)*M).sum(axis=1)+M@diagonalC;b=(M@D*M).sum(axis=1)+M@diagonalD
 return point,np.divide(a,b,out=np.full(R,np.nan),where=b>0)
def independent_ap(s,y,weights=None):
 s=np.asarray(s);y=np.asarray(y);weights=np.ones((1,len(s))) if weights is None else weights
 z=np.argsort(-s,kind='stable');starts=np.r_[0,1+np.flatnonzero(s[z][1:]!=s[z][:-1])];pos=np.add.reduceat(weights[:,z]*y[z],starts,axis=1);allw=np.add.reduceat(weights[:,z],starts,axis=1)
 p=pos.sum(axis=1);n=weights.sum(axis=1)-p;cp=pos.cumsum(axis=1);tot=allw.cumsum(axis=1)
 a=(np.divide(cp,tot,out=np.zeros_like(cp,dtype=float),where=tot>0)*pos).sum(axis=1)
 return np.divide(a,p,out=np.full(len(p),np.nan),where=(p>0)&(n>0))
def original_data():
 cc=lines(ROOT/'r1_work/score_certification/CURRENT_FOUR_HEAD_INTELLIGENCE.jsonl.gz');native={r['entry_id']:r for r in lines(ROOT/'r1_work/runs/OFF_PRIMARY/DECISIONS.jsonl.gz')};mm={r['entry_id']:r for r in lines(W/'sources/mret/private/MRET_POST_FIT_EVALUATION_ROWS.jsonl.gz')};oo=get(ROOT/'r1_work/metrics/evaluation_only/OUTCOMES_EXACT_EVALUATION.json');runtime={r['entry_id']:r for r in lines(ROOT/'r1_work/inputs/v8r1/inputs/movement/RUNTIME_CAUSAL.jsonl.gz')};tr={r['entry_id']:r for r in lines(ROOT/'r1_work/runs/OFF_PRIMARY/TRADES.jsonl.gz')};dd={}
 for r in cc:
  k=r['entry_id'];o=oo[k];pot=Fraction(o['potential_return_source_cell']) if o['potential_return_source_cell'] is not None else None;net=Fraction(o['frozen_realized_net_return_cell']) if o['frozen_realized_net_return_cell'] is not None else None
  z={'entry_id':k,'session':r['session'],'block':r['block'],'time':runtime[k]['entry_timestamp'],'symbol':runtime[k]['symbol'],'s':{h:r[h]['score'] for h in H},'rank':{h:r[h]['rank_numerator']/r[h]['rank_denominator'] for h in H},'slot':native[k].get('funded_slot'),'reason':native[k]['reason'],'realized_return':float(net) if net is not None else None,'MRET_label':mm[k]['label'] if k in mm else None,'nativebucket':mm[k]['bucket'] if k in mm else None,'pnl':Fraction(tr[k]['pnl']) if k in tr else None}
  for u in [2,3,5,10]:z['U'+str(u)]=int(pot>=Fraction(u,100)) if pot is not None else None
  z['Weak']=1-z['U2'] if pot is not None else None;z['Medium']=int(Fraction(3,100)<=pot<Fraction(5,100)) if pot is not None else None;z['positive']=int(net>0) if net is not None else None;z['ge1']=int(net>=Fraction(1,100)) if net is not None else None;z['Loser']=int(net<=0) if net is not None else None;z['bucket']=None if pot is None else ['Weak','Low','Medium','Big','Mega'][sum(pot>=Fraction(u,100) for u in [2,3,5,10])];dd[k]=z
 return dd,native,runtime
def full():
 assert not (E/'INDEPENDENT_INITIAL_AUDIT.json').exists(),'independent verification already started; resume comparisons only'
 sources={str(p.relative_to(ROOT)):hashfile(p) for p in [ROOT/'r1_work/score_certification/CURRENT_FOUR_HEAD_INTELLIGENCE.jsonl.gz',ROOT/'r1_work/score_certification/TRAINING_REFERENCE_POPULATIONS.json',ROOT/'r1_work/runs/OFF_PRIMARY/DECISIONS.jsonl.gz',ROOT/'r1_work/runs/OFF_PRIMARY/NATIVE_PROPOSALS.jsonl.gz',ROOT/'r1_work/metrics/evaluation_only/OUTCOMES_EXACT_EVALUATION.json']}
 emit('INDEPENDENT_DIAGNOSTIC_CLAIM.json',{'independentDiagnosticVerification':1,'exact_jst':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),'code_sha256':hashfile(__file__),'source_hashes':sources,'primary_imports':0,'new_fit_inference_replay':0,'independence_scope':'separate algorithm, same researcher/sources/shared NumPy SciPy; not blind external'})
 dd,native,runtime=original_data();current={r['entry_id']:r for r in lines(ROOT/'r1_work/score_certification/CURRENT_FOUR_HEAD_INTELLIGENCE.jsonl.gz')};packet=lines(P/'FROZEN_EXPERT_PACKET.jsonl.gz');coh=get(P/'COHORT_MASKS.json');checks=[];fail=[];values={};apvalues={}
 def check(name,ok,detail=None):
  checks.append(name)
  if not ok:fail.append({'check':name,'detail':detail})
 def close(a,b):return (a is None and b is None) or (a is not None and b is not None and abs(a-b)<=1e-12)
 check('packet1039 unique',len(packet)==len({r['entry_id'] for r in packet})==1039)
 ref={(r['block'],r['head']):r for r in get(ROOT/'r1_work/score_certification/TRAINING_REFERENCE_POPULATIONS.json')}
 for p in packet:
  k=p['entry_id'];r=current[k];check('packet identity '+k,(p['session'],p['frozen_entry_time'],p['symbol'])==(r['session'],runtime[k]['entry_timestamp'],runtime[k]['symbol']))
  check('future fields excluded '+k,not any(f in p for f in ['potential','realized','EXIT','protected100','future_source_available']))
  for h in H:
   t=ref[(r['block'],h)];num=1+sum(v<r[h]['score'] for v in t['scores']);den=t['reference_N']+1;v=p['heads'][h]
   check('copy fraction '+k+h,struct.pack('d',v['raw_score'])==struct.pack('d',r[h]['score']) and v['numerator']==num and v['denominator']==den and v['LOW']==(num*2<den) and v['HIGH']==(num*2>=den))
 long=lines(ROOT/'r1_work/metrics/supplement/V5_FUNDED150_FOUR_SCORE_NATIVE_SLOT.jsonl.gz');wide={}
 for r in long:
  check('long duplicate '+r['entry_id']+r['head'],r['head'] not in wide.setdefault(r['entry_id'],{}));wide[r['entry_id']][r['head']]=r
 check('600long->150wide',len(long)==600 and len(wide)==150 and all(set(v)==set(H) for v in wide.values()))
 check('C2 exact',set(wide)==set(coh['C2']));check('slots exact',dict(collections.Counter(native[k]['funded_slot'] for k in wide))=={1:41,2:59,3:50})
 common=lines(W/'sources/e3d349607207/private/QUALITY_COMMON_EVAL_ROWS_V1R1.jsonl.gz');mre=lines(W/'sources/mret/private/MRET_POST_FIT_EVALUATION_ROWS.jsonl.gz')
 check('C0 original mask',[r['entry_id'] for r in common]==coh['C0']);check('C1 original mask',[r['entry_id'] for r in mre]==coh['C1']);check('C3 original mask',set(coh['C3'])=={k for k,v in native.items() if v['admission']})
 qp=get(W/'sources/REMOTE_quality_primary.json')['metrics']
 for h,t in [('pP','U5'),('pP','U10'),('MOVE_U2','U2'),('MOVE_U3','U3')]:
  a,_=independent_auc([r[h] for r in common],[r[t] for r in common]);ap=independent_ap([r[h] for r in common],[r[t] for r in common])[0];check('original '+h+t,close(a,qp[h][t]['AUC']) and close(ap,qp[h][t]['PR_AUC']))
 sessions=sorted({r['session'] for r in dd.values()});rng=np.random.Generator(np.random.PCG64(570100520));M=np.asarray([np.bincount(rng.integers(0,38,38),minlength=38) for _ in range(R)]);saved=lines(P/'BOOTSTRAP_MULTIPLICITIES.jsonl.gz');check('PCG64 stream exact',np.array_equal(M,np.asarray([r['multiplicities'] for r in saved])))
 matrix=get(E/'EXPERT_TARGET_MATRIX.json')['cohorts'];cohorts={'C2':coh['C2'],'C3':coh['C3']}
 for slot in [1,2,3]:cohorts['C2_slot'+str(slot)]=[k for k in coh['C2'] if dd[k]['slot']==slot]
 cohorts.update({'C4_'+r:ids for r,ids in coh['C4'].items()})
 for name,ids in cohorts.items():
  check('subset mask '+name,matrix[name]['N']==len(ids) and matrix[name]['mask_hash']==mask(ids))
  for metric in matrix[name]['metrics']:
   h,t=metric['head'],metric['target'];direction=metric.get('direction',1);rr=[dd[k] for k in ids if dd[k]['s'][h] is not None and dd[k][t] is not None];s=np.asarray([direction*r['s'][h] for r in rr]);y=np.asarray([r[t] for r in rr]);idx=np.asarray([sessions.index(r['session']) for r in rr],int)
   check('known/unknown '+name+h+t,metric['known_N']==len(rr) and metric['unknown_N']==len(ids)-len(rr) and metric['mask_hash']==mask(r['entry_id'] for r in rr))
   if t=='realized_return':
    rho=float(spearmanr(s,y).statistic) if len(rr)>1 and len(set(s))>1 and len(set(y))>1 else None;check('Spearman '+name+h,close(rho,metric['Spearman']));continue
   a,bs=independent_auc(s,y,idx,M);ap=float(independent_ap(s,y)[0]) if len(rr) and len(set(y))==2 else None;check('AUC/AP '+name+h+t,close(a,metric['AUC']) and close(ap,metric['AP']))
   if a is not None:
    key=name+'|'+h+'|'+t;values[key]=bs;apv=independent_ap(s,y,M[:,idx]);apvalues[key]=apv;check('AP CI '+key,np.allclose(interval(apv),metric['AP_bootstrap']['CI95'],rtol=0,atol=1e-12))
    check('AUC session-pair CI '+key,np.allclose(interval(bs),metric['AUC_bootstrap']['CI95'],rtol=0,atol=1e-12),{'correct_CI':interval(bs),'stored_CI':metric['AUC_bootstrap']['CI95']})
  ct=collections.Counter((dd[k]['bucket'] or 'UNKNOWN')+'|'+('UNKNOWN' if dd[k]['realized_return'] is None else 'NEGATIVE' if dd[k]['realized_return']<0 else 'ZERO' if dd[k]['realized_return']==0 else 'POSITIVE') for k in ids);check('Loser Potential orthogonal '+name,dict(ct)==matrix[name]['cross_table'])
 flags=get(E/'FLAGGED_LOSER_WINNER_TRADEOFF.json')['rows']
 for f in flags:
  h=f['risk_direction'][1:];ss=sorted([dd[k] for k in coh['C2']],key=lambda r:(r['s'][h],r['time'],r['symbol'],r['entry_id']))[:math.ceil(f['fraction']*150)]
  neg=sum((r['pnl'] for r in ss if r['pnl']<0),Fraction(0));pos=sum((r['pnl'] for r in ss if r['pnl']>0),Fraction(0));check('FLAG budget/hash '+h+str(f['fraction']),f['N']==f['K']==len(ss) and f['mask_hash']==mask(r['entry_id'] for r in ss));check('FLAG money '+h+str(f['fraction']),Fraction(f['gross_negative_PnL_exact'])==neg and Fraction(f['positive_PnL_exact'])==pos)
  for t in ['Weak','Medium','U5','U10','positive','Loser']:check('FLAG '+h+t+str(f['fraction']),f[t]['N']==sum(r[t]==1 for r in ss))
 signed=get(E/'MRET_SIGNED_CONTROLS.json')['cohorts'];signedvalues={}
 for name,ids,target in [('C1',coh['C1'],'MRET_label'),('C2',coh['C2'],'positive'),('C3',coh['C3'],'positive')]:
  for tag,z in signed[name]['scores'].items():
   h=tag.lstrip('-');direction=-1 if tag.startswith('-') else 1;rr=[dd[k] for k in ids if dd[k][target] is not None];s=[direction*r['s'][h] for r in rr];y=[r[target] for r in rr];ix=np.asarray([sessions.index(r['session']) for r in rr]);a,bs=independent_auc(s,y,ix,M);check('signed AUC '+name+tag,close(a,z['AUC']));signedvalues[name+'|'+tag+'|AUC']=bs;check('signed session-pair CI '+name+tag,np.allclose(interval(bs),z['AUC_bootstrap']['CI95'],rtol=0,atol=1e-12),{'correct_CI':interval(bs),'stored_CI':z['AUC_bootstrap']['CI95']})
   r2=[dd[k] for k in ids if dd[k]['nativebucket'] is not None and dd[k]['realized_return'] is not None];credits=[]
   for i,r in enumerate(r2):
    for j in range(i):
     q=r2[j]
     if (r['block'],r['nativebucket'])==(q['block'],q['nativebucket']) and r['realized_return']!=q['realized_return']:credits.append(.5+.5*np.sign(direction*(r['s'][h]-q['s'][h]))*np.sign(r['realized_return']-q['realized_return']))
   val=sum(credits)/len(credits) if credits else None;zcon=z['native_bucket_concordance'];check('native concordance '+name+tag,close(val,zcon['concordance']) and len(credits)==zcon['valid_pairs'])
  for tag,z in signed[name]['all_control_deltas'].items():
   bs=signedvalues[name+'|MRET|AUC']-signedvalues[name+'|'+tag+'|AUC'];check('signed paired delta CI '+name+tag,np.allclose(interval(bs),z['paired_bootstrap']['CI95'],rtol=0,atol=1e-12),{'correct_CI':interval(bs),'stored_CI':z['paired_bootstrap']['CI95']})
 # Independently reconstruct canonical pair signs/Pareto/order, not counted as independent samples.
 rank=get(E/'RANK_CONFLICT_SUMMARY.json')['cohorts'];order=get(E/'SCORE_ORDER_AUDIT.json')['raw_vs_r']
 for name,ids in [('C0',coh['C0']),('C2',coh['C2']),('C3',coh['C3'])]:
  rr=[dd[k] for k in sorted(ids)];a,b=np.triu_indices(len(rr),1);s=np.asarray([[r['s'][h] for h in H] for r in rr]);ranks=np.asarray([[r['rank'][h] for h in H] for r in rr]);sig=np.sign(s[a]-s[b]);rs=np.sign(ranks[a]-ranks[b]);bl=np.asarray([r['block'] for r in rr]);z=rank[name];check('pair_N '+name,z['pair_N']==len(a));check('Pareto '+name,z['pareto'].get('INCOMPARABLE',0)==int((~((sig>=0).all(axis=1)|(sig<=0).all(axis=1))).sum()) and z['pareto'].get('ALL_TIE',0)==int((sig==0).all(axis=1).sum()))
  for j,h in enumerate(H[1:],1):
   c=z['pP_vs_auxiliary'][h];check('pair conflicts '+name+h,c.get('AGREE',0)==int(((sig[:,0]*sig[:,j])>0).sum()) and c.get('CONFLICT',0)==int(((sig[:,0]*sig[:,j])<0).sum()) and c.get('TIE',0)==int(((sig[:,0]*sig[:,j])==0).sum()))
  for j,h in enumerate(H):
   c=order[name]['changes'];check('r reversals '+name+h,c.get(h+'_cross_block_reversal',0)==int(((sig[:,j]*rs[:,j]<0)&(bl[a]!=bl[b])).sum()) and c.get(h+'_tie_increase',0)==int(((sig[:,j]!=0)&(rs[:,j]==0)).sum()))
 channel=get(E/'CHANNEL_CENSUS.json');cnt=collections.Counter();pending=0
 for batch in lines(ROOT/'r1_work/runs/OFF_PRIMARY/NATIVE_PROPOSALS.jsonl.gz'):
  ass={r['entry_id']:r for r in batch['assigned']};prior=0;rp=[r for r in batch['candidates'] if r['entry_id'] in set(coh['C3'])]
  for r in batch['candidates']:
   k=r['entry_id'];reason=native[k]['reason'];q=ass.get(k,{}).get('quantity',0);n=batch['existing_open_N']
   if len(rp)>1 and k in set(coh['C3']):cnt['CH1_PRE_BUY_SAME_BATCH']+=1
   if q>=100:cnt['CH2_PRE_BUY_DEFENSE']+=1;check('planned slot '+k,native[k]['funded_slot']==n+prior+1)
   if reason=='SLOT_RESERVE_REJECT' and n+prior<3:cnt['CH3_VACANT_SLOT_RESERVE']+=1
   if reason=='MAX_POSITION_CAP':
    if n==3:cnt['CH4_FULL_MAX3']+=1
    else:pending+=1
   if reason=='CASH_OR_LOT_CONSTRAINED':cnt['CH5_CASH_OR_LOT']+=1
   if q>=100:prior+=1
 cnt['CH6_RANK_REJECT_OTHER']=len(dd)-len(coh['C3'])
 for tag,n in cnt.items():check('channel '+tag,channel['channels'][tag]['population_N']==n)
 check('MAX3 pending',channel['pending_same_batch_MAX3_N']==pending)
 for u,total,funded,res,maxn,cash in [('U5',113,50,30,28,5),('U10',47,26,10,9,2)]:
  counts=collections.Counter(native[k]['reason'] for k in coh['C3'] if dd[k][u]);check('winner reason '+u,counts=={'FUNDED':funded,'SLOT_RESERVE_REJECT':res,'MAX_POSITION_CAP':maxn,'CASH_OR_LOT_CONSTRAINED':cash} and sum(counts.values())==total)
 modules=[n.module for n in ast.walk(ast.parse(pathlib.Path(__file__).read_text())) if isinstance(n,ast.ImportFrom)];check('no primary imports',not any(m in ['adapter','metrics','diagnostics','feasibility'] for m in modules))
 np.savez_compressed(P/'INDEPENDENT_AUC_BOOTSTRAP_VALUES.npz',**values);np.savez_compressed(P/'INDEPENDENT_SIGNED_AUC_VALUES.npz',**signedvalues)
 emit('INDEPENDENT_INITIAL_AUDIT.json',{'status':'FAIL' if fail else 'PASS','check_N':len(checks),'mismatch_N':len(fail),'failures':fail,'code_sha256':hashfile(__file__),'numeric_tolerance':1e-12,'identity_fraction_money_tolerance':0,'primary_imports':0,'new_fit_inference_replay':0,'independentDiagnosticVerification':1,'independence_scope':'separate implementation, shared source and NumPy/SciPy, same researcher, not blind external'})
 print(json.dumps({'check_N':len(checks),'mismatch_N':len(fail),'first_failures':fail[:2]}))
if __name__=='__main__':full()
