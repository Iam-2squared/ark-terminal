"""Unchanged R1/R2 base maths, only rolling inner calibration design differs."""
from pathlib import Path
from collections import Counter,defaultdict
import json,hashlib,os,math
import numpy as np
R=Path(__file__).resolve().parent
CLASSES=['UP_CONTINUE','DOWN_REVERSAL','RANGE_OR_STOP','NO_DECISION_WITHIN30']
ALPHAS=[.01,.1,1.];TEMPS=[.5,.75,1.,1.25,1.5,2.]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,obj):
 p=R/n;p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n');os.replace(tmp,p)
def charge(lane,**kw):
 p=R/'MODEL_EXECUTION_LEDGER_V5.jsonl';rows=list(map(json.loads,p.open())) if p.exists() else [];n=len(rows)+1
 cap=json.loads((R/'BUDGET_START_V5.json').read_text())['finite_caps'];assert n<=cap['total_fits'] and sum(r['lane']==lane for r in rows)<cap[lane+'_fits'],'FIT_CAP_BREACH'
 with p.open('a') as f:f.write(json.dumps({'fit_N':n,'lane':lane,'charged_before_fit':True,**kw})+'\n');f.flush();os.fsync(f.fileno())
 return n
def weights(rows):
 g=Counter((r['date'],r['security_id'],r['session_id']) for r in rows);ds=Counter(x[0] for x in g)
 w=np.array([1/(len(ds)*ds[r['date']]*g[(r['date'],r['security_id'],r['session_id'])]) for r in rows]);return w/w.mean()
def prob(z):
 p=np.maximum(z,1e-12);return p/p.sum(1,keepdims=True)
def temp(p,T):
 z=np.log(p)/T;z-=z.max(1,keepdims=True);q=np.exp(z);return q/q.sum(1,keepdims=True)
def date_ll(p,y,rows):
 g=defaultdict(list)
 for i,r in enumerate(rows):g[r['date']].append(-math.log(max(float(p[i,y[i]]),1e-300)))
 return sum(sum(v)/len(v) for v in g.values())/len(g)
def transform(art,rows):
 e=art['encoder'];cols=[np.ones(len(rows))]
 for n in e['numeric']:
  mean,sd=e['stats'][n];a=np.array([np.nan if r['features'][n] is None else r['features'][n] for r in rows]);bad=~np.isfinite(a);cols.extend([np.where(bad,0,(a-mean)/sd),bad.astype(float)])
 for n in e['categorical']:
  for v in e['vocab'][n]:cols.append(np.array([r['features'][n]==v for r in rows],float))
 return np.column_stack(cols)
def build(rows,y,model,schema,alpha,lane,tag):
 w=weights(rows);Y=np.eye(4)[y]
 if model=='R1':
  charged=charge(lane,model=model,alpha=None,rows=len(rows),**tag);prior=np.average(Y,axis=0,weights=w);lookup={}
  for v in sorted({r['features']['formal_primary'] for r in rows}):
   ix=np.array([r['features']['formal_primary']==v for r in rows]);lookup[v]=((Y[ix]*w[ix,None]).sum(0)+10*prior)/(w[ix].sum()+10)
  return {'model':model,'alpha':None,'encoder':None,'prior':prior.tolist(),'lookup':{k:v.tolist() for k,v in lookup.items()},'coefficients':None,'charged_fit_ordinal':charged}
 assert model=='R2','V5_PRIMARY_SCOPE_ONLY_R1_R2'
 e={'numeric':schema['numeric_state'],'categorical':schema['categorical_state'],'stats':{},'vocab':{}}
 for n in e['numeric']:
  a=np.array([np.nan if r['features'][n] is None else r['features'][n] for r in rows]);ok=np.isfinite(a);mean=float(np.average(a[ok],weights=w[ok])) if ok.any() else 0.;var=float(np.average((a[ok]-mean)**2,weights=w[ok])) if ok.any() else 0.;e['stats'][n]=[mean,math.sqrt(var) if var>0 else 1.]
 for n in e['categorical']:e['vocab'][n]=sorted({r['features'][n] for r in rows})
 art={'model':model,'alpha':alpha,'encoder':e,'prior':None,'lookup':None};z=transform(art,rows);charged=charge(lane,model=model,alpha=alpha,rows=len(rows),columns=z.shape[1]-1,**tag)
 A=(z.T*w)@z/w.sum()+np.diag([0.]+[alpha]*(z.shape[1]-1));B=(z.T*w)@Y/w.sum();art['coefficients']=np.linalg.solve(A,B).tolist();art['charged_fit_ordinal']=charged;return art
def predict(a,rows):
 if a['encoder'] is None:return prob(np.array([a['lookup'].get(r['features']['formal_primary'],a['prior']) for r in rows]))
 return prob(transform(a,rows)@np.asarray(a['coefficients']))
