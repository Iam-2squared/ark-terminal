"""Stage-scoped append-only publisher; bytes already published are immutable."""
from common import *
import sys,re
def main():
 stage=int(sys.argv[1]);remote=json.loads((WORK/'remote_state.json').read_text());known=remote['published_paths'];entries=[]
 minima={'ARRIVAL_TABLE.json':3,'POLICY_PRECOMMIT.json':3,'CAUSAL_CANARY_RESULTS.json':4,'MAIN_REPLAY_RESULT.json':5,'SLOT_QUALITY_AND_RESERVATION.json':6,'OPPORTUNITY_AND_ORACLE_GAP.json':7,'INDEPENDENT_AUDIT.json':8,'INDEPENDENT_ORACLE_AUDIT.json':8,'DETERMINISTIC_RERUN.json':8,'REPORT_FINAL-ja.md':9,'CLOSURE.json':10}
 for top in (CODE,OUT):
  for p in sorted(top.rglob('*')):
   if not p.is_file() or '__pycache__' in p.parts:continue
   name=p.relative_to(ROOT).as_posix();digest=sha(p)
   if name in known:assert known[name]==digest,('APPEND_ONLY_VIOLATION',name);continue
   if top==CODE and stage<3 and p.name not in ('oracle_v2.py','publish_payload_v2.py'):continue
   if top==OUT:
    if 'checkpoints' in p.parts:
     n=int(re.match(r'V(\d+)_',p.name).group(1))
     if n>stage:continue
    elif 'receipts' not in p.parts and minima.get(p.name,0)>stage:continue
   entries.append({'path':name,'mode':'100644','type':'blob','content':p.read_text()})
 assert entries
 print(json.dumps({'state':remote,'entries':entries,'hashes':{e['path']:sha(ROOT/e['path']) for e in entries}}))
if __name__=='__main__':main()
