"""Deterministic append-only publication packages; no strategy execution."""
from pathlib import Path
import argparse,base64,gzip,hashlib,io,json,lzma,tarfile
R=Path(__file__).resolve().parent
def pin(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,sort_keys=True,indent=2,ensure_ascii=False)+'\n')
def package(label,files):
 dest=R/'publication'/label;dest.mkdir(parents=True,exist_ok=True);archive=dest/(label+'.tar.xz');manifest=[]
 with io.BytesIO() as f:
  with tarfile.open(fileobj=f,mode='w') as t:
   for p in sorted(files):
    b=p.read_bytes();name=str(p.relative_to(R));q=tarfile.TarInfo(name);q.size=len(b);q.mtime=0;q.mode=0o644;t.addfile(q,io.BytesIO(b));manifest.append({'path':name,**pin(b)})
  body=lzma.compress(f.getvalue(),preset=3)
 archive.write_bytes(body);parts=[]
 for index,start in enumerate(range(0,len(body),600000)):
  b=body[start:start+600000];p=dest/(label+f'.part-{index:03d}.bin');p.write_bytes(b);parts.append({'path':str(p.relative_to(R)),**pin(b)})
 x={'label':label,'archive':archive.name,**pin(body),'parts':parts,'members':manifest,'serialization':'Deterministic tar then XZ; concatenate numbered raw parts in order'};save(dest/(label+'_MANIFEST.json'),x);return x
def main():
 a=argparse.ArgumentParser();a.add_argument('label');args=a.parse_args();label=args.label
 if label=='SHARED_INPUTS':
  files=[p for p in (R/'native').rglob('*') if p.is_file() and p.suffix=='.py']
  files += [R/'inputs'/n for n in ['candidate_stream','books','arrival','split','core_runtime']]
  files += [p for p in (R/'inputs/frozen_models').glob('*.json')]
  files += [p for p in (R/'private/immutable').glob('*') if p.is_file()]
  files += [R/'inputs/STATE9_TRACE_ARCHIVE_BINDING.json',R/'ORIGINAL_EXTRACTION_RECEIPT.json',R/'NATIVE_STREAM_IDENTITY_RECEIPT.json',R/'STATE_ORIGINAL_PROJECTION_RECEIPT.json']
  files += [p for p in (R/'state_projection').glob('*.py')]
 elif label in [f'W{i:02}' for i in range(13,22)]+['CHAIN38']:
  files=[p for p in (R/'private/runs'/label).rglob('*') if p.is_file()]
  for arm in ['H1','H2']:
   result=json.loads((R/'private/runs'/label/arm/'RESULT.json').read_bytes())
   events=[e for d in result['daily_series'] for e in d['admission_state_events']]
   p=R/'private/runs'/label/arm/'STATE_EVENTS.jsonl.gz';p.write_bytes(gzip.compress((''.join(json.dumps(e,sort_keys=True,separators=(',',':'))+'\n' for e in events)).encode(),mtime=0));files.append(p)
 elif label=='FINAL_PRIVATE':
  files=[p for p in (R/'private').rglob('*') if p.is_file() and not any(q in p.parts for q in ['runs','reproduction','parity','immutable'])]
  files += [p for p in (R/'independent').rglob('*') if p.is_file()] if (R/'independent').exists() else []
 else:raise ValueError(label)
 x=package(label,files);print(json.dumps({'label':label,'bytes':x['bytes'],'part_N':len(x['parts']),'member_N':len(x['members'])}))
if __name__=='__main__':main()
