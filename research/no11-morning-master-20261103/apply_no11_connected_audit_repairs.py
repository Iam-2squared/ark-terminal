"""Maintainer-only deterministic source repairs. Never touches user PC data.

Run in a repository checkout. Only the listed Python sources/tests are edited.
Every production input is verified against the reviewed Git blob before edits.
This is not the PC installer and performs no RSS, Excel or brokerage activity.
"""
from pathlib import Path
import hashlib

ROOT=Path(__file__).resolve().parent
PINS={
 'no11_auto_minute_exclusion.py':'5c3c5e837b031e6df66ac94ae6e56c6eec7049b9',
 'no11_auto_minute_worker_transform.py':'1e7a2f91c99b05e1bacc696efab916056f1abdfd',
 'install_no11_auto_minutes_release.py':'36e96df82d3cd234b547ad84735a5b293d4448a6',
 'no11_nightly_resume_workeraware.py':'892477d57e0fe1dc6b1774b238fc01ea7d113ffc'}

def blob(raw):
 return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()

def once(text,a,b):
 assert text.count(a)==1,repr(a)
 return text.replace(a,b,1)

def source(name):
 raw=(ROOT/name).read_bytes()
 assert blob(raw)==PINS[name],(name,blob(raw))
 return raw.decode('utf-8')


