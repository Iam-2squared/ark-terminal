from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import gzip,hashlib,json

REPO=Path(__file__).resolve().parents[2]
ROOT=REPO.parent
INPUTS=ROOT/'sources/resolved'
OUT=REPO/'docs/evidence/capital-v51-reset20-r5r10-20261006-v1'
PRIVATE=ROOT/'capital_v51_private'

def now():return datetime.now(ZoneInfo('Asia/Tokyo')).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def rows(p):return [json.loads(s) for s in gzip.open(p,'rt') if s.strip()]
def save(p,obj):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n')
def write_rows(p,obj):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes(gzip.compress(('\n'.join(json.dumps(x,sort_keys=True,allow_nan=False) for x in obj)+'\n').encode(),mtime=0))
def checkpoint(event,status,next_step,counts,details=None):
    obj={'exact_jst':now(),'event':event,'status':status,'next':next_step,'counts':counts,'details':details or {},'productionReady':False}
    save(OUT/'checkpoints'/f'{event}.json',obj)
    with (OUT/'WORK_STATUS_LOG.jsonl').open('a') as f:f.write(json.dumps(obj,ensure_ascii=False)+'\n')
