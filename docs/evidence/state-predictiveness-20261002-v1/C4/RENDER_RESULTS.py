"""Render fixed computed evidence, without changing rows, fits or interpretation."""
from pathlib import Path
from collections import Counter,defaultdict
import csv,hashlib,json,math,datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
R=Path(__file__).resolve().parent;O=R/'CHARTS';O.mkdir(exist_ok=True)
colors={'B0':'#687588','B1':'#3e8190','B2':'#3062a1','B3':'#a35947'}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':0.18,'grid.linestyle':'-','axes.axisbelow':True,'figure.facecolor':'white','axes.facecolor':'white','savefig.facecolor':'white'})
def read(name):return list(csv.DictReader((R/name).open()))
def f(row,k):return float(row[k])
def save(fig,name,title,note):
 fig.suptitle(title,fontsize=16,fontweight='bold',x=0.04,ha='left',y=0.99);fig.text(0.04,0.01,note,fontsize=9,color='#45566b');fig.tight_layout(rect=(0,0.045,1,0.95))
 for ext in ['png','svg']:fig.savefig(O/(name+'.'+ext),dpi=150,bbox_inches='tight')
 plt.close(fig)
def main():
 agg=read('METRICS_AGGREGATE.csv');real={(int(r['horizon']),r['model']):r for r in agg if r['control']=='REAL'};inc=read('INCREMENTAL_VALUE.csv');fold=read('METRICS_BY_FOLD.csv');models=['B0','B1','B2','B3'];hs=[5,15,30]
 fig,axs=plt.subplots(1,3,figsize=(13,4.8))
 for ax,h in zip(axs,hs):
  values=[f(real[(h,m)],'date_equal_MSE')/1e6 for m in models];ax.bar(models,values,color=[colors[m] for m in models],width=0.65)
  for i,y in enumerate(values):ax.text(i,y+max(values)*.02,f'{y:.2f}',ha='center',fontsize=10)
  ax.set_ylim(0,max(values)*1.18);ax.set_title(f'{h} scheduled minutes | OOF N={real[(h,"B0")]["row_N"]}');ax.set_ylabel('Date-equal MSE, million (JPY/U)^2')
 save(fig,'01_MODEL_HORIZON_PERFORMANCE','Full State and Path did not improve the primary loss','Literal target = raw Close difference / frozen log-scale U, not a percent return. Lower is better. OOF dates=5; evaluable folds=2.')
 fig,axs=plt.subplots(1,3,figsize=(14,5.1))
 for ax,(m,b) in zip(axs,[('B1','B0'),('B2','B1'),('B3','B2')]):
  rows=[next(r for r in inc if int(r['horizon'])==h and r['candidate']==m and r['comparator']==b) for h in hs];ys=[100*f(r,'relative_reduction') for r in rows];low=[100*f(r,'CI_low') for r in rows];high=[100*f(r,'CI_high') for r in rows]
  ax.errorbar(range(3),ys,yerr=np.array([[y-l for y,l in zip(ys,low)],[u-y for u,y in zip(high,ys)]]),fmt='o',color=colors[m],capsize=4,linewidth=1.5,markersize=7);ax.axhline(0,color='#586271',linewidth=1);ax.set_xticks(range(3),[str(h) for h in hs]);ax.set_xlabel('Scheduled-minute horizon');ax.set_title(f'{m} vs {b}');ax.set_ylabel('Date-equal MSE reduction (%)')
  for i,y in enumerate(ys):ax.annotate(f'{y:+.1f}%',(i,y),xytext=(7,5),textcoords='offset points',fontsize=9)
 save(fig,'02_INCREMENTAL_DELTA','No positive primary incremental value was demonstrated','Positive means lower MSE. Registered date-cluster bootstrap 99.1667% intervals; 1000 draws. Only five OOF dates: imprecise, not proof of no effect.')
 fig,axs=plt.subplots(1,3,figsize=(13,5.0))
 for ax,h in zip(axs,hs):
  ax.axhline(1,color='#687588',linestyle='--',label='B0 reference')
  for m in ['B1','B2','B3']:
   ys=[]
   for foldN in [1,2,3]:
    a=next((r for r in fold if r['control']=='REAL' and int(r['horizon'])==h and r['model']==m and int(r['fold'])==foldN),None);b=next((r for r in fold if r['control']=='REAL' and int(r['horizon'])==h and r['model']=='B0' and int(r['fold'])==foldN),None);ys.append(np.nan if a is None else f(a,'date_equal_MSE')/f(b,'date_equal_MSE'))
   ax.plot([1,2,3],ys,'o-',color=colors[m],label=m)
  ax.axvspan(1.7,2.3,color='#f0f1f4');ax.text(2,.98,'Fold 2: unavailable\n0 targets',transform=ax.get_xaxis_transform(),ha='center',va='top',fontsize=9);ax.set_xticks([1,2,3]);ax.set_xlim(.65,3.35);ax.set_title(f'{h}-minute horizon');ax.set_ylabel('Date-equal MSE / B0 MSE');ax.set_xlabel('Chronological outer fold')
 axs[-1].legend(loc='best',fontsize=9)
 save(fig,'03_FOLD_STABILITY','No candidate improvement replicated across the evaluable folds','NA is not zero or PASS. Fold 2 has no available price targets. Three fixed folds and their dates were not re-selected after results.')
 buckets=read('PREDICTION_BUCKETS.csv');fig,axs=plt.subplots(4,3,figsize=(14,12))
 for i,m in enumerate(models):
  for j,h in enumerate(hs):
   ax=axs[i,j];rows=sorted([r for r in buckets if r['model']==m and int(r['horizon'])==h],key=lambda r:int(r['bucket']));x=[int(r['bucket']) for r in rows]
   for field,label,col,style in [('predicted_mean','Predicted mean','#687588','--'),('realized_mean','Realized mean','#3062a1','-'),('realized_median','Realized median','#a35947',':')]:ax.plot(x,[f(r,field) for r in rows],marker='o',linestyle=style,color=col,label=label,markersize=3)
   ax.axhline(0,color='#a1a8b3',linewidth=.7);ax.set_title(f'{m} | {h} minutes');ax.set_xticks(range(1,6));ax.set_xlabel('Prediction-rank bucket');ax.set_ylabel('Literal target (JPY/U)')
 axs[0,0].legend(fontsize=8,loc='best')
 save(fig,'04_BUCKET_REALIZED_RETURN','Rank buckets are descriptive, not Entry thresholds','Five fixed rank buckets; equal-size bins, stable key breaks ties. Row-level means and medians. All four models and three primary horizons are shown.')
 coverage=read('FEATURE_COVERAGE.csv');fig,axs=plt.subplots(1,2,figsize=(15,13));family={'numeric_state':'#3062a1','categorical_state':'#3e8190','numeric_path':'#a35947','categorical_path':'#a484b4'}
 for ax,rows in zip(axs,[coverage[:32],coverage[32:]]):
  y=np.arange(len(rows));ax.barh(y,[100*f(r,'coverage_fraction') for r in rows],color=[family[r['family']] for r in rows],height=.72);ax.set_yticks(y,[r['feature'] for r in rows],fontsize=8);ax.invert_yaxis();ax.set_xlim(0,108);ax.set_xticks([0,25,50,75,100]);ax.set_xlabel('Present coverage (%)')
  for k,r in enumerate(rows):ax.text(100*f(r,'coverage_fraction')+1,k,str(r['present_N']),va='center',fontsize=7)
 fig.legend(handles=[Patch(facecolor=v,label=k.replace('_',' ')) for k,v in family.items()],loc='lower center',bbox_to_anchor=(.5,.033),ncol=4,frameon=False)
 save(fig,'05_STATE_PATH_FEATURE_COVERAGE','All allowlisted feature coverage is exposed','8050 scheduled endpoints. Missing remains missing. Formal null is counted as a present missing-observation category, not a tenth market State. S/A/B/C, Membership and velocity excluded.')
 manifest=json.loads((R/'RECEIVED_DEVELOPMENT/DATASET_MANIFEST.json').read_text());ds=sorted({p['date'] for p in manifest['pairs']});fig,axs=plt.subplots(3,1,figsize=(13,10));obs=[sum(p['observed_semantic_N'] for p in manifest['pairs'] if p['date']==d) for d in ds];null=[sum(p['formal_null_N'] for p in manifest['pairs'] if p['date']==d) for d in ds];x=np.arange(len(ds));axs[0].bar(x,obs,color='#3062a1',label='Observed semantics');axs[0].bar(x,null,bottom=obs,color='#ccd3dd',label='Formal null');axs[0].set_ylabel('Scheduled feature endpoints');axs[0].legend(ncol=2,fontsize=9)
 for j,h in enumerate(hs):
  rows=read(f'OOF/REAL_H{h}.csv');count=Counter(r['date'] for r in rows if r['model']=='B0');axs[1].bar(x+(j-1)*.25,[count[d] for d in ds],width=.25,label=f'{h} min')
 axs[1].set_ylabel('Unique price-target OOF rows');axs[1].legend(ncol=3,fontsize=9)
 samples=read('SAMPLE_CLUSTER_COUNTS.csv');chosen=[next(r for r in samples if r['scope']==f'REAL_H{h}_OOF_UNIQUE') for h in hs]
 for j,field in enumerate(['security_session_N','session_date_N','unique_run_N']):axs[2].bar(np.arange(3)+(j-1)*.25,[int(r[field]) for r in chosen],width=.25,label=field.replace('_',' '))
 for ax in axs[:2]:ax.set_xticks(x,ds,rotation=30,ha='right')
 axs[2].set_xticks(range(3),['5 min','15 min','30 min']);axs[2].set_ylabel('Distinct groups, not IID rows');axs[2].legend(ncol=3,fontsize=9)
 save(fig,'06_SAMPLE_CLUSTER_COUNTS','Large row counts reduce to only five evaluable price-target dates','Full input slice: 25 securities/sessions, 10 dates, 8050 endpoints. Date-cluster uncertainty. Overlapping horizon pairs and run concentration are saved separately; no IID row claim.')
 neg=read('NEGATIVE_CONTROL_RESULTS.csv');fig,axs=plt.subplots(1,3,figsize=(15,6))
 for ax,h in zip(axs,hs):
  rows=[r for r in neg if int(r['horizon'])==h];x=np.arange(len(rows));realvals=[100*f(r,'real_matched_relative_improvement') for r in rows];controls=[100*f(r,'control_relative_improvement') for r in rows];ax.bar(x-.17,realvals,width=.34,color='#3062a1',label='Real, matched rows');ax.bar(x+.17,controls,width=.34,color='#c28a49',label='Control');ax.axhline(0,color='#687588',linewidth=1);ax.set_xticks(x,[('Perm' if r['control']=='PERMUTATION' else 'Shift')+'\n'+r['model'] for r in rows],fontsize=9);ax.set_ylabel('Date-equal MSE reduction vs B0 (%)');ax.set_title(f'{h} minutes')
  for i,r in enumerate(rows):
   if r.get('comparably_good')=='True':ax.annotate('STOP',(i+.17,controls[i]),xytext=(0,8),textcoords='offset points',ha='center',fontsize=9,color='#9b3e2e',fontweight='bold')
 axs[-1].legend(loc='best',fontsize=9)
 save(fig,'07_NEGATIVE_CONTROL_COMPARISON','The precommitted SHIFT60 integrity condition fires in three cells','Controls use identical matched row keys and the unchanged model grid. SHIFT60: 2 OOF dates, 1 fold; suspicion is not proof of leakage. No threshold or selection repair.')
 sources=['METRICS_AGGREGATE.csv','METRICS_BY_FOLD.csv','INCREMENTAL_VALUE.csv','NEGATIVE_CONTROL_RESULTS.csv','PREDICTION_BUCKETS.csv','FEATURE_COVERAGE.csv','SAMPLE_CLUSTER_COUNTS.csv','TARGET_OVERLAP.csv']
 record={'created_at_jst':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),'unique_chart_N':7,'files_N':14,'semantic_or_result_changes':0,'data_source_hashes':{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in sources},'files':[{'path':str(p.relative_to(R)),'bytes':p.stat().st_size,'SHA256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(O.glob('*'))],'visual_QA':'See separate VISUAL_QA_RECEIPT.json after image inspection.','unit':'literal raw Close difference / frozen dimensionless log U; not percentage return','not_a_predictive_candidate':True}
 (R/'CHART_MANIFEST.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n');print(json.dumps({'unique_charts':7,'files':14,'total_bytes':sum(f['bytes'] for f in record['files'])}))
if __name__=='__main__':main()
