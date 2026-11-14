"""Saved277 Development path diagnostic, no Entry prediction or EXIT selection."""
import collections,gzip,hashlib,json
from pathlib import Path
from scripts.summarize_phase57_long_exit_paired import dist,rate

BASE=Path('docs/evidence/phase57-long-exit-continuation-v1')
def measure(rows):
 if not rows or any(b['missing'] for b in rows):return None
 hi=max(b['h'] for b in rows);lo=min(b['l'] for b in rows)
 return {'close':rows[-1]['c'],'mfe':max(0,hi),'mae':min(0,lo),'mfeTime':next(b['minutes'] for b in rows if b['h']==hi),'firstPositive':next((b['minutes'] for b in rows if b['c']>0),None),'giveback':max(0,hi)-rows[-1]['c']}
def diagnostic():
 raw=gzip.decompress(Path('docs/evidence/phase57-long-exit-v345-paired/paths.json.gz').read_bytes());assert hashlib.sha256(raw).hexdigest()=='01543fb3c003f939d73567280f9141392f254f1ec3c058b3163f5dede33fc5fd'
 es=json.loads(raw)['events'];prefix={x['selectorEventId']:x['prefix'] for x in json.loads(Path('docs/evidence/phase57-long-exit-v5-fast-track/prefix-ledger.json').read_text())}
 groups={'NON_ADVERSE_REQUIRES_V4':'A_FIRST_BAR_NON_ADVERSE','RECLAIM_OBSERVED_REQUIRES_V4':'B_ADVERSE_RECLAIM_BY_BAR5','NO_RECLAIM_THROUGH_BAR5_OBSERVED':'C_ADVERSE_NO_RECLAIM_BY_BAR5','UNKNOWN':'D_PATH_INCOMPLETE'}
 per=[]
 for e in es:
  p=prefix[e['selectorEventId']];rs={}
  for h in [5,10,15,20,25,30,45,60]:
   rows=[b for b in e['future'] if b['minutes']<=h]
   crosses=e['entryMinute']<690<e['entryMinute']+h or 690<=e['entryMinute']<750
   rs[str(h)]=None if crosses or e['entryMinute']+h>e['sessionEndMinute'] or not rows or rows[-1]['minutes']!=h else measure(rows)
  rs['SESSION_END']=measure(e['future'])
  running=[];peak=0;low=0;previous=None
  for b in e['future']:
   if b['missing']:break
   updated=b['h']>peak;peak=max(peak,b['h']);low=min(low,b['l'])
   running.append({'bar':b['slot'],'clockMinutes':b['minutes'],'closePct':b['c'],'runningMfePct':peak,'runningMaePct':low,'newMfe':updated,'givebackPctPoints':peak-b['c'],'mfeUpdateBar':b['slot'] if updated else previous});previous=running[-1]['mfeUpdateBar']
  per.append({'selectorEventId':e['selectorEventId'],'cohort':groups[p['state']],'firstBarExactlyFlat':bool(e['future'] and not e['future'][0]['missing'] and e['future'][0]['c']==0),'reclaimBar':p.get('reclaimBar'),'horizons':rs,'observableRunningPrefix':running,'firstHits':{str(k):next((b['clockMinutes'] for b in running if b['runningMfePct']>=k),None) for k in [1,2,3,5]}})
 out={}
 for group in ['ALL',*groups.values()]:
  selected=[r for r in per if group=='ALL' or r['cohort']==group];hs={}
  for h in ['5','10','15','20','25','30','45','60','SESSION_END']:
   valid=[r['horizons'][h] for r in selected if r['horizons'][h] is not None]
   hs[h]={'available':rate(len(valid),len(selected)),**{key:dist([p[key] for p in valid]) for key in ['close','mfe','mae','mfeTime','firstPositive','giveback']},'hits':{str(k):rate(sum(p['mfe']>=k for p in valid),len(valid)) for k in [1,2,3,5]}}
  out[group]={'n':len(selected),'exactlyFlat':sum(r['firstBarExactlyFlat'] for r in selected),'horizons':hs}
 BASE.mkdir(parents=True,exist_ok=True)
 for f,v in [('path-diagnostic.json',out),('path-diagnostic-ledger.json',per)]:
  p=BASE/f;assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n')
 print(json.dumps({k:{'n':v['n'],'flat':v['exactlyFlat'],'30m':v['horizons']['30'],'60m':v['horizons']['60']} for k,v in out.items()}))
if __name__=='__main__':diagnostic()
