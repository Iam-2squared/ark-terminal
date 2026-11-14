"""Only H2/H3/H5 probabilities and past training rates enter Capital decisions."""
import math
def pava(raw):
 assert len(raw)==3 and all(math.isfinite(v) and 0<=v<=1 for v in raw)
 pools=[]
 for value in raw:
  pools.append([value,1])
  while len(pools)>=2 and pools[-2][0]/pools[-2][1]<pools[-1][0]/pools[-1][1]:
   b=pools.pop();a=pools.pop();pools.append([a[0]+b[0],a[1]+b[1]])
 fitted=[total/count for total,count in pools for _ in range(count)]
 assert 1>=fitted[0]>=fitted[1]>=fitted[2]>=0
 return fitted
def band(score):
 assert score is not None and math.isfinite(score) and score>=0
 return 'S' if score>=2 else 'A' if score>=1.5 else 'B' if score>=1 else 'C'
def materialize(row):
 raw=[float(row[k]) for k in ('p2','p3','p5')];bases=[float(row[k]) for k in ('base2','base3','base5')]
 assert 1>=bases[0]>=bases[1]>=bases[2]>=0,'CONTRACT_FAIL_BASE_ORDER'
 m=pava(raw);M=sum(m);B=sum(bases);assert B>0
 ML=M/B;return {'m2':m[0],'m3':m[1],'m5':m[2],'M':M,'B':B,'ML':ML,'capital_score':ML,'admission':ML>=1,'rank':band(ML),'capacity_band':band(ML)}
def candidate_order(r):return (-r['ML'],-r['m5'],-r['m3'],-r['m2'],r['entry_timestamp'],r['symbol'])
