from pathlib import Path
import csv,json,hashlib,sys,numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent;D=R/'CHARTS';D.mkdir(exist_ok=True)
plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':120})
def read(n):return list(csv.DictReader((R/n).open()))
def val(x):return float(x) if x not in ('','None',None) else np.nan
def export(fig,n):
 fig.tight_layout();fig.savefig(D/(n+'.png'),dpi=150);fig.savefig(D/(n+'.svg'));plt.close(fig)
def fold_chart(tasks,models,byfold):
 fig,axes=plt.subplots(1,2,figsize=(12,5))
 for ax,task in zip(axes,tasks):
  for model in models:
   rows=[next(r for r in byfold if r['task']==task and r['control']=='REAL' and r['model']==model and r['fold']==str(f)) for f in [1,2,3]]
   ax.plot([1,2,3],[val(r['macro_F1']) if int(r['row_N']) else np.nan for r in rows],marker='o',label=model)
  ax.set_xticks([1,2,3],['1','2','3\nNO EVALUATION']);ax.set_xlim(.85,3.15);ax.axvspan(2.8,3.15,color='grey',alpha=.12);ax.set_xlabel('Chronological fold (empty is not a zero score)');ax.set_ylabel('Macro F1');ax.set_title(task);ax.legend()
 export(fig,'07_fold_stability')