def main():
 updates={}
 name='no11_auto_minute_exclusion.py';text=source(name)
 start=text.index('def hardlink_member(');end=text.index('\nNODE=',start)
 text=text[:start]+'''def hardlink_member(m,source,target,sha):
    # Compatibility name only: V2 writes an independent byte-identical copy.
    # An edit to a derived receipt can never alter the original source inode.
    raw=m.safe(source).read_bytes()
    need(digest(raw)==sha,'ORIGINAL_1M_RECEIPT_HASH')
    return save_once(m,Path(target),raw)
''' + text[end:]
 text=once(text,"      'schemaId':'ARK_NO11_AUTO_MINUTE_EXCLUSION_EVIDENCE_V1',",
   "      'schemaId':'ARK_NO11_AUTO_MINUTE_EXCLUSION_EVIDENCE_V1',\n      'independentSourceCopiesVersion':2,")
 text=text.replace('actual immutable progress files and read-only source hardlinks','actual immutable progress files and independent byte copies')
 updates[name]=text

 name='no11_nightly_resume_workeraware.py';text=source(name)
 text=once(text,"if($parentTime -gt $childTime){throw 'ANCESTOR_PID_REUSED'}",
   "if($parentTime -gt $childTime){break} # Not an ancestor: still scanned as an unrelated process below.")
 updates[name]=text

 name='no11_auto_minute_worker_transform.py';text=source(name)
 text=once(text,"MARK='ARK_NO11_AUTO_MINUTE_CAPTURE_ADOPTION_V1'",
   "MARK='ARK_NO11_AUTO_MINUTE_CAPTURE_ADOPTION_V1'\nVERSION_MARK='ARK_NO11_AUTO_MINUTE_CAPTURE_ADOPTION_V2'")
 text=once(text,'    # ARK_NO11_AUTO_MINUTE_CAPTURE_ADOPTION_V1',
   '    # ARK_NO11_AUTO_MINUTE_CAPTURE_ADOPTION_V1\n    # ARK_NO11_AUTO_MINUTE_CAPTURE_ADOPTION_V2')
 old="""        need(not dest.exists() and not dest.is_symlink(),
             'SAVED_LOG_COPY_COLLISION')
        os.link(oldlog,dest)
        need(digest(dest.read_bytes())==digest(raw),'SAVED_LOG_COPY_CHANGED')"""
 new="""        need(not dest.is_symlink(),'SAVED_LOG_COPY_REPARSE')
        if dest.exists():
            need(safe(dest).read_bytes()==raw,'SAVED_LOG_COPY_CHANGED')
        else:
            temp=None
            try:
                with tempfile.NamedTemporaryFile('wb',dir=pipe.work,
                        prefix='.saved-capture-',delete=False) as stream:
                    temp=Path(stream.name)
                    stream.write(raw);stream.flush();os.fsync(stream.fileno())
                try:
                    os.link(temp,dest)
                except FileExistsError:
                    need(safe(dest).read_bytes()==raw,'SAVED_LOG_COPY_CHANGED')
            finally:
                if temp is not None:temp.unlink(missing_ok=True)
        need(digest(dest.read_bytes())==digest(raw),'SAVED_LOG_COPY_CHANGED')"""
 text=once(text,old,new)
 text=once(text,'    adopt_prior_completed_capture(pipe)',
   "    with exclusive(work.parent / 'nightly.lock'):\n        no_workers()\n        adopt_prior_completed_capture(pipe)")
 at=text.index('def transform(raw,helper_sha):')
 text=text[:at]+'''def transform(raw,helper_sha):
    bom=raw.startswith(b'\\xef\\xbb\\xbf')
    text=raw.decode('utf-8-sig')
    newline='\\r\\n' if '\\r\\n' in text else '\\n'
    text=text.replace('\\r\\n','\\n')
    if VERSION_MARK in text:return raw
    match=re.findall(r"(?m)^    work = root / 'resumable-nightly' / \\(asof \\+ '_' \\+ target \\+ ('-(?:data-books-v1|auto-minutes-v1)-[a-f0-9]{16}')\\)$",text)
    if len(match)!=1 or not re.fullmatch(r'[a-f0-9]{64}',helper_sha) or 'ARK_NO11_CIRCUIT_AUDIT_V1' not in text:
        raise ValueError('NO11_AUTO_MINUTE_WORKER_SOURCE_NOT_BOUND')
    old_tag=match[0]
    old_line="    work = root / 'resumable-nightly' / (asof + '_' + target + "+old_tag+")"
    new_line="    work = root / 'resumable-nightly' / (asof + '_' + target + '-auto-minutes-v2-"+helper_sha[:16]+"')"
    text=text.replace(old_line,new_line,1)
    adopted="    legacy_work = root / 'resumable-nightly' / (asof + '_' + target + "+old_tag+")\\n"
    if MARK in text:
        a=text.index("    legacy_work = root / 'resumable-nightly'")
        b=text.index("    print('NO11_DAILY_CYCLE_SESSION=' + target)",a)
        text=text[:a]+adopted+ADOPT+'\\n'+text[b:]
    else:
        anchor='    Pipeline(work, identity, pointer, capture, publish, validate, no_workers).run()'
        if text.count(anchor)!=1:
            raise ValueError('NO11_AUTO_MINUTE_WORKER_ENTRY_CHANGED')
        text=text.replace(anchor,adopted+ADOPT,1)
    text=text.replace("if($parentTime -gt $childTime){throw 'ANCESTOR_PID_REUSED'}",
        "if($parentTime -gt $childTime){break} # Unrelated reused PID is not exempt from scanning.")
    compile(text,'no11_auto_minute_worker.py','exec')
    if text.count(VERSION_MARK)!=1:
        raise ValueError('NO11_AUTO_MINUTE_WORKER_GUARDS_CHANGED')
    return (b'\\xef\\xbb\\xbf' if bom else b'')+text.replace('\\n',newline).encode('utf-8')
'''
 updates[name]=text

 name='install_no11_auto_minutes_release.py';text=source(name)
 text=once(text,"KIND='ARK_NO11_AUTO_INVALID_MINUTE_ENTRY_EXCLUSION_RELEASE_V1'","KIND='ARK_NO11_AUTO_INVALID_MINUTE_ENTRY_EXCLUSION_RELEASE_V2'")
 text=once(text,"JOURNAL='auto-minute-exclusion-release-v1-transaction.json'","JOURNAL='auto-minute-exclusion-release-v2-transaction.json'")
 text=once(text,'previous_work_tag=re.findall(r"\'-data-books-v1-[a-f0-9]{16}\'",',
   'previous_work_tag=re.findall(r"(?m)^    work = root / \'resumable-nightly\' / \\(asof \\+ \'_\' \\+ target \\+ (\'-(?:data-books-v1|auto-minutes-v1)-[a-f0-9]{16}\')\\)$",')
 text=once(text,"    return first,latter\n\ndef apply(j):", """    if n.safe(j['bindingFile']).read_bytes()==after or j.get('phase')=='COMPLETE':
        for name,row in payload.items():
            need(n.digest(n.safe(Path(j['package'])/name).read_bytes())==row['sha256'],
                 'INSTALLED_PACKAGE_CHANGED')
    return first,latter

def apply(j):""")
 text=once(text,"        print('NO11_AUTO_MINUTE_SAVED_STAGE=BLOCKED|VERIFIED_RECEIPT_OR_PUBLIC_SOURCE',flush=True)",
   "        print('NO11_AUTO_MINUTE_SAVED_STAGE=BLOCKED|VERIFIED_RECEIPT_OR_PUBLIC_SOURCE',flush=True)\n        need(False,'SAVED_STAGE_FAILED')")
 updates[name]=text

 # Fixtures resolve the Linux interpreter symlink; production no-reparse
 # checks are not relaxed. The user's bound Windows executable is a file.
 name='test_no11_saved_replay_connected.py'
 text=(ROOT/name).read_text(encoding='utf-8')
 text=once(text,'self.f.binding.update(python=sys.executable,','self.f.binding.update(python=str(Path(sys.executable).resolve()),')
 updates[name]=text
 name='test_no11_auto_minutes_connected_audit.py'
 text=(ROOT/name).read_text(encoding='utf-8')
 anchor="        _,j=installer.install(fixture.store,HERE,True,True)\n        fail=subprocess.CompletedProcess"
 replacement="""        binding=n.read(fixture.binding)
        binding['python']=str(Path(sys.executable).resolve())
        fixture.binding.write_bytes(encode(binding))
        _,j=installer.install(fixture.store,HERE,True,True)
        fail=subprocess.CompletedProcess"""
 text=once(text,anchor,replacement)
 updates[name]=text
 for name,text in updates.items():compile(text,name,'exec')
 for name,text in updates.items():
    (ROOT/name).write_text(text,encoding='utf-8',newline='\n')
    print('AUDIT_SOURCE_REPAIR='+name)

if __name__=='__main__':main()
