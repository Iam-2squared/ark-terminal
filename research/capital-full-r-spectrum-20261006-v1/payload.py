"""Prepare only this cycle's public paths for authorized GitHub checkpoints."""
from pathlib import Path
import argparse, base64, hashlib, json
REPO=Path(__file__).resolve().parents[2]
FOLDERS=[REPO/'docs/evidence/capital-full-r-spectrum-20261006-v1',Path(__file__).resolve().parent]
def inventory():
    out=[]
    for folder in FOLDERS:
        for p in sorted(folder.rglob('*')):
            if not p.is_file() or '__pycache__' in p.parts:continue
            assert p.suffix in ['.json','.jsonl','.md','.csv','.py','.png'],p
            b=p.read_bytes(); enc='base64' if p.suffix=='.png' else 'utf-8'
            out.append({'path':p.relative_to(REPO).as_posix(),'bytes':len(b),
                'chars':4*((len(b)+2)//3) if enc=='base64' else len(b.decode('utf-8')),
                'encoding':enc,'blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(),
                'sha256':hashlib.sha256(b).hexdigest()})
    return out
if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('mode',choices=['inventory','chunk'])
    parser.add_argument('path',nargs='?');parser.add_argument('offset',type=int,nargs='?',default=0)
    parser.add_argument('count',type=int,nargs='?',default=8500);a=parser.parse_args()
    if a.mode=='inventory':print(json.dumps(inventory()))
    else:
        p=(REPO/a.path).resolve();assert any(p.is_relative_to(d) for d in FOLDERS)
        b=p.read_bytes();s=base64.b64encode(b).decode() if p.suffix=='.png' else b.decode('utf-8')
        print(json.dumps(s[a.offset:a.offset+a.count],ensure_ascii=False))
