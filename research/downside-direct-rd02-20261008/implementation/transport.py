"""Prepare deterministic checkpoint carriers. GitHub transport is connector-only."""
import sys,os,tarfile,io,lzma,base64
from common import *

def prepare(stage,private_roots):
 td=WORK/'transport'/stage;td.mkdir(parents=True,exist_ok=True);prefix='research/downside-direct-rd02-20261008/'
 previous=read(WORK/'transport/LAST_LOCAL_PINS.json') if (WORK/'transport/LAST_LOCAL_PINS.json').exists() else {}
 pubs=[]
 for root in [PUB,WORK/'implementation']:
  for p in sorted(root.rglob('*')):
   if not p.is_file() or '__pycache__' in str(p) or p.suffix=='.pyc':continue
   rel=p.relative_to(WORK).as_posix();rel=rel[7:] if rel.startswith('public/') else rel
   if previous.get(rel)==pin(p):continue
   b=p.read_bytes();pubs.append({'path':prefix+rel,'local':str(p),'encoding':'utf-8','content':b.decode(),**pin(p)})
 archive=None;prvs=[]
 if private_roots:
  names=[]
  for root in private_roots:
   p=PRIVATE/root
   names.extend(q for q in (sorted(p.rglob('*')) if p.is_dir() else [p]) if q.is_file())
  names=sorted(set(names));buf=io.BytesIO()
  with tarfile.open(fileobj=buf,mode='w',format=tarfile.PAX_FORMAT) as t:
   for p in names:
    b=p.read_bytes();info=tarfile.TarInfo(p.relative_to(PRIVATE).as_posix());info.size=len(b);info.mtime=0;info.mode=0o600;info.uid=info.gid=0;t.addfile(info,io.BytesIO(b))
  payload=lzma.compress(buf.getvalue(),preset=6);archive=td/(stage+'.tar.xz');archive.write_bytes(payload);parts=[]
  for i,start in enumerate(range(0,len(payload),600000),1):
   part=td/f'{stage}.tar.xz.part{i:03d}';part.write_bytes(payload[start:start+600000]);info={'path':prefix+'checkpoints/'+stage+'/'+part.name,'local':str(part),'encoding':'base64','content':base64.b64encode(part.read_bytes()).decode(),**pin(part)};parts.append({k:v for k,v in info.items() if k!='content'});prvs.append(info)
  manifest={'stage':stage,'archive':archive.name,'archive_pin':pin(archive),'parts':parts,'members':[{'path':p.relative_to(PRIVATE).as_posix(),**pin(p)} for p in names],'source_carrier_repeated':False}
  mf=td/'PRIVATE_CARRIER_MANIFEST.json';save(mf,manifest);prvs.append({'path':prefix+'checkpoints/'+stage+'/PRIVATE_CARRIER_MANIFEST.json','local':str(mf),'encoding':'utf-8','content':mf.read_text(),**pin(mf)})
 assets={'stage':stage,'public':pubs,'private':prvs}
 save(td/'assets.json',assets)
 print(json.dumps({'stage':stage,'public_files':len(pubs),'private_parts':len(prvs)-bool(prvs),'private_bytes':archive.stat().st_size if archive else 0,'assets':str(td/'assets.json')}))

def done(stage):
 prev=read(WORK/'transport/LAST_LOCAL_PINS.json') if (WORK/'transport/LAST_LOCAL_PINS.json').exists() else {}
 a=read(WORK/'transport'/stage/'assets.json')
 for r in a['public']:
  rel=r['path'].removeprefix('research/downside-direct-rd02-20261008/');prev[rel]={k:r[k] for k in ['bytes','sha256','git_blob']}
 save(WORK/'transport/LAST_LOCAL_PINS.json',prev)

if __name__=='__main__':
 if sys.argv[1]=='prepare':prepare(sys.argv[2],sys.argv[3:])
 else:done(sys.argv[2])
