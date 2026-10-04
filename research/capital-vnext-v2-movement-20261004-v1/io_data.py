"""Private I/O separated from runtime funding and evaluation teachers."""
from pathlib import Path
import gzip,json
from checkpoint import ROOT,PRIVATE

def rows(path):return [json.loads(s) for s in gzip.open(path,'rt')]
def gzwrite(path,values):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 data=gzip.compress(('\n'.join(json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False) for r in values)+'\n').encode(),mtime=0)
 with path.open('xb') as f:f.write(data)

def books():return {r['entry_id']:r for r in rows(ROOT.parent/'bigwinner_private/MARKET_EXECUTION_BOOK_V2.jsonl.gz')}
def core_runtime():return rows(ROOT.parent/'bigwinner_private/RUNTIME_CAUSAL.jsonl.gz')
def calendar():
 s=json.loads((ROOT/'research/capital-bigwinner-one-shot-20261004-v1/SOURCE_RECOVERY_SCOPE.json').read_text())
 return sorted(set(s['required_prior_dates']+s['entry_cohort_dates']))

def history():
 directory=ROOT.parent/'work_inputs/movement_v2_source'
 receipt=json.loads((directory/'MOVEMENT_SOURCE_RECEIPT.json').read_text())
 from checkpoint import sha
 assert receipt['protected_body_opened']==0 and receipt['provider_requests']==0
 result={}
 for part in receipt['shards']:
  path=directory/part['filename'];assert sha(path)==part['sha256']
  rr=json.load(gzip.open(path,'rt'));assert len(rr)==part['records_N']
  for r in rr:
   key=(r['session'],r['symbol']);assert key not in result
   result[key]=r
 assert len(result)==receipt['records_N']
 return result,receipt
