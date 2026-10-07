"""Post-seal fixed-cohort evaluation. No model fitting or cutoff modification."""
import csv,decimal,hashlib,json,pathlib,shutil
from fractions import Fraction
from common import ROOT,PUB,PRIV,canonical,clock,dump,read,pin,sha,gzrows,seal_rows,checkpoint,event

POINTS=['ALL_KEEP','CAL95','CAL_MINUS_KEEP_80','CAL_MINUS_KEEP_60','CAL_MINUS_KEEP_40','CAL_MINUS_KEEP_20','CAL_MINUS_KEEP_10']
BANDS=['PLUS_0_1','PLUS_1_2','PLUS_2_3','PLUS_3_4','PLUS_4_5','PLUS_5_PLUS']
CLASSES=['MINUS']+BANDS+['ZERO','UNKNOWN_SIGN','PLUS_RETURN_UNAVAILABLE']
PARENT=ROOT.parent/'recovery/saved_parent/nc09_c10'
MODELS=['C08','C10','C11'];SCOPES=['S1','S2','S1+S2']
def bucket(r):
 s=r['sign_status']
 if s in ['UNKNOWN','UNKNOWN_SIGN']:return 'UNKNOWN_SIGN'
 v=r['R_native_fraction_decimal']
 if v is None or not r['return_available']:return s+'_RETURN_UNAVAILABLE'
 p=Fraction(decimal.Decimal(v))*100
 assert (p>0 and s=='PLUS') or (p<0 and s=='MINUS') or (p==0 and s=='ZERO'),('SIGN_R_MISMATCH',r['entry_id'])
 if p<0:return 'MINUS'
 if p==0:return 'ZERO'
 return BANDS[min(int(p),5)]
def rate(a,n):return a/n if n else None
def stats(rr):
 n=len(rr);k=sum(r['decision']=='KEEP' for r in rr);return {'N':n,'KEEP':k,'DROP':n-k,'KEEP_rate':rate(k,n),'DROP_rate':rate(n-k,n)}
