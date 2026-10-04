"""Byte-preserving chunked transport; identical append-only publication rules."""
from common import *
def main():
 remote=json.loads(STATE.read_text());known=remote['published_paths'];entries=[]
 prefix=(WORK/'v6_published_status_prefix.txt').read_bytes() if (WORK/'v6_published_status_prefix.txt').exists() else remote['published_status_prefix'].encode()
 remote={k:v for k,v in remote.items() if k!='published_status_prefix'}
 for top in (CODE,OUT):
  for p in sorted(top.rglob('*')):
   if not p.is_file() or '__pycache__' in p.parts:continue
   path=p.relative_to(ROOT).as_posix();data=p.read_bytes();digest=sha(p)
   if path in known:
    if known[path]==digest:continue
    assert p.name=='WORK_STATUS_LOG.jsonl' and data.startswith(prefix),('APPEND_ONLY_VIOLATION',path)
   entries.append({'path':path,'mode':'100644','type':'blob','content':data.decode('utf8')})
 assert entries
 status_bytes=(OUT/'WORK_STATUS_LOG.jsonl').read_bytes()
 payload={'state':remote,'entries':entries,'hashes':{e['path']:sha(ROOT/e['path']) for e in entries},'status_bytes':len(status_bytes),'status_sha256':hashlib.sha256(status_bytes).hexdigest()}
 target=WORK/'v6_publication_payload_transport.json';target.write_text(json.dumps(payload,ensure_ascii=False))
 print(json.dumps({'characters':len(target.read_text()),'file':str(target),'entries':len(entries)}))
if __name__=='__main__':main()
