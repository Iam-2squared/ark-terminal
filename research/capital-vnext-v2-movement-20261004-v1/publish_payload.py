"""Public Git tree export; preserve exact UTF8 bytes including CSV newlines."""
import json,subprocess,sys
from checkpoint import ROOT,OUT,NAME,git
label,message=sys.argv[1:3]
elements=[]
for item in git('diff','--cached','--name-status').splitlines():
 status,path=item.split('\t')
 assert status in ('A','M')
 assert path.startswith(('research/'+NAME+'/','docs/evidence/'+NAME+'/')) or path=='.github/workflows/capital-vnext-v2-movement-source-20261004.yml'
 assert not any(s in path.upper() for s in ('PRIVATE','JSONL','RAW_PATH','NPY','NPZ'))
 content=subprocess.check_output(['git','show',':'+path],cwd=ROOT).decode('utf8')
 elements.append({'path':path,'mode':'100644','type':'blob','content':content})
assert elements
print(json.dumps({'label':label,'parent':git('rev-parse','HEAD'),'base_tree':git('rev-parse','HEAD^{tree}'),
 'local_tree':git('write-tree'),'message':message,'elements':elements}))
