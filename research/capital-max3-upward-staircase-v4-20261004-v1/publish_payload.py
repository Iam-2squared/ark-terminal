"""Export only new files under the two authorized append-only paths."""
import json,sys
from common import *
state=json.loads((WORK/'publish_state.json').read_text());sent=state['sent'];files=[];elements=[]
assert (OUT/'checkpoints'/f'{sys.argv[1]}.json').exists()
for base in (OUT,CODE):
 for p in sorted(base.rglob('*')):
  if not p.is_file() or '__pycache__' in p.parts:continue
  rel=p.relative_to(ROOT).as_posix();digest=sha(p)
  if rel in sent:
   assert sent[rel]==digest,('APPEND_ONLY_OVERWRITE_FORBIDDEN',rel)
   continue
  elements.append({'path':rel,'mode':'100644','type':'blob','content':p.read_text()});files.append({'path':rel,'sha256':digest})
assert elements
print(json.dumps({'tree_elements':elements,'files':files},ensure_ascii=False))
