"""CAL sign/score-only operating points; no evaluation-label or return input."""
import math,struct
def encode(t):
 if math.isinf(t):return {'sentinel':'POSITIVE_INFINITY' if t>0 else 'NEGATIVE_INFINITY','comparison':'KEEP finite eta>=tau; missing eta KEEP'}
 return {'value':float(t),'round_trip':repr(float(t)),'hex':float(t).hex(),'ieee754_binary64_be':struct.pack('>d',float(t)).hex()}
def decode(t):return math.inf if t.get('sentinel')=='POSITIVE_INFINITY' else -math.inf if t.get('sentinel')=='NEGATIVE_INFINITY' else float.fromhex(t['hex'])
def decide(eta,threshold):
 if eta is None:return 'KEEP'
 if not math.isfinite(float(eta)):raise ValueError('INVALID_SCORE')
 return 'KEEP' if float(eta)>=decode(threshold) else 'DROP'
def cal_point(rows,point):
 if any(set(r)!={'entry_id','eta','sign_status'} for r in rows):raise ValueError('UNAUTHORIZED_CAL_CAPABILITY')
 if point=='ALL_KEEP':return {'status':'BASELINE','threshold':encode(-math.inf)}
 if point=='CAL95':
  a=sorted(float(r['eta']) for r in rows if r['sign_status']=='PLUS' and r['eta'] is not None)
  if not a:return {'status':'CAL_PLUS_SUPPORT_UNAVAILABLE','threshold':encode(-math.inf),'N_plus':0}
  k=5*len(a)//100;return {'status':'OK','threshold':encode(a[k]),'N_plus':len(a),'k':k,'tie_rule':'KEEP all equal tau'}
 gamma=int(point.rsplit('_',1)[-1]);assert gamma in [80,60,40,20,10]
 minus=[r['eta'] for r in rows if r['sign_status']=='MINUS'];n=len(minus);k=gamma*n//100
 if not n:return {'status':'CAL_MINUS_SUPPORT_UNAVAILABLE','threshold':None,'N_minus_total':0}
 missing=sum(v is None for v in minus)
 if missing>k:return {'status':'TARGET_UNATTAINABLE_WITH_KEEP_FALLBACK','N_minus_total':n,'k_total':k,'missing_minus_KEEP':missing,'threshold':None}
 a=sorted(float(v) for v in minus if v is not None);assert all(math.isfinite(v) for v in a)
 kv=k-missing;tau=-math.inf if kv>=len(a) else math.nextafter(a[len(a)-kv-1],math.inf)
 return {'status':'OK','gamma_percent':gamma,'N_minus_total':n,'N_minus_valid':len(a),'k_total':k,'k_valid':kv,'missing_minus_KEEP':missing,'threshold':encode(tau),'tie_rule':'boundary-score ties all DROP; no ID splitting'}
