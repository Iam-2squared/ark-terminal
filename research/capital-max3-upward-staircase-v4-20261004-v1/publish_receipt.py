"""Persist only actual returned postcommit GET identities."""
import sys,json
from common import *
x=json.load(sys.stdin);r=x['receipt'];save(OUT/'receipts'/f"{r['checkpoint']}.json",r)
state=json.loads((WORK/'publish_state.json').read_text());state['remote']=x['remote']
for f in x['published']:state['sent'][f['path']]=f['sha256']
(WORK/'publish_state.json').write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
print(json.dumps({'actual_GET_receipt_saved':r['result_HEAD']}))
