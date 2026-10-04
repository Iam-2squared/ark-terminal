"""Produce only new append-only paths; reject mutation of any published local file."""
from common import *
def main():
 remote=json.loads((WORK/'remote_state.json').read_text());known=remote['published_paths'];entries=[]
 for top in (CODE,OUT):
  for p in sorted(top.rglob('*')):
   if not p.is_file() or '__pycache__' in p.parts:continue
   name=p.relative_to(ROOT).as_posix();digest=sha(p)
   if name in known:assert known[name]==digest,('APPEND_ONLY_VIOLATION',name);continue
   entries.append({'path':name,'mode':'100644','type':'blob','content':p.read_text()})
 assert entries
 print(json.dumps({'state':remote,'entries':entries,'hashes':{e['path']:sha(ROOT/e['path']) for e in entries}}))
if __name__=='__main__':main()
