"""Canonical numerical replay audit; exact identities, tolerant float roundoff only."""
import argparse,math
from pathlib import Path
from scripts import phase57_comprehensive_entry as m

def equal(a,b,path='root'):
 if isinstance(a,float) or isinstance(b,float):
  assert isinstance(a,(int,float)) and isinstance(b,(int,float)) and math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-10),(path,a,b)
 elif isinstance(a,dict):
  assert isinstance(b,dict) and a.keys()==b.keys(),path
  for k in a:
   if path.endswith('runtime') and k=='python':continue
   equal(a[k],b[k],path+'.'+k)
 elif isinstance(a,list):
  assert isinstance(b,list) and len(a)==len(b),path
  for i,(x,y) in enumerate(zip(a,b)):equal(x,y,path+f'[{i}]')
 else:assert a==b,(path,a,b)

def verify(saved,regen):
 saved=Path(saved);regen=Path(regen);files=[]
 for p in sorted(saved.iterdir()):
  r=regen/p.name
  if p.name=='manifest.json':
   manifest=m.read(p)
   for n,h in manifest.get('outputs',manifest.get('outputPins',{})).items():assert m.sha(saved/n)==h,(n,'SAVED_HASH')
   other=m.read(r)
   for n,h in other.get('outputs',other.get('outputPins',{})).items():assert m.sha(regen/n)==h,(n,'REGENERATED_HASH')
   continue
  if '.json' in p.name:equal(m.read(p),m.read(r),p.name)
  else:assert p.read_bytes()==r.read_bytes(),p.name
  files.append(p.name)
 return files
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--saved',required=True);p.add_argument('--regen',required=True);a=p.parse_args();print(verify(a.saved,a.regen))
