"""Standalone scalar inference / Fraction accounting auditor.

Never imports Primary mapping, runtime, execution, replay, oracle or evaluator.
Input market source independence is not claimed; implementation independence is.
"""
from pathlib import Path
from fractions import Fraction as F
from decimal import Decimal as D
from bisect import bisect_left
from collections import Counter,defaultdict
from statistics import mean,median
import gzip,json,hashlib,math
ROOT=Path(__file__).resolve().parents[2];W=ROOT.parent/'v10_work';P=W/'private';I=W/'authority/main/inputs';PIN=W/'authority/main/private';Q=W/'authority/quality_original';O=ROOT/'docs/evidence/capital-v10-monetization-sizing-20261005-v1';PARENT=ROOT/'docs/evidence/capital-v8r1-cash-constrained-online-max3-20261005-v1'
ARMS=['I2_EQUAL_WEIGHT_SIZING_V1','I2_CONSENSUS_MINRANK_SIZING_V1'];BANDS=['P_HIGH','P_MID','P_BASE','P_BELOW'];CAP=[F(45,100),F(35,100),F(25,100)];BASE=[F(68,100),F(56,100),F(44,100)]
def read(p):return json.loads(Path(p).read_text())
def rows(p):
 with gzip.open(p,'rt') as f:return [json.loads(x) for x in f if x.strip()]
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def key(r):return (-r['pP'],r['entry_timestamp'],r['symbol'],r['entry_id'])
class Audit:
 def __init__(self):self.checks=0;self.mismatches=[];self.max_float_delta=0
 def check(self,name,ok):
  self.checks+=1
  if not ok and len(self.mismatches)<200:self.mismatches.append(name)
 def money(self,name,a,b):self.check(name,F(a)==F(b))
 def num(self,name,a,b):
  delta=abs(a-b);self.max_float_delta=max(self.max_float_delta,delta);self.check(name,delta<=1e-12)
def actual(row,auction=False):
 try:
  vals=[F(row[k]) for k in ('O','H','L','C','Vo','Va')];o,h,l,c,vo,va=vals
  return bool(row.get('lineage')) and all(v>0 for v in vals) and l<=min(o,c)<=max(o,c)<=h and (not auction or o==h==l==c)
 except (KeyError,ValueError,ZeroDivisionError):return False
def clock(s):return int(s[11:13])*60+int(s[14:16])
def early(book):
 x=book['frozen_exit']
 if x['sell_status']!='FILLED' or clock(x['sell_source_assumed_available_at'])>920:return None
 r=next((r for r in book['market'] if r['minute']==x['sell_minute']),None)
 if r is None or not actual(r):return None
 price=F(r['O'] if x['sell_source']=='NEXT_ELIGIBLE_REGULAR_RAW_OPEN' else r['C'])*F(9995,10000)
 assert price==F(x['sell_price_decimal'])
 return {'release':clock(x['sell_source_assumed_available_at']),'source':r['minute'],'price':price,'kind':'FROZEN_EXIT_V3'}
def late(book):
 rr=[r for r in book['market'] if r['session']==book['session'] and 920<=r['minute']<925 and actual(r)];aa=[r for r in book['market'] if r['session']==book['session'] and r['minute']==930 and actual(r,True)]
 r=min(rr,key=lambda r:r['minute']) if rr else aa[0] if aa else None
 if r is None:return None
 return {'release':r['minute']+1,'source':r['minute'],'price':F(r['O'] if rr else r['C'])*F(9995,10000),'kind':'EOD_REGULAR' if rr else 'EOD_EXACT_1530_AUCTION'}
def lot_allocate(picked,equity,cash,held_bands):
 ids=[BANDS.index(b) for b in held_bands]+[BANDS.index(r['band']) for r in picked];target=min(F(92,100),BASE[min(ids)]+F(55,1000)*(len(ids)-1));budget=min(cash,max(F(0),equity*target-(equity-cash)));ws=[F(str(r['sizing_weight'])) for r in picked];remaining=cash;unspent=budget;alloc=[]
 for r,w in zip(picked,ws):
  lot=F(r['raw_reference'])*F(10005,10000)*100;cap=equity*CAP[BANDS.index(r['band'])];desired=budget*w/sum(ws);lots=max(0,int(min(desired,cap,remaining)//lot));debit=lots*lot;remaining-=debit;unspent-=debit
  alloc.append({'quantity':lots*100,'first_pass_quantity':lots*100,'debit':debit,'lot_debit':lot,'equity_cap':cap,'batch_budget':budget,'batch_equity':equity,'target_utilization':target,'water_fill_lots':0,'desired':desired,'sizing_weight':w,'rp':r['rp'],'r2':r['r2'],'r3':r['r3']})
 rounds=0
 while True:
  changes=0
  for z in alloc:
   if z['first_pass_quantity'] and z['lot_debit']<=min(remaining,unspent,z['equity_cap']-z['debit']):
    z['quantity']+=100;z['debit']+=z['lot_debit'];z['water_fill_lots']+=1;remaining-=z['lot_debit'];unspent-=z['lot_debit'];changes+=1
  if not changes:break
  rounds+=1
 for z in alloc:z.update(water_fill_rounds=rounds,budget_unspent=unspent)
 return alloc

