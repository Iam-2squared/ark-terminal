"""New EXIT research only. No historical EXIT, provider, order or Capital imports."""
from pathlib import Path
import datetime, gzip, hashlib, json, math
from zoneinfo import ZoneInfo
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SCRATCH = REPO.parent
ENTRY = REPO / 'research/persistent-watchlist-uptrend-first-entry-20261003-v2/CORRECTED_LINEAGE_FAST_FREEZE_20261003'
STATE = REPO / 'research/state9-safe-upside-hybrid-entry-20261003'
SOURCE = SCRATCH / 'persistent_sources/raw_paths_selected.json.gz'
ENTRY_HEAD = '4a2d6f35946b16820a13449a9288a6685a5c283c'
DOC = 'WORK_STATE_AWARE_EXIT_V1_FASTTRACK_20261003'
SAFETY = {k: False for k in ('executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','productionReady')}
PARAMS = dict(max_depth=3, learning_rate=.05, max_iter=100, max_leaf_nodes=31,
              min_samples_leaf=20, l2_regularization=0., early_stopping=False, random_state=570926)
def now(): return datetime.datetime.now(ZoneInfo('Asia/Tokyo')).isoformat()
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(2**20),b''): h.update(chunk)
    return h.hexdigest()
def read(p):
    p=Path(p); b=p.read_bytes()
    return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)
def write(p,d):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n')
def lines(p):
    with gzip.open(p,'rt',encoding='utf8') as f:
        for l in f: yield json.loads(l)
def write_lines(p,records):
    with Path(p).open('wb') as f,gzip.GzipFile(fileobj=f,mode='wb',mtime=0) as z:
        for r in records:z.write((json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode())
def regular(day): return list(range(540,690))+list(range(750,900 if day<'2024-11-05' else 925))
def close_minute(day): return 900 if day<'2024-11-05' else 930
def sell_starts(day): return [t for t in regular(day) if t not in (540,750)]
def active_elapsed(day,a,b):
    return sum(max(0,min(b,y)-max(a,x)) for x,y in ((540,690),(750,900 if day<'2024-11-05' else 925)))
def clean(rows):
    a=np.asarray(rows,dtype=float).reshape(-1,7)
    assert len(a)==len(set(a[:,0])) and (len(a)<2 or np.all(np.diff(a[:,0])>0))
    good=np.isfinite(a).all(axis=1)&(a[:,3]>0)&(a[:,3]<=np.minimum(a[:,1],a[:,4]))&(np.maximum(a[:,1],a[:,4])<=a[:,2])&(a[:,5]>=0)&(a[:,6]>=0)
    return a[good]
def sell_price(raw): return float(raw)*.9995
def stats(v):
    a=np.asarray([x for x in v if x is not None and np.isfinite(x)],float)
    return {'N':len(a),'mean':float(np.mean(a)) if len(a) else None,'median':float(np.median(a)) if len(a) else None}
def stamp(day,t): return day+'T%02d:%02d:00+09:00'%divmod(t,60)
