"""M0 primary path. No imports from either State9 engine or 120 path."""
from decimal import Decimal,Context,ROUND_HALF_EVEN,localcontext,InvalidOperation,DivisionByZero,Overflow
import re
GRAM=re.compile(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?',re.ASCII)
Q=Decimal('1e-24')
def context():
 c=Context(prec=80,rounding=ROUND_HALF_EVEN,Emin=-999999,Emax=999999,clamp=0)
 for signal in c.traps:c.traps[signal]=signal in (InvalidOperation,DivisionByZero,Overflow)
 return c
def positive(s):
 if type(s) is not str or not GRAM.fullmatch(s):raise ValueError('RAW_DECIMAL_LEXEME_REQUIRED')
 v=Decimal(s)
 if not v.is_finite() or v<=0:raise ValueError('NONPOSITIVE_RAW_PRICE')
 return v
def bucket(row,first_am,first_pm):
 m=int(row['Time'][:2])*60+int(row['Time'][3:]);late=row['Date']>='2024-11-05'
 if m in (690,930 if late else 900):return 'TERMINAL_AUCTION_MINUTE'
 if m==first_am or m==first_pm:return 'OPENING_MIXED_MINUTE'
 if 540<=m<690 or 750<=m<(925 if late else 900):return 'CONTINUOUS'
 raise ValueError('SOURCE_TIME_OUTSIDE_DATED_INTERVAL_SPEC')
def generate(previous,current):
 with localcontext(context()) as ctx:
  ctx.clear_flags();p=sorted(previous,key=lambda r:r['Time']);a=[int(r['Time'][:2])*60+int(r['Time'][3:]) for r in p]
  am=min((m for m in a if m<690),default=None);pm=min((m for m in a if m>=750 and m<(925 if p[0]['Date']>='2024-11-05' else 900)),default=None)
  returns=[];pair_ids=[]
  for left,right in zip(p,p[1:]):
   lm=int(left['Time'][:2])*60+int(left['Time'][3:]);rm=int(right['Time'][:2])*60+int(right['Time'][3:])
   if rm-lm!=1 or bucket(left,am,pm)!=bucket(right,am,pm) or bucket(left,am,pm)!='CONTINUOUS':continue
   returns.append(abs(positive(right['C']).ln()-positive(left['C']).ln()));pair_ids.append([left['_source'],right['_source']])
  if not returns:raise ValueError('U_UNAVAILABLE')
  returns.sort();n=len(returns);median=returns[n//2] if n%2 else (returns[n//2-1]+returns[n//2])/Decimal(2)
  U=max(Decimal('1.001').ln(),Decimal('0.5')*median).quantize(Q)
  if U<=0:raise ValueError('U_UNAVAILABLE')
  pref=positive(p[-1]['C']);coords=[]
  for row in current:
   values={k:format(((positive(row[k]).ln()-pref.ln())/U).quantize(Q),'f') for k in ('O','H','L','C')}
   coords.append(values)
  return {'U':format(U,'f'),'P_ref':p[-1]['C'],'previous_return_pairs_N':n,'previous_pair_ids':pair_ids,
   'previous_last_source':p[-1]['_source'],'previous_last_source_time':p[-1]['Time'],'coordinates':coords,
   'flags':{s.__name__:bool(v) for s,v in ctx.flags.items()},'precision':80}