def main():
 states=read('PER_STATE_PRECISION_RECALL_F1.csv');models=['B0','B1','B2','B3'];classes=json.loads((R/'TARGET_SCHEMA_V2.json').read_text())['class_order'];tasks=['NEXT_DISTINCT_PRIMARY','NEXT_OBSERVED_PRIMARY'];metrics=read('MODEL_METRICS_AGGREGATE.csv');byfold=read('MODEL_METRICS_BY_FOLD.csv')
 for measure in ['Precision','Recall']:
  fig,axes=plt.subplots(2,1,figsize=(13,8))
  for ax,task in zip(axes,tasks):
   for j,model in enumerate(models):
    data=[next(r for r in states if r['task']==task and r['control']=='REAL' and r['model']==model and r['State']==c) for c in classes];y=[val(r[measure])*100 for r in data];x=np.arange(9)+(j-1.5)*.2;ax.bar(x,y,width=.19,label=model)
    for xx,yy in zip(x,y):
     if not np.isfinite(yy):ax.text(xx,2,'NA',rotation=90,fontsize=6,ha='center')
   ax.set_xticks(range(9),classes,rotation=20,ha='right');ax.set_ylim(0,105);ax.set_ylabel(measure+' (%)');ax.set_title(task);ax.legend(ncol=4);ax.grid(axis='y',alpha=.15)
  export(fig,'01_precision_9state' if measure=='Precision' else '02_recall_9state')
 cm=read('CONFUSION_MATRIX_9STATE.csv');fig,axes=plt.subplots(2,4,figsize=(19,10))
 for row,task in enumerate(tasks):
  for j,model in enumerate(models):
   ax=axes[row,j];matrix=np.array([[int(next(r['N'] for r in cm if r['task']==task and r['control']=='REAL' and r['model']==model and r['actual_State']==a and r['predicted_State']==b)) for b in classes] for a in classes]);ax.imshow(matrix,cmap='Blues');ax.set_xticks(range(9),classes,rotation=90,fontsize=7);ax.set_yticks(range(9),classes,fontsize=7);ax.set_title(task+'\n'+model+' counts')
   for i in range(9):
    for k in range(9):ax.text(k,i,matrix[i,k],ha='center',va='center',fontsize=6,color='white' if matrix[i,k]>matrix.max()*.6 else 'black')
   ax.set_xlabel('Predicted');ax.set_ylabel('Actual')
 export(fig,'03_confusion_all_models')
 for name,fields in [('04_macro_f1',['macro_F1']),('05_calibration',['date_equal_log_loss','date_equal_Brier'])]:
  fig,axes=plt.subplots(1,len(fields),figsize=(7*len(fields),5));axes=np.atleast_1d(axes)
  for ax,field in zip(axes,fields):
   for i,task in enumerate(tasks):
    y=[val(next(r[field] for r in metrics if r['task']==task and r['control']=='REAL' and r['model']==m)) for m in models];ax.bar(np.arange(4)+(i-.5)*.35,y,width=.34,label=task)
   ax.set_xticks(range(4),models);ax.set_ylabel(field);ax.legend(fontsize=7);ax.grid(axis='y',alpha=.15)
  export(fig,name)
 fam=read('MOTION_FAMILY_METRICS.csv');fig,axes=plt.subplots(2,1,figsize=(11,8));fs=['UP_MOVE','DOWN_MOVE','NON_DIRECTIONAL_OR_STOP']
 for ax,task in zip(axes,tasks):
  for j,model in enumerate(models):ax.bar(np.arange(3)+(j-1.5)*.18,[100*val(next(r['Precision'] for r in fam if r['task']==task and r['control']=='REAL' and r['model']==model and r['family']==f)) for f in fs],width=.17,label=model)
  ax.set_xticks(range(3),fs);ax.set_title(task);ax.set_ylabel('Precision (%)');ax.set_ylim(0,105);ax.legend(ncol=4)
 export(fig,'06_motion_family_precision')
 fold_chart(tasks,models,byfold)
 fig,axes=plt.subplots(2,1,figsize=(12,8))
 for ax,task in zip(axes,tasks):
  data=[next(r for r in states if r['task']==task and r['control']=='REAL' and r['model']=='B3' and r['State']==c) for c in classes];ax.bar(np.arange(9)-.2,[int(r['Predicted_N']) for r in data],width=.38,label='B3 Predicted');ax.bar(np.arange(9)+.2,[int(r['Actual_N']) for r in data],width=.38,label='Actual');ax.axhline(50,ls='--',color='grey',label='Support floor 50');ax.set_xticks(range(9),classes,rotation=20,ha='right');ax.set_title(task);ax.set_ylabel('OOF endpoint count (not IID)');ax.legend()
 export(fig,'08_state_support')
 for name,control in [('09_true_null_vs_real','TRUE_NULL'),('10_shift60_stress','SHIFT60')]:
  data=read('NEGATIVE_CONTROL_V2.csv');fig,axes=plt.subplots(1,2,figsize=(12,5))
  for ax,task in zip(axes,tasks):
   rr=[next(r for r in data if r['task']==task and r['control']==control and r['model']==m) for m in models];ax.bar(np.arange(4)-.18,[val(r['REAL_log_loss']) for r in rr],width=.35,label='REAL matched');ax.bar(np.arange(4)+.18,[val(r['control_log_loss']) for r in rr],width=.35,label=control);ax.set_xticks(range(4),models);ax.set_title(task+'\n'+' / '.join('N='+r['matched_row_N'] for r in rr));ax.set_ylabel('Matched log loss (lower better)');ax.legend(fontsize=8)
  export(fig,name)
 price=read('PRICE_SECONDARY_V2.csv');fig,axes=plt.subplots(1,3,figsize=(15,5))
 for ax,h in zip(axes,[5,15,30]):
  for j,version in enumerate(['V1_RETAINED','V2']):
   values=[val(next((r['date_equal_MSE'] for r in price if r['version']==version and r['horizon']==str(h) and r['model']==m),''))/1e6 for m in models];ax.bar(np.arange(4)+(j-.5)*.35,values,width=.34,label=version)
  ax.set_xticks(range(4),models);ax.set_ylabel('Date-equal MSE / 1e6 (JPY/U)^2');ax.set_title('Price secondary H'+str(h));ax.legend()
 export(fig,'11_price_secondary')
 files=[{'path':str(p.relative_to(R)),'bytes':p.stat().st_size,'SHA256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(D.iterdir()) if p.is_file()]
 (R/'CHART_MANIFEST.json').write_text(json.dumps({'charts':11,'files':files,'source':'Immutable CSV metrics only','new_model_fits':0},indent=2)+'\n');print(json.dumps({'charts':11,'files':len(files)}))
if __name__=='__main__':
 if sys.argv[1:]==['--fold-only']:
  fold_chart(['NEXT_DISTINCT_PRIMARY','NEXT_OBSERVED_PRIMARY'],['B0','B1','B2','B3'],read('MODEL_METRICS_BY_FOLD.csv'))
  files=[{'path':str(p.relative_to(R)),'bytes':p.stat().st_size,'SHA256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(D.iterdir()) if p.is_file()]
  (R/'CHART_MANIFEST.json').write_text(json.dumps({'charts':11,'files':files,'source':'Immutable CSV metrics only; empty fold masked from plotted scores','new_model_fits':0,'focused_renderer_repair_N':1},indent=2)+'\n');print(json.dumps({'focused_redraw':1,'metric_changes':0}))
 else:main()
