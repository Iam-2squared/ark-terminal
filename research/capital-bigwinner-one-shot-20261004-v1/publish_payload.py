"""Export staged public text for the authenticated GitHub Git-data route."""
import json
import sys
import subprocess
from checkpoint import ROOT, git

label,message=sys.argv[1:3]
files=git('diff','--cached','--name-status').splitlines()
elements=[]
for item in files:
    status,path=item.split('\t')
    assert status in ('A','M'), 'APPEND_ONLY_NO_DELETE'
    assert (path.startswith('research/capital-bigwinner-one-shot-20261004-v1/')
            or path.startswith('docs/evidence/capital-bigwinner-one-shot-20261004-v1/')
            or path=='.github/workflows/capital-bigwinner-saved-source-20261004.yml')
    assert not any(x in path.upper() for x in ('PRIVATE','JSONL','RAW_PATH','NPY','NPZ'))
    content=subprocess.check_output(['git','show',':'+path],cwd=ROOT).decode('utf-8')
    elements.append({'path':path,'mode':'100644','type':'blob','content':content})
print(json.dumps({'label':label,'parent':git('rev-parse','HEAD'),
    'base_tree':git('rev-parse','HEAD^{tree}'),'local_tree':git('write-tree'),
    'message':message,'elements':elements}))
