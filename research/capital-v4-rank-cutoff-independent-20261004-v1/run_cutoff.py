from common import *
from replay import run_profile
import sys
def main():
 arm=sys.argv[1];assert arm in PROFILES
 pin=json.loads((OUT/'CODE_PRECOMMIT.json').read_text());assert all(sha(CODE/k)==v for k,v in pin.items())
 save(PRIVATE/f'{arm}_STARTED.json',{'JST':now(),'replay_count':1,'rerun_permitted':False})
 result,ds,ts,cs,it=run_profile(arm,3,rows(FROZEN/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz'),source_books())
 assert not result['blocked_execution_day_N']
 result.update(avg_funded_per_session=result['funded_N']/38,session_max_concurrent_counts={str(i):sum(d['max_concurrent']==i for d in result['daily_series']) for i in range(4)},daily_sign_counts={k:sum(fn(d['daily_return']) for d in result['daily_series']) for k,fn in [('positive',lambda x:x>0),('negative',lambda x:x<0),('zero',lambda x:x==0)]})
 for label,data in [('DECISIONS',ds),('TRADES',ts),('CURVE',cs),('INTENTS',it)]:gzwrite(PRIVATE/f'{arm}_{label}.jsonl.gz',data)
 save(PRIVATE/f'{arm}_RESULT.json',result)
 if arm=='B_PLUS_MAX3':
  old='UPWARD_STAIRCASE_V4_MAX3';mismatch=[]
  for label,new in [('DECISIONS',ds),('TRADES',ts),('CURVE',cs),('INTENTS',it)]:
   saved=rows(FROZEN/f'{old}_{label}.jsonl.gz');norm=lambda records:[{k:v for k,v in r.items() if k!='profile'} for r in records]
   if norm(new)!=norm(saved):mismatch.append(label)
  saved=json.loads((FROZEN/f'{old}_RESULT.json').read_text())
  for k,v in saved.items():
   if k not in ('profile','arm','score_stream_sha256') and result.get(k)!=v:mismatch.append('RESULT/'+k)
  identity={'JST':now(),'status':'B_PLUS_V4_IDENTITY_MISMATCH' if mismatch else 'B_PLUS_V4_EXACT_IDENTITY_PASS','mismatch':mismatch,'final_equity_exact':result['final_equity'],'normalization':'Only diagnostic profile name differs; all other saved ledger fields and result metrics exact.'}
  save(OUT/'B_PLUS_IDENTITY.json',identity);assert not mismatch,'B_PLUS_V4_IDENTITY_MISMATCH'
 cp={'S_ONLY_MAX3':'R3_S_ONLY_REPLAY','A_PLUS_MAX3':'R4_A_PLUS_REPLAY','B_PLUS_MAX3':'R5_B_PLUS_IDENTITY_REPLAY'}[arm]
 public={k:v for k,v in result.items() if k not in ('daily_series','rolling20_windows')};save(OUT/f'{arm}_ECONOMIC.json',public)
 checkpoint(cp,'FROZEN_CUTOFF_REPLAY_COMPLETE',public)
 print(json.dumps(public),flush=True)
if __name__=='__main__':main()
