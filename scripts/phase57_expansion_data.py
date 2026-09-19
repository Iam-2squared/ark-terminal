"""Bounded current-contract acquisition. Exact precommitted allowlists, immutable raw."""
import argparse,datetime,hashlib,json,os,subprocess,time,urllib.request,urllib.error
from pathlib import Path
from scripts import phase57_behavior_dictionary as base
ROOT=base.ROOT;B=ROOT/'docs/evidence/phase57-behavior-expansion-v1'
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):raise ValueError('REDIRECT_FORBIDDEN')
def plan():
 p=base.read(B/'04_session_split_manifest.json');assert base.sha(B/'04_session_split_manifest.json')==base.read(B/'split-lock.json')['sha256'],'SPLIT_HASH'
 assert base.sha(ROOT/'docs/evidence/phase57-research-dictionary-v0/registry.json')==p['registrySha256'],'REGISTRY_HASH'
 d=set(p['dailyDevelopment']);i=set(p['intradayDevelopment']);h=set(p['commonHoldout']);blocked=set(p['excluded'])
 assert not (d|i)&(h|blocked),'SEALED_OVERLAP';assert all(v is False for v in p['safety'].values())
 return p
def authorize(day,kind,p=None):
 p=p or plan();allowed=set(p['dailyDevelopment'])|set(p['intradayDevelopment'])
 if day not in allowed or (kind=='minute' and day not in p['intradayDevelopment']):raise ValueError('ACQUISITION_BOUNDARY')
 if kind not in ['daily','master','minute']:raise ValueError('ENDPOINT_NOT_ALLOWED')
def matrix():
 p=plan();jobs=[]
 for kind,dates,size in [('daily',p['dailyDevelopment'],20),('minute',[d for d in p['intradayDevelopment'] if d not in p['reuseMinuteDates']],5)]:
  for n in range(0,len(dates),size):jobs.append({'id':f'{kind}-{n//size:03d}','kind':kind,'dates':dates[n:n+size]})
 return jobs
