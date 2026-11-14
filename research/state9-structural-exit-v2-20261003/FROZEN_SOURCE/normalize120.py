"""Independent M0 regeneration: own ordering, pairing, lexeme checks, U and x."""
from decimal import Decimal,Context,localcontext,ROUND_HALF_EVEN,InvalidOperation,DivisionByZero,Overflow
def decimal_price(text):
 if type(text)!=str or not text.isascii():raise ValueError('EXACT_RAW_STRING_REQUIRED')
 import re
 if re.fullmatch(r'-?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?',text,flags=re.ASCII) is None:raise ValueError('RAW_LEXICAL_ERROR')
 x=Decimal(text)
 if not x.is_finite() or x<=0:raise ValueError('NONPOSITIVE_RAW_PRICE')
 return x
def regenerate(rows,observations):
 config=Context(prec=120,rounding=ROUND_HALF_EVEN,Emin=-999999,Emax=999999,clamp=0)
 for flag in config.traps:config.traps[flag]=flag in {InvalidOperation,DivisionByZero,Overflow}
 with localcontext(config) as ctx:
  ctx.clear_flags();ordered=list(rows);ordered.sort(key=lambda x:tuple(int(v) for v in x['Time'].split(':')))
  minutes=[60*int(x['Time'].split(':')[0])+int(x['Time'].split(':')[1]) for x in ordered]
  terminal=930 if ordered[0]['Date']>='2024-11-05' else 900
  afternoon_stop=925 if terminal==930 else 900
  opening_am=next((m for m in minutes if 540<=m<690),None)
  opening_pm=next((m for m in minutes if 750<=m<afternoon_stop),None)
  changes=[];ids=[]
  for i in range(1,len(ordered)):
   old,new=minutes[i-1],minutes[i]
   same_segment=(540<=old<new<690) or (750<=old<new<afternoon_stop)
   if new!=old+1 or not same_segment or old in (opening_am,opening_pm) or new in (opening_am,opening_pm):continue
   delta=decimal_price(ordered[i]['C']).ln()-decimal_price(ordered[i-1]['C']).ln()
   changes.append(delta.copy_abs());ids.append([ordered[i-1]['_source'],ordered[i]['_source']])
  if len(changes)==0:raise ValueError('U_UNAVAILABLE')
  changes=sorted(changes);count=len(changes)
  middle=changes[(count-1)//2] if count%2 else (changes[count//2]+changes[count//2-1])/Decimal('2')
  minimum=Decimal('1.001').ln();scale=middle/Decimal('2')
  u=(minimum if minimum>scale else scale).quantize(Decimal('0.000000000000000000000001'),rounding=ROUND_HALF_EVEN)
  origin=decimal_price(ordered[-1]['C']);out=[]
  for candle in observations:
   r={}
   for name in ['O','H','L','C']:
    z=(decimal_price(candle[name]).ln()-origin.ln())/u
    r[name]=format(z.quantize(Decimal('1E-24'),rounding=ROUND_HALF_EVEN),'f')
   out.append(r)
  return {'U':format(u,'f'),'P_ref':ordered[-1]['C'],'previous_return_pairs_N':count,'previous_pair_ids':ids,
   'previous_last_source':ordered[-1]['_source'],'previous_last_source_time':ordered[-1]['Time'],'coordinates':out,
   'flags':{s.__name__:bool(v) for s,v in ctx.flags.items()},'precision':120}
