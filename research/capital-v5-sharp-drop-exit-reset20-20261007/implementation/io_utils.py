from pathlib import Path
from decimal import Decimal,localcontext
from fractions import Fraction
import json,gzip,hashlib

ROOT=Path(__file__).resolve().parent
PUB=ROOT/'public';PRI=ROOT/'private'
NATIVE=ROOT/'inputs/v5_archive/repo/research/capital-v5-max3-slot-intelligence-20261004-v1'
SHARP=ROOT/'inputs/sharp_archive'
D=Decimal;F=Fraction
def rows(p):return [json.loads(l) for l in gzip.decompress(Path(p).read_bytes()).splitlines() if l]
def atomic(p,b):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 t=p.with_suffix(p.suffix+'.tmp');t.write_bytes(b);t.replace(p)
def save(p,obj):atomic(p,(json.dumps(obj,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode())
def gzsave(p,rr):atomic(p,gzip.compress((''.join(json.dumps(r,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n' for r in rr)).encode(),mtime=0))
def pin(p):
 b=Path(p).read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}
def stamp(day,m):return day+'T%02d:%02d:00+09:00'%divmod(m,60)
def native_pct(pnl,debit):
 with localcontext() as c:
  c.prec=60
  x=D(str(pnl))/D(str(debit))
 return F(str(x))*100
def bucket(r):
 if r is None:return 'R_UNKNOWN'
 if r<=-5:return 'L5_PLUS'
 for bound,label in [(-4,'L4_5'),(-3,'L3_4'),(-2,'L2_3'),(-1,'L1_2')]:
  if r<=bound:return label
 if r<0:return 'L0_1'
 if r==0:return 'ZERO'
 if r<1:return 'P0_1'
 for bound,label in [(2,'P1_2'),(3,'P2_3'),(4,'P3_4'),(5,'P4_5')]:
  if r<bound:return label
 return 'P5_PLUS'
def fmt(x):
 if x is None:return None
 if isinstance(x,F):
  with localcontext() as c:c.prec=80;return str(D(x.numerator)/D(x.denominator))
 return str(x) if isinstance(x,D) else x
def csvsave(p,rr):
 import csv,io
 columns=list(dict.fromkeys(k for r in rr for k in r));s=io.StringIO(newline='')
 w=csv.DictWriter(s,fieldnames=columns,lineterminator='\n');w.writeheader()
 for r in rr:w.writerow({k:json.dumps(v,sort_keys=True,separators=(',',':')) if isinstance(v,(list,dict)) else fmt(v) for k,v in r.items()})
 atomic(p,s.getvalue().encode())
