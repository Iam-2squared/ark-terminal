"""Preserves all published bytes; only WORK_STATUS_LOG can grow by exact prefix."""
from common import *
def main():
 remote=json.loads(STATE.read_text());known=remote['published_paths'];entries=[]
 for top in (CODE,OUT):
  for p in sorted(top.rglob('*')):
   if not p.is_file() or '__pycache__' in p.parts:continue
   path=p.relative_to(ROOT).as_posix();content=p.read_bytes().decode('utf8');digest=sha(p)
   if path in known:
    if known[path]==digest:continue
    assert p.name=='WORK_STATUS_LOG.jsonl' and content.startswith(remote['published_status_prefix']),('APPEND_ONLY_VIOLATION',path)
   entries.append({'path':path,'mode':'100644','type':'blob','content':content})
 assert entries,'NO_NEW_EVIDENCE'
 print(json.dumps({'state':remote,'entries':entries,'hashes':{e['path']:sha(ROOT/e['path']) for e in entries},'status_prefix':(OUT/'WORK_STATUS_LOG.jsonl').read_bytes().decode('utf8')}))
if __name__=='__main__':main()
