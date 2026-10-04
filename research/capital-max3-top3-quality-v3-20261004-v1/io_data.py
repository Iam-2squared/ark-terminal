"""Read immutable existing CORE score and source artifacts; no model fit."""
from pathlib import Path
import gzip,json
from checkpoint import ROOT,PRIVATE,V2
def rows(path):return [json.loads(s) for s in gzip.open(path,'rt')]
def gzwrite(path,values):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 data=gzip.compress(('\n'.join(json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False) for r in values)+'\n').encode(),mtime=0)
 with path.open('xb') as f:f.write(data)
def books():return {r['entry_id']:r for r in rows(ROOT.parent/'bigwinner_private/MARKET_EXECUTION_BOOK_V2.jsonl.gz')}
def stream():return rows(PRIVATE/'QUALITY_V3_SCORE_STREAM.jsonl.gz')