def csvsave(name,rows):
 assert rows
 with (PUB/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def run():
 assert not (PUB/'RESULTS.json').exists(),'NO_POST_RESULT_RERUN'
 for m in ['C11']:
  c=read(PRIV/m/'COMPLETE.json');assert c['status']=='ALL_STAGE_DECISIONS_SEALED_BEFORE_WINNER_JOIN' and c['DEV_union_seal']==pin(PRIV/m/'DEV_SCORES_DECISIONS.jsonl.gz')|{'row_N':322}
  assert read(PUB/(m+'_SEALED_READBACK.json'))['status']=='PASS'
 frozen_pins={str(p.relative_to(ROOT)):pin(p) for m in ['C11'] for p in (PRIV/m).rglob('*') if p.is_file()}
 locator=read(PARENT/'public/R_LOCATOR.json')
 for n in ['SPLITS_S1_S2.json','SIGNS_CAL_DEV.json']:shutil.copyfile(PARENT/'private'/n,PRIV/n)
 for n,key in [('CANONICAL_RETURN_ROWS_322.json','canonical_targeted_R_pin'),('RNEG_TARGETED_OUTCOMES_322.json','canonical_source_rows_pin')]:
  src=PARENT/'private'/n;assert pin(src)==locator[key];shutil.copyfile(src,PRIV/n)
 ret=read(PRIV/'CANONICAL_RETURN_ROWS_322.json');rmap={r['entry_id']:r for r in ret};orig={r['entry_id']:r for r in read(PRIV/'RNEG_TARGETED_OUTCOMES_322.json')};signs={r['entry_id']:r for r in read(PRIV/'SIGNS_CAL_DEV.json')}
 assert len(rmap)==len(ret)==len(orig)==322
 for i,r in rmap.items():
  s=signs[i]['sign_status'];assert s==r['sign_status']
  if r['return_available']:
   # WB01's canonical R_pct fields are percent; its named native token is fraction.
   assert r['R_unit']=='percent' and Fraction(decimal.Decimal(r['R_native_fraction_decimal']))==Fraction(decimal.Decimal(str(orig[i]['r_original'])))
   assert Fraction(int(r['R_pct_numerator']),int(r['R_pct_denominator']))==Fraction(decimal.Decimal(r['R_native_fraction_decimal']))*100
  bucket(r)
 ev=[]
 for x in gzrows(PARENT/'private/EVAL_ROWS.jsonl.gz'):
  if x['model'] in ['C08','C10']:
   ev.append({k:x[k] for k in ['model','block','point','entry_id','eta','decision','current_state_available','history_available','model_sha256']})
 for m in ['C11']:
  for r in gzrows(PRIV/m/'DEV_SCORES_DECISIONS.jsonl.gz'):
   for p,d in r['decisions'].items():ev.append({'model':m,'block':r['block'],'point':p,'entry_id':r['entry_id'],'eta':r['eta'],'decision':d,'current_state_available':r['current_state_available'],'history_available':r['history_available'],'model_sha256':r['model_sha256']})
 for r in ev:
  i=r['entry_id'];r.update(sign_status='UNKNOWN_SIGN' if rmap[i]['sign_status']=='UNKNOWN' else rmap[i]['sign_status'],bucket=bucket(rmap[i]),return_available=rmap[i]['return_available'],R_native_fraction_decimal=rmap[i]['R_native_fraction_decimal'],R_pct_numerator=rmap[i]['R_pct_numerator'],R_pct_denominator=rmap[i]['R_pct_denominator'],return_source_hash=rmap[i]['source_hash'])
 assert len(ev)==3*7*322 and len({(r['model'],r['point'],r['entry_id']) for r in ev})==len(ev)
 evaluation_seal=seal_rows(PRIV/'EVAL_ROWS.jsonl.gz',ev)
 results={};signrows=[];bandrows=[];curverows=[];composition=[];cumulative=[];quality=[]
 for m in MODELS:
  results[m]={}
  for p in POINTS:
   results[m][p]={}
   for scope in SCOPES:
    rr=[r for r in ev if r['model']==m and r['point']==p and (scope=='S1+S2' or r['block']==scope)];assert len(rr)=={'S1':164,'S2':158,'S1+S2':322}[scope]
    sig={s:stats([r for r in rr if r['sign_status']==t]) for s,t in [('ALL_PLUS','PLUS'),('ALL_MINUS','MINUS'),('ZERO','ZERO'),('UNKNOWN_SIGN','UNKNOWN_SIGN')]}
    bands={b:stats([r for r in rr if r['bucket']==b]) for b in BANDS+['PLUS_RETURN_UNAVAILABLE']};cum={}
    for k in [1,2,3,5]:cum[str(k)]=stats([r for r in rr if r['sign_status']=='PLUS' and r['return_available'] and Fraction(decimal.Decimal(r['R_native_fraction_decimal']))*100>=k])
    total=stats(rr);counts={b:stats([r for r in rr if r['bucket']==b]) for b in CLASSES};item={'signs':sig,'bands':bands,'cumulative':cum,'total':total,'drop_composition':{b:{'DROP':v['DROP'],'share_of_total_DROP':rate(v['DROP'],total['DROP']),'band_N':v['N'],'band_DROP_rate':v['DROP_rate']} for b,v in counts.items()}}
    assert sum(v['N'] for v in bands.values())==sig['ALL_PLUS']['N'] and sum(v['KEEP'] for v in bands.values())==sig['ALL_PLUS']['KEEP'] and sum(v['DROP'] for v in counts.values())==total['DROP']
    results[m][p][scope]=item;base={'model':m,'point':p,'scope':scope}
    for s,v in sig.items():signrows.append({**base,'sign':s,**v})
    for b,v in bands.items():bandrows.append({**base,'band':b,**v,'R_original_available':b!='PLUS_RETURN_UNAVAILABLE','small_sample':v['N']<10})
    for b,v in item['drop_composition'].items():composition.append({**base,'band':b,**v})
    for k,v in cum.items():cumulative.append({**base,'R_ge_percent':k,**v,'overlapping_not_additive':True})
    curverows.append({**base,**{s+'_'+k:v for s in ['ALL_PLUS','ALL_MINUS'] for k,v in sig[s].items()},**{b+'_KEEP':v['KEEP'] for b,v in bands.items() if b in BANDS},**{b+'_N':v['N'] for b,v in bands.items() if b in BANDS}})
    for key in ['current_state_available','history_available']:
     for val in [True,False]:
      subset=[r for r in rr if bool(r[key])==val];quality.append({**base,'quality':key,'value':val,**stats(subset),'PLUS_N':sum(r['sign_status']=='PLUS' for r in subset),'MINUS_N':sum(r['sign_status']=='MINUS' for r in subset)})
 pairs=[];ids=[];matrix={(r['model'],r['point'],r['entry_id']):r for r in ev}
 specifications=[(a,p,b,p) for a,b in [('C08','C10'),('C08','C11'),('C10','C11')] for p in POINTS]
 for am,ap,bm,bp in specifications:
  for scope in SCOPES:
   for band in CLASSES:
    rr=[r for r in ev if r['model']==bm and r['point']==bp and r['bucket']==band and (scope=='S1+S2' or r['block']==scope)];a={k:[] for k in ['KEEP_TO_DROP','DROP_TO_KEEP','STAY_KEEP','STAY_DROP']}
    for r in rr:
     old=matrix[(am,ap,r['entry_id'])]['decision'];new=r['decision'];key=('STAY_'+new) if old==new else old+'_TO_'+new;a[key].append(r['entry_id'])
    base={'reference_model':am,'reference_point':ap,'new_model':bm,'new_point':bp,'scope':scope,'band':band};pairs.append({**base,'N':len(rr),**{k:len(v) for k,v in a.items()},'NET_KEEP_CHANGE':len(a['DROP_TO_KEEP'])-len(a['KEEP_TO_DROP'])});ids.append({**base,**a})
 dump(PRIV/'PAIRED_CHANGE_IDS.json',ids)
 candidates=read(PARENT/'public/WINNER_BAND_PARETO.json')['candidates']
 for m in ['C11']:
  for p in POINTS:
   r=results[m][p]['S1+S2'];candidates.append({'candidate_id':m+'_'+p,'model':m,'point':p,'MINUS_KEEP':r['signs']['ALL_MINUS']['KEEP'],'ALL_PLUS_KEEP':r['signs']['ALL_PLUS']['KEEP'],'band_KEEP':{b:r['bands'][b]['KEEP'] for b in BANDS},'band_N':{b:r['bands'][b]['N'] for b in BANDS},'result':r,'exposure':'ADAPTIVE_DEVELOPMENT','Fresh_OOS':0,'R_unavailable':r['bands']['PLUS_RETURN_UNAVAILABLE']['N'],'auto_Champion':False})
 edges=[]
 for a in candidates:
  for b in candidates:
   if a['candidate_id']==b['candidate_id'] or a['band_N']!=b['band_N'] or a['R_unavailable'] or b['R_unavailable']:continue
   better=a['MINUS_KEEP']<=b['MINUS_KEEP'] and all(a['band_KEEP'][k]>=b['band_KEEP'][k] for k in BANDS)
   strict=a['MINUS_KEEP']<b['MINUS_KEEP'] or any(a['band_KEEP'][k]>b['band_KEEP'][k] for k in BANDS)
   if better and strict:edges.append({'dominator':a['candidate_id'],'dominated':b['candidate_id'],'definition':'MINUS KEEP<=; all6 exclusive Winner KEEP>=; at least1 strict'})
 for c in candidates:c['strictly_dominated_by']=[e['dominator'] for e in edges if e['dominated']==c['candidate_id']]
 pareto={'status':'TRADE_OFF_ARCHIVE_NOT_NEW_CHAMPION','candidates':candidates,'strict_dominance':edges,'nondominated_ids':[c['candidate_id'] for c in candidates if not c['strictly_dominated_by']],'all_fixed_points_retained':True,'unapproved_Winner_weights_or_Gates':0,'old_champion_unchanged':True,'exposure':'ADAPTIVE_DEVELOPMENT','Fresh_OOS':0}
 dump(PUB/'WINNER_BAND_PARETO.json',pareto);dump(PUB/'RESULTS.json',results)
 cumulative_edges=[]
 for a in candidates:
  for b in candidates:
   if a['candidate_id']==b['candidate_id']:continue
   av=[a['ALL_PLUS_KEEP']]+[a['result']['cumulative'][str(k)]['KEEP'] for k in [1,2,3,5]];bv=[b['ALL_PLUS_KEEP']]+[b['result']['cumulative'][str(k)]['KEEP'] for k in [1,2,3,5]]
   if a['MINUS_KEEP']<=b['MINUS_KEEP'] and all(x>=y for x,y in zip(av,bv)) and (a['MINUS_KEEP']<b['MINUS_KEEP'] or any(x>y for x,y in zip(av,bv))):cumulative_edges.append({'dominator':a['candidate_id'],'dominated':b['candidate_id']})
 dump(PUB/'CUMULATIVE_PARETO.json',{'precommitted_definition':'MINUS KEEP<=; ALL PLUS and cumulative >=1/2/3/5 KEEP>=; one strict, no weights','edges':cumulative_edges,'nondominated_ids':[c['candidate_id'] for c in candidates if not any(e['dominated']==c['candidate_id'] for e in cumulative_edges)],'all28_candidates_retained':True,'Champion':None})
 for name,rows in [('SIGN_KEEP_DROP.csv',signrows),('WINNER_BAND_KEEP_DROP.csv',bandrows),('OPERATING_POINT_COMPARISON.csv',curverows),('DROP_COMPOSITION.csv',composition),('CUMULATIVE_WINNER_KEEP_DROP.csv',cumulative),('PAIRED_CHANGE_COMPARISON.csv',pairs),('QUALITY_SUPPLEMENT.csv',quality)]:csvsave(name,rows)
 for rel,p in frozen_pins.items():assert pin(ROOT/rel)==p,('POST_EVALUATION_SEAL_CHANGED',rel)
 dump(PUB/'EVALUATION_JOIN_RECEIPT.json',{'clock':clock(),'status':'PASS','cohort_N':322,'class_counts':{s:sum(('UNKNOWN_SIGN' if r['sign_status']=='UNKNOWN' else r['sign_status'])==s for r in ret) for s in ['PLUS','MINUS','ZERO','UNKNOWN_SIGN']},'known_R_N':sum(r['return_available'] for r in ret),'PLUS_R_unavailable_N':sum(r['sign_status']=='PLUS' and not r['return_available'] for r in ret),'new_band_bounds':False,'freeze_changes':0,'report501_new':0,'evaluation_rows_seal':evaluation_seal,'immutable_model_score_threshold_pins':frozen_pins,'prediction_seals_precede_join':{m:read(PRIV/m/'COMPLETE.json')['clock'] for m in ['C11']},'CAL95_new_reference_N':2,'new_aggressive_threshold_N':10,'all_new_CAL_computations_N':12})
 dump(PRIV/'EXPOSURE_LEDGER.json',{'clock':clock(),'inherited_C09_C10_WB01_exposure_preserved':True,'new_exposure_events':[{'purpose':'C11 post-seal Winner join','Entry_IDs':sorted(rmap),'exact_R_known_N':316,'new_dates':0,'source':'frozen C09/C10 canonical R reused'},{'purpose':'teacher-blind ordered prefix feature QA only','Entry_N':1600,'known_Development_date_N':58,'new_RAW_scan':0,'new_dates':0,'REPORT501_new_model_score':0,'R_label_capability':False}],'all_sessions_status':'ADAPTIVE_DEVELOPMENT','Fresh':0,'OOS':0,'protected_opened':0,'provider_fetch':0})
 event('POST_SEAL_WINNER_EVALUATION_COMPLETED',models=['C08','C10','C11'],Entry_N=322,new_fit=0,new_threshold=0)
 checkpoint('EVALUATION_COMPLETE','Independent reconstruction without importing aggregation, then final GitHub save/readback; no C12.')
 print({'status':'POST_SEAL_EVALUATION_COMPLETE','rows':len(ev),'candidates':len(candidates),'strict_dominance_edges':len(edges),'nondominated':pareto['nondominated_ids']},flush=True)

if __name__=='__main__':run()