def restore(archives,destination):
 p=plan();allowed=set(p['dailyDevelopment'])|set(p['intradayDevelopment']);receipts=[]
 for f in sorted(Path(archives).rglob('*.tar.gz.enc')):
  expected=f.with_name(f.name+'.sha256').read_text().split()[0];assert base.sha(f)==expected
  proc=subprocess.Popen(['openssl','enc','-d','-aes-256-cbc','-pbkdf2','-iter','200000','-pass','env:JQUANTS_API_KEY','-in',str(f)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  try:r=base.extract_stream(proc.stdout,destination,allowed)
  finally:proc.stdout.close();err=proc.stderr.read();ret=proc.wait()
  assert ret==0,'DECRYPT_FAILED';receipts.append({'archiveSha256':expected,**r})
 return receipts
def encrypt(directory,output):
 output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
 proc=subprocess.Popen(['tar','-czf','-','-C',str(Path(directory).parent),Path(directory).name],stdout=subprocess.PIPE)
 r=subprocess.run(['openssl','enc','-aes-256-cbc','-salt','-pbkdf2','-iter','200000','-pass','env:JQUANTS_API_KEY','-out',str(output)],stdin=proc.stdout,capture_output=True)
 proc.stdout.close();assert proc.wait()==0 and r.returncode==0,'ENCRYPT_FAILED'
 base.write(str(output)+'.sha256',base.sha(output)+'\n')
def request_pages(day,kind,destination,budget):
 authorize(day,kind);dest=Path(destination)/day;dest.mkdir(parents=True,exist_ok=True)
 target=dest/(kind+'-pages.json')
 if target.exists():
  rows,info=base.pages(target);assert all(r['Date']==day for r in rows),'REUSE_DATE'
  return {'session':day,'kind':kind,'reused':True,**info}
 endpoint='equities/master' if kind=='master' else 'equities/bars/'+kind
 pages=[];cursor=None;seen=set();key=os.environ['JQUANTS_API_KEY'];opener=urllib.request.build_opener(NoRedirect())
 partial=dest/(kind+'-checkpoint.json')
 if partial.exists():
  checkpoint=base.read(partial);pages=checkpoint['pages'];cursor=checkpoint['nextCursor'];seen=set(checkpoint['seen'])
  for page in pages:assert hashlib.sha256(page['responseText'].encode()).hexdigest()==page['responseSha256']
 completed_checkpoint=bool(pages) and cursor is None
 while not completed_checkpoint:
  assert budget['requests']<budget['limit'],'REQUEST_BUDGET';assert len(pages)<30,'PAGE_LIMIT'
  query={'date':day}
  if cursor:query['pagination_key']=cursor
  from urllib.parse import urlencode
  url='https://api.jquants.com/v2/'+endpoint+'?'+urlencode(query)
  time.sleep(2.6);budget['requests']+=1
  req=urllib.request.Request(url,headers={'x-api-key':key})
  with opener.open(req,timeout=120) as response:raw=response.read()
  text=raw.decode('utf8');body=json.loads(text);rows=body['data']
  assert isinstance(rows,list) and all(r['Date']==day for r in rows),'CROSS_DATE'
  pages.append({'page':len(pages)+1,'responseSha256':hashlib.sha256(raw).hexdigest(),'responseText':text,'request':{'endpoint':'/v2/'+endpoint,'params':query},'acquiredAt':datetime.datetime.now(datetime.timezone.utc).isoformat()})
  nxt=body.get('pagination_key')
  if nxt:
   assert nxt not in seen,'PAGINATION_CYCLE';seen.add(nxt)
  # fsync atomic checkpoint after every physical response; resume never substitutes retrieval for historical knownAt.
  temp=partial.with_suffix('.tmp');temp.write_text(json.dumps({'pages':pages,'nextCursor':nxt,'seen':sorted(seen)}));
  with temp.open('rb') as f:os.fsync(f.fileno())
  temp.replace(partial)
  if not nxt:break
  cursor=nxt
 base.write(target,pages);partial.unlink();rows,info=base.pages(target)
 keyfields=['Code','Date']+(['Time'] if kind=='minute' else [])
 assert len({tuple(r.get(k) for k in keyfields) for r in rows})==len(rows),'DUPLICATE_ROWS'
 return {'session':day,'kind':kind,'reused':False,'historicalKnownAt':None,**info}
def acquire(jobid,cache,output):
 job=next(j for j in matrix() if j['id']==jobid);budget={'requests':0,'limit':len(job['dates'])*(32 if job['kind']=='minute' else 2)};records=[];error=None
 try:
  for d in job['dates']:
   for kind in (['daily','master','minute'] if job['kind']=='minute' else ['daily','master']):records.append(request_pages(d,kind,cache,budget))
 except Exception as e:error={'type':type(e).__name__,'reason':str(e)}
 out=Path(output);out.mkdir(parents=True,exist_ok=True)
 # Archive layout contains jquants-v2/date; compatible with selective extraction.
 encrypt(cache,out/(jobid+'.tar.gz.enc'))
 base.write(out/(jobid+'-receipt.json'),{'job':job,'budget':budget,'records':records,'error':error,'localRawPersisted':True,'remoteRawPersisted':'REQUIRES_ARTIFACT_UPLOAD_RECEIPT','sealedRequests':0,'labels':['RESEARCH_ONLY','NOT_PIT_VERIFIED'],'splitHash':base.sha(B/'04_session_split_manifest.json')})
 print(json.dumps({'job':jobid,'requests':budget['requests'],'error':error}),flush=True)
 if error:raise RuntimeError('PARTITION_FAILED_RAW_CHECKPOINT_PRESERVED')
def main():
 a=argparse.ArgumentParser();a.add_argument('command',choices=['matrix','restore','acquire','encrypt']);a.add_argument('--archives');a.add_argument('--cache');a.add_argument('--output');a.add_argument('--job');x=a.parse_args()
 if x.command=='matrix':print(json.dumps({'include':matrix()},separators=(',',':')))
 elif x.command=='restore':base.write(x.output,restore(x.archives,x.cache))
 elif x.command=='encrypt':encrypt(x.cache,x.output)
 else:acquire(x.job,x.cache,x.output)
if __name__=='__main__':main()