def tie_select(grid,value_key,prefer):
 best=min(x[value_key] for x in grid);ties=[x for x in grid if x[value_key]<=best+1e-12];return min(ties,key=prefer)
def inner_plan(dates):
 dates=sorted(dates);remaining=dates[5:];q,rem=divmod(len(remaining),4);blocks=[];cursor=0
 for i in range(4):size=q+int(i<rem);blocks.append(remaining[cursor:cursor+size]);cursor+=size
 return [{'inner_fold':i+1,'validation_dates':block,'train_dates':[d for d in dates if block and d<block[0]],'validation_start':block[0]+'T00:00:00+09:00' if block else None} for i,block in enumerate(blocks)]
def fit(train,test,targets,model,schema,outer_train_dates,lane,fold,control):
 plan=inner_plan(outer_train_dates);alpha_grid=[None] if model=='R1' else ALPHAS;predictions={a:[] for a in alpha_grid};inners=[];tag={'outer_fold':fold,'control':control};path=f'{lane.upper()}_FITTED/{control}_{model}_F{fold}.json';assert not (R/path).exists(),'SUCCESSFUL_FIT_ALREADY_FIXED'
 for block in plan:
  itr=[r for r in train if r['date'] in block['train_dates'] and targets[r['row_key']]['label_end']<block['validation_start']];ival=[r for r in train if r['date'] in block['validation_dates']]
  block.update(train_N=len(itr),validation_N=len(ival),status='EVALUABLE' if itr and ival else 'EMPTY_TRAIN_OR_VALIDATION')
  if not itr or not ival:continue
  y=np.array([CLASSES.index(targets[r['row_key']]['target']) for r in itr]);iy=np.array([CLASSES.index(targets[r['row_key']]['target']) for r in ival])
  for alpha in alpha_grid:
   a=build(itr,y,model,schema,alpha,lane,{**tag,'phase':'inner','inner_fold':block['inner_fold']});p=predict(a,ival)
   saved={**a,'train_keys':[r['row_key'] for r in itr],'validation_keys':[r['row_key'] for r in ival],'validation_actual':iy.tolist(),'validation_probabilities':p.tolist(),'inner_fold':block['inner_fold']}
   inners.append(saved)
   predictions[alpha].extend({'row_key':r['row_key'],'date':r['date'],'inner_fold':block['inner_fold'],'actual':int(iy[i]),'probabilities':p[i].tolist()} for i,r in enumerate(ival))
 alpha_receipt=[]
 for alpha in alpha_grid:
  rs=predictions[alpha]
  if rs:alpha_receipt.append({'alpha':alpha,'date_equal_LL':date_ll(np.array([r['probabilities'] for r in rs]),np.array([r['actual'] for r in rs]),rs),'OOF_N':len(rs),'OOF_dates':len({r['date'] for r in rs})})
 selected=tie_select(alpha_receipt,'date_equal_LL',lambda x:-(x['alpha'] or 0))['alpha'] if alpha_receipt else (None if model=='R1' else .1)
 rs=predictions.get(selected,[]);en=len({r['inner_fold'] for r in rs});dates=len({r['date'] for r in rs});fallback=[]
 if en<2:fallback.append('INNER_EVALUABLE_FOLDS_LT2')
 if dates<5:fallback.append('INNER_OOF_DATES_LT5')
 if len(rs)<20:fallback.append('INNER_OOF_ROWS_LT20')
 T=1.;tg=[]
 if rs:
  ip=np.array([r['probabilities'] for r in rs]);iy=np.array([r['actual'] for r in rs])
  tg=[{'temperature':t,'date_equal_LL':date_ll(temp(ip,t),iy,rs)} for t in TEMPS]
  if not fallback:T=tie_select(tg,'date_equal_LL',lambda x:(abs(x['temperature']-1),-x['temperature']))['temperature']
 y=np.array([CLASSES.index(targets[r['row_key']]['target']) for r in train]);art=build(train,y,model,schema,selected,lane,{**tag,'phase':'final'});p=predict(art,test)
 art.update(classes=CLASSES,temperature=T,alpha_receipt=alpha_receipt,temperature_receipt=tg,inner_plan=plan,inner_artifacts=inners,selected_alpha_inner_OOF=rs,fallback_reason=fallback,alpha_fallback_reason='NO_INNER_OOF' if not alpha_receipt else None,train_keys=[r['row_key'] for r in train],test_keys=[r['row_key'] for r in test],outer_train_dates=outer_train_dates,train_feature_SHA256=hashlib.sha256(json.dumps([[r['row_key'],r['features']] for r in train],sort_keys=True,separators=(',',':')).encode()).hexdigest(),train_target_SHA256=hashlib.sha256(np.eye(4)[y].astype('<f8').tobytes()).hexdigest())
 save(path,art);return p,temp(p,T),path,art
