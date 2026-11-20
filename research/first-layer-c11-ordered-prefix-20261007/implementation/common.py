"""WB01-derived, one-writer finite C11 accounting and immutable byte helpers."""
import datetime as dt, fcntl, gzip, hashlib, json, os, pathlib
ROOT=pathlib.Path(__file__).resolve().parent
PUB=ROOT/'public'; PRIV=ROOT/'private'
PUB.mkdir(exist_ok=True);PRIV.mkdir(exist_ok=True)
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def pin(path):
 b=pathlib.Path(path).read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}
def read(path):return json.loads(pathlib.Path(path).read_text())
def dump(path,x):
 p=pathlib.Path(path);p.parent.mkdir(parents=True,exist_ok=True);b=(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode();t=p.with_name(p.name+'.tmp');t.write_bytes(b);os.replace(t,p)
def clock():
 t=dt.datetime.now(dt.timezone.utc);return {'UTC':t.isoformat(),'JST':t.astimezone(dt.timezone(dt.timedelta(hours=9))).isoformat()}
def gzrows(path):
 with gzip.open(path,'rt') as f:return [json.loads(l) for l in f]
def seal_rows(path,rows):
 p=pathlib.Path(path);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('wb') as f,gzip.GzipFile(fileobj=f,mode='wb',mtime=0,filename='') as g:
  for r in rows:g.write(canonical(r)+b'\n')
 return {**pin(p),'row_N':len(rows)}
def event(kind,**kwargs):
 with (PRIV/'BUDGET_WRITER.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);b=read(PUB/'BUDGET_LEDGER.json');b['events'].append({'clock':clock(),'kind':kind,**kwargs})
  counter={'CYCLE_STARTED':'cycles_started','CYCLE_COMPLETED':'cycles_completed','MODEL_FIT_STARTED':'model_fit_attempts','MODEL_FIT_SUCCESS':'model_fit_success','PREPROCESS_FIT_STARTED':'preprocessing_fits','THRESHOLD_DECIDED':'threshold_decisions','CAL95_REFERENCE_DECIDED':'new_CAL95_reference_decisions','TECHNICAL_RETRY':'technical_retries'}.get(kind)
  if counter:b[counter]=b.get(counter,0)+1
  if kind=='MODEL_FIT_STARTED':b['fit_phase_attempts']['search']+=1
  if kind in ['THRESHOLD_DECIDED','CAL95_REFERENCE_DECIDED']:b['new_CAL_computations_total']=b.get('new_CAL_computations_total',0)+1
  assert b['model_fit_attempts']<=36 and b['preprocessing_fits']<=30 and b['threshold_decisions']<=150 and b.get('new_CAL95_reference_decisions',0)<=6 and b.get('new_CAL_computations_total',0)<=36 and b['cycles_started']<=11 and b['technical_retries']==0,'BUDGET_LIMIT'
  assert b['fit_phase_attempts']['report']==6 and b['legacy_threshold_decisions']==9,'INHERITED_REPORT_OR_V1_BUDGET_CHANGED'
  dump(PUB/'BUDGET_LEDGER.json',b);return b
def checkpoint(stage,next_action,**extra):
 b=read(PUB/'BUDGET_LEDGER.json');authority=read(PUB/'SOURCE_PIN.json')
 dump(PUB/('CHECKPOINT_'+stage+'.json'),{'stage':stage,'clock':clock(),'owner':'Iam-2squared / Codex C11 single writer','parent_HEADs':{k:v['final_HEAD'] for k,v in authority['recovery'].items()},'budget_counters':{k:v for k,v in b.items() if k!='events'},'budget_sha256':sha(PUB/'BUDGET_LEDGER.json'),'next':next_action,**extra})
