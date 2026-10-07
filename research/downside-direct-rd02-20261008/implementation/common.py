"""RD02 byte-stable IO and fixed, outcome-independent contracts."""
from pathlib import Path
import json, gzip, hashlib, math
from fractions import Fraction

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'rd02'; PUB=WORK/'public'; PRIVATE=WORK/'private'; INPUT=ROOT/'inputs'
DOC='ARK_RANK_DOWNSIDE_DIRECT_RD02_20261008'
BRANCH='research/downside-direct-rd02-20261008'
STATES=['RISE_STOP','RISE','SHARP_RISE','PULLBACK','RANGE','REBOUND','SHARP_DROP','DROP','DROP_STOP']
CLASSES=['T5','T3_5','T2_3','T0_2','NONNEG']
BANDS=['P5_PLUS','P4_5','P3_4','P2_3','P1_2','P0_1','L0_1','L1_2','L2_3','L3_4','L4_5','L5_PLUS','ZERO','R_UNKNOWN']
METHODS=['D-LINEAR','D-PRICE','D-FULL']
PRICE=[f'PRICE/w{w}/{x}' for w in [5,20,60] for x in ['coverage','net_log','range_log','from_high_log','from_low_log','signed_efficiency','return_rms','close_drawdown','down_pair_rate','down_volume_share','mean_volume_log1p','mean_value_log1p']]+['PRICE/'+x for x in ['body','upper_wick','lower_wick','flat','volume5_20_log','value5_20_log','active_minutes','raw_age','raw_breaks60']]
STATE=[f'STATE/w{w}/{x}' for w in [20,60] for x in STATES+['coverage','transitions']]+['STATE/run_duration','STATE/last_valid_age','STATE/breaks60']
CAT=['STATE/current','STATE/previous_run','STATE/previous_previous_run','STATE/quality_reset_reason']
# All combinations of frozen reset enum tokens are defined from the contract,
# independent of observed frequencies or development outcomes.
RESET_ENUM=['AFTER_UNAVAILABLE','AUCTION_CHANGE','FROZEN_RESET_EVENT','INITIAL_SEGMENT','ORDINAL_GAP']
RESET_VOCAB=['RESET:'+'|'.join(sorted(RESET_ENUM[i] for i in range(len(RESET_ENUM)) if mask&(1<<i))) for mask in range(1,1<<len(RESET_ENUM))]
QUALITY_ENUM=['OBSERVED_VALID','INITIALIZING','CARRIED_GAP','QUALITY_ABSTAIN','SOURCE_UNAVAILABLE','NO_ADMISSIBLE_CLOSED_BAR','NOT_AVAILABLE','INVALID','REJECTED','NOT_NORMALIZABLE','OPENING_MIXED_MINUTE','TERMINAL_AUCTION_MINUTE','UNKNOWN']
VOCAB={CAT[0]:STATES+['INITIALIZING','QUALITY_ABSTAIN','CARRIED_GAP','SOURCE_UNAVAILABLE','START','UNKNOWN'],CAT[1]:STATES+['START','UNKNOWN'],CAT[2]:STATES+['START','UNKNOWN'],CAT[3]:QUALITY_ENUM+RESET_VOCAB}
SAFETY={k:False for k in ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','productionReady']}

def canonical(x):return (json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def blob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def pin(p):
 b=Path(p).read_bytes();return {'bytes':len(b),'sha256':sha(b),'git_blob':blob(b)}
def read(p):return json.loads(Path(p).read_bytes())
def save(p,x,once=False):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);b=canonical(x)
 if once and p.exists():assert p.read_bytes()==b,'RESUME_HASH_MISMATCH:'+str(p);return
 p.write_bytes(b)
def rows(p):return [json.loads(x) for x in gzip.decompress(Path(p).read_bytes()).splitlines()]
def gzsave(p,rr,once=False):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);b=gzip.compress(b''.join(canonical(r) for r in rr),mtime=0)
 if once and p.exists():assert p.read_bytes()==b,'RESUME_HASH_MISMATCH:'+str(p);return
 p.write_bytes(b)
def unpack(r):return Fraction(int(r['r_numerator']),int(r['r_denominator'])) if r.get('known') else None
def target(r):
 if r is None:return None
 return 0 if r<=-5 else 1 if r<=-3 else 2 if r<=-2 else 3 if r<0 else 4
def bucket(r):
 if r is None:return 'R_UNKNOWN'
 if r>=5:return 'P5_PLUS'
 for lower,label in [(4,'P4_5'),(3,'P3_4'),(2,'P2_3'),(1,'P1_2')]:
  if r>=lower:return label
 if r>0:return 'P0_1'
 if r==0:return 'ZERO'
 if r>-1:return 'L0_1'
 for lower,label in [(-2,'L1_2'),(-3,'L2_3'),(-4,'L3_4'),(-5,'L4_5')]:
  if r>lower:return label
 return 'L5_PLUS'
def regular_starts():return list(range(540,690))+list(range(750,925))
def active(t):return sum(m<t for m in regular_starts())
def stamp(day,t):return f'{day}T{t//60:02d}:{t%60:02d}:00+09:00'
def finite(x):return x is not None and math.isfinite(float(x))
