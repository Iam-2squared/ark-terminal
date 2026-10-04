"""Reuse encrypted saved Development cache; compact actual historical aggregates only."""
import argparse,gzip,hashlib,json,os,subprocess,sys,tarfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from decimal import Decimal
from movement import raw_bins,raw_prefix,bitmap,activity,valid

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'research/capital-bigwinner-one-shot-20261004-v1'))
from recover_saved_source import pages
def digest(raw):return hashlib.sha256(raw).hexdigest()

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--archives',required=True);ap.add_argument('--out',required=True);args=ap.parse_args()
 scope=json.loads((HERE/'SOURCE_RECOVERY_SCOPE.json').read_text());allowed=set(scope['source_dates_authorized'])
 split=json.loads((ROOT/'docs/evidence/phase57-behavior-expansion-v1/04_session_split_manifest.json').read_text())
 assert not allowed&set(split['commonHoldout']) and allowed<=set(split['intradayDevelopment'])|set(split['dailyDevelopment'])
 ledger=json.loads((ROOT/'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/source-ledger.json').read_text())
 pins={(r['session'],r['kind']):r['sha256'] for r in ledger}
 symbols=set(scope['symbol_sha256']);clocks=scope['entry_clock_by_symbol_hash']
 archives=sorted(Path(args.archives).rglob('*.tar.gz.enc'));assert archives and os.environ.get('JQUANTS_API_KEY')
 def one(archive):
  expected=archive.with_name(archive.name+'.sha256').read_text().strip()
  expected=(json.loads(expected) if expected.startswith('"') else expected).split()[0]
  assert digest(archive.read_bytes())==expected
  proc=subprocess.Popen(['openssl','enc','-d','-aes-256-cbc','-pbkdf2','-iter','200000','-pass','env:JQUANTS_API_KEY','-in',str(archive)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  records={};sources={};opened=[]
  try:
   with tarfile.open(fileobj=proc.stdout,mode='r|gz') as tar:
    for member in tar:
     kind={'minute-pages.json':'minute','daily-pages.json':'daily'}.get(Path(member.name).name)
     day=next((s for s in Path(member.name).parts if len(s)==10 and s[4:5]=='-' and s[7:8]=='-'),None)
     if not member.isfile() or not kind or day not in allowed:continue
     raw=tar.extractfile(member).read();rows,receipt=pages(raw,day,kind,pins[day,kind]);del raw
     source={'wrapper_sha256':pins[day,kind],'terminal_pagination_proven':True,'date_scope_complete':True,
      'provider':'JQUANTS_V2_EQUITIES_BARS_'+kind.upper(),'historical_actual_arrival':'UNKNOWN','assumed_available_at':day+'T16:30:00+09:00'}
     sources[day,kind+'_source']=source;opened.append({'session':day,'kind':kind,'wrapper_sha256':pins[day,kind],'pages':receipt})
     hashes={};touched=set()
     for row,lineage in rows:
      code=row['Code'];h=hashes.setdefault(code,digest(code.encode()))
      if h not in symbols:continue
      rec=records.setdefault((day,code),{'session':day,'symbol':code,'daily':None,'bins':[],'prefixes':{},'active_minute_bitmap_hex':'0'*82})
      touched.add((day,code))
      if kind=='daily':rec['daily']={**{k:row.get(k) for k in ('O','H','L','C','Va','Vo')},'lineage':lineage}
      else:
       hh,mm=map(int,row['Time'].split(':'));t=hh*60+mm
       rr={'minute':t,**{k:row.get(k) for k in ('O','H','L','C','Va','Vo')},'lineage':lineage}
       if (540<=t<690 or 750<=t<925) and valid(rr):rec.setdefault('_market',[]).append(rr)
     if kind=='minute':
      for key in touched:
       rec=records[key];market=rec.pop('_market',[])
       rec['bins']=raw_bins(market);rec['active_minute_bitmap_hex']=bitmap(market)
       rec.update(activity(rec['active_minute_bitmap_hex']))
       h=digest(rec['symbol'].encode());rec['prefixes']={str(t):raw_prefix(market,t) for t in clocks[h]}
     del rows
   assert proc.wait()==0,'DECRYPT_FAILED'
  finally:
   if proc.poll() is None:proc.terminate()
   proc.stdout.close()
  for rec in records.values():
   for kind in ('minute_source','daily_source'):
    if (rec['session'],kind) in sources:rec[kind]=sources[rec['session'],kind]
   if rec.get('minute_source') and not rec['prefixes']:
    h=digest(rec['symbol'].encode());rec['prefixes']={str(t):raw_prefix([],t) for t in clocks[h]}
    rec.update(activity(rec['active_minute_bitmap_hex']))
  return records,{'archive_sha256':expected,'opened_members':opened}
 all_rows={};source_by_date={};receipts=[]
 with ThreadPoolExecutor(max_workers=2) as pool:
  for records,receipt in pool.map(one,archives):
   receipts.append(receipt)
   for key,r in records.items():
    if key in all_rows:assert all_rows[key]==r,'CACHE_CONFLICT'
    all_rows[key]=r
    for k in ('minute_source','daily_source'):
     if k in r:source_by_date[r['session'],k]=r[k]
 for r in all_rows.values():
  for k in ('minute_source','daily_source'):
   if (r['session'],k) in source_by_date:r[k]=source_by_date[r['session'],k]
 out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
 # Fixed four date shards keep each reusable attachment below32 MiB.
 ordered=sorted(allowed);shards=[]
 for i in range(4):
  dates=set(ordered[i::4]);rr=[r for r in all_rows.values() if r['session'] in dates]
  data=gzip.compress((json.dumps(rr,sort_keys=True,separators=(',',':'))+'\n').encode(),mtime=0)
  name=f'MOVEMENT_SOURCE_PART_{i+1:02d}.json.gz';(out/name).write_bytes(data)
  assert len(data)<30*1024*1024,'SOURCE_SHARD_SIZE_LIMIT'
  shards.append({'filename':name,'sha256':digest(data),'bytes':len(data),'records_N':len(rr),'dates':sorted(dates)})
 report={'status':'SAVED_DEVELOPMENT_MOVEMENT_SOURCE_RECOVERED','scope_sha256':digest((HERE/'SOURCE_RECOVERY_SCOPE.json').read_bytes()),
  'shards':shards,'records_N':len(all_rows),'source_dates_N':len({r['session'] for r in all_rows.values()}),
  'archives':receipts,'protected_body_opened':0,'new_market_data':0,'provider_requests':0,'fits':0,'orders':0,
  'executionAllowed':False,'productionReady':False}
 (out/'MOVEMENT_SOURCE_RECEIPT.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k!='archives'}))

if __name__=='__main__':main()
