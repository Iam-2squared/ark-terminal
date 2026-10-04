import json,sys
from common import *
state=json.loads((WORK/'rank_cutoff_publish_state.json').read_text())
if sys.argv[1]=='payload':
 files=[];elements=[]
 for base in (OUT,CODE):
  for p in sorted(base.rglob('*')):
   if not p.is_file() or '__pycache__' in p.parts:continue
   rel=p.relative_to(ROOT).as_posix();digest=sha(p)
   if rel in state['sent']:
    assert state['sent'][rel]==digest,('APPEND_ONLY_OVERWRITE_FORBIDDEN',rel)
    continue
   elements.append({'path':rel,'mode':'100644','type':'blob','content':p.read_text()});files.append({'path':rel,'sha256':digest})
 print(json.dumps({'tree_elements':elements,'files':files},ensure_ascii=False))
else:
 x=json.load(sys.stdin);save(OUT/'receipts'/f"{x['receipt']['checkpoint']}.json",x['receipt'])
 state['remote']=x['remote'];state['sent'].update({f['path']:f['sha256'] for f in x['published']})
 (WORK/'rank_cutoff_publish_state.json').write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'actual_GET_receipt_saved':x['receipt']['result_HEAD']}))
