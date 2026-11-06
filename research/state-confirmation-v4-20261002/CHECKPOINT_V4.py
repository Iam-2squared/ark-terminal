from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,hashlib,sys
R=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
c,status,head,next_action=sys.argv[1:5]
assert c in ['C0','C1','C2','C3','C4','C5','C6'] and len(head)==40
p=R/'CHECKPOINTS'/f'{c}.json'
if p.exists():
 old=json.loads(p.read_text());assert c in ['C0','C2'],'NO_CHECKPOINT_OVERWRITE'
 (R/'CHECKPOINTS'/f'{c}_INITIAL_FIXATION.json').write_bytes(p.read_bytes())
x={'JST':datetime.now(timezone(timedelta(hours=9))).isoformat(),'current_status':status,'parent_HEAD':'c0e6968292f1a79c089a267d3f3a72cc1f7b5ead','current_HEAD':head,'contract_SHA256':sha(R/'PREDICTIVENESS_V4_CONTRACT.md'),'data_scope_SHA256':sha(R/'DATA_SCOPE_V4.json'),'precommit_SHA256':sha(R/'PREDICTIVENESS_V4_PRECOMMIT.json'),'next_action':next_action}
p.write_text(json.dumps(x,sort_keys=True,indent=2)+'\n');print(json.dumps(x))
