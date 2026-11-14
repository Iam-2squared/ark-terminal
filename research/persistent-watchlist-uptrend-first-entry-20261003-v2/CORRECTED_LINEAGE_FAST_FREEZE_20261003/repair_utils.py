"""Repair-only artifact utilities. Frozen research contracts remain in parent."""
from pathlib import Path
import sys,hashlib,json,gzip,datetime,os
from zoneinfo import ZoneInfo
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
REPO=BASE.parents[1]
SCRATCH=REPO.parent
sys.path.insert(0,str(BASE))
SAFETY={k:False for k in ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','productionReady']}
HEADS=('UPSIDE','QUALITY','ADVERSE')
POLICIES={'Q70':.70,'Q80':.80,'Q90':.90,'Q95':.95}
START_HEAD='0e1526305d4f172e8e230cfc26210ad7a370e0f1'
DOCUMENT_ID='WORK_FIRST_ENTRY_V2_CORRECTED_LINEAGE_FAST_FREEZE_20261003'
def now():return datetime.datetime.now(ZoneInfo('Asia/Tokyo')).isoformat()
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def read(p):
 p=Path(p);b=p.read_bytes()
 return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)
def write(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n')
def rows(p):
 with gzip.open(p,'rt',encoding='utf8') as f:
  for line in f:yield json.loads(line)
def write_rows(p,records):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 temporary=p.with_name(p.name+'.pending');N=0
 with temporary.open('wb') as f:
  with gzip.GzipFile(fileobj=f,mode='wb',mtime=0,filename=p.name) as z:
   for r in records:
    z.write((json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode());N+=1
  f.flush();os.fsync(f.fileno())
 with gzip.open(temporary,'rt',encoding='utf8') as z:assert sum(1 for _ in z)==N
 os.replace(temporary,p)
def load_npz(p):
 import numpy as np
 with np.load(p) as z:return {k:z[k] for k in z.files}
