"""Finite FIRST ENTRY research utilities. No network/order/EXIT imports."""
from pathlib import Path
import collections,datetime,gzip,hashlib,json,math
from zoneinfo import ZoneInfo
import numpy as np
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
SCRATCH=REPO.parent
INPUT=SCRATCH/'persistent_sources'
OLD=REPO/'research/state9-safe-upside-hybrid-entry-20261003'
BASE_HEAD='bd9c34a67650467c68feaa631779f4095fac77ac'
SAFETY={k:False for k in ('executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','productionReady')}
HEADS=('UPSIDE','QUALITY','ADVERSE')
POLICIES={'Q70':.70,'Q80':.80,'Q90':.90,'Q95':.95}
def now():return datetime.datetime.now(ZoneInfo('Asia/Tokyo')).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):
 p=Path(p);b=p.read_bytes()
 return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)
def write(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 b=(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
 p.write_bytes(gzip.compress(b,mtime=0) if p.suffix=='.gz' else b)
def lines(p):
 with gzip.open(p,'rt',encoding='utf8') as f:
  for l in f:yield json.loads(l)
def write_lines(p,records):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('wb') as f,gzip.GzipFile(fileobj=f,mode='wb',mtime=0) as gz:
  for r in records:gz.write((json.dumps(r,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode())
def minute(s):return int(s[11:13])*60+int(s[14:16])
def stamp(day,t):return day+'T%02d:%02d:00+09:00'%divmod(t,60)
def regular_starts(day):return list(range(540,690))+list(range(750,900 if day<'2024-11-05' else 925))
def close_minute(day):return 900 if day<'2024-11-05' else 930
def source_starts(day):return regular_starts(day)+[690,close_minute(day)]
def active_elapsed(day,start,end):
 return sum(max(0,min(end,b)-max(start,a)) for a,b in ((540,690),(750,900 if day<'2024-11-05' else 925)))
def valid_bar(x):
 return len(x)==7 and all(math.isfinite(float(v)) for v in x) and x[3]>0 and x[3]<=min(x[1],x[4])<=max(x[1],x[4])<=x[2] and x[5]>=0 and x[6]>=0
def clean_array(rows):
 a=np.asarray(rows,dtype=np.float64).reshape(-1,7)
 assert len(a)==len(set(a[:,0])),'DUPLICATE_RAW_MINUTE'
 assert len(a)<2 or np.all(np.diff(a[:,0])>0),'UNSORTED_RAW_MINUTE'
 return a[np.asarray([valid_bar(x) for x in a],dtype=bool)]
def summarize(values):
 x=np.asarray([v for v in values if v is not None and np.isfinite(v)],float)
 return {'N':len(x),'median':float(np.median(x)) if len(x) else None,'mean':float(np.mean(x)) if len(x) else None,'p25':float(np.quantile(x,.25)) if len(x) else None,'p75':float(np.quantile(x,.75)) if len(x) else None}
def bucket(v):
 if v is None:return 'missing'
 return '<1%' if v<1 else '1–<2%' if v<2 else '2–<3%' if v<3 else '3–<4%' if v<4 else '4–<5%' if v<5 else '>=5%'
def input_manifest():
 return {p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(INPUT.iterdir()) if p.is_file()}
def load_npz(p):
 # NpzFile is lazy: materialize each immutable array once, never per decision.
 with np.load(p) as z:return {k:z[k] for k in z.files}
