"""Current-slot request/response worker. No raw/future/label paths or key env."""
import json,sys
from pathlib import Path
from candidate.api import Engine
engine=Engine(json.loads(Path('profile.json').read_text()))
for line in sys.stdin:
 x=json.loads(line)
 assert x['raw'] is None or x['raw']['t']==x['t'] and x['raw']['known_at']<=x['t']
 result=engine.step(x['t'],x['raw'],x['case_id'])
 print(json.dumps(result,sort_keys=True,separators=(',',':')),flush=True)
