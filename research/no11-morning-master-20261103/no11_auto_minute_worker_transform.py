"""Safe capture-stage adoption when Friday and Monday completed but parser failed.

Old logs/checkpoints remain immutable. A separately versioned DATA worker adopts
one SHA-verified *completed* log and proceeds directly to 1M exclusion and
morning handoff, without recollecting 4,328 or 142 RSS symbols.

No adoption of an incomplete native child, unknown date, changed engine source,
live/EXIT worker, or already running capture.
"""
from __future__ import annotations

import re

MARK='ARK_NO11_AUTO_MINUTE_CAPTURE_ADOPTION_V1'

ADOPT=r'''    # ARK_NO11_AUTO_MINUTE_CAPTURE_ADOPTION_V1
    # A prior DATA capture can end cleanly while the old parser rejects the
    # genuine two-session log. Preserve its old CAPTURING checkpoint and bytes.
    # ONLY adopt once, after full manifest/code/clock/source validation.
    def adopt_prior_completed_capture(pipe):
        if pipe.state_file.exists() or pointer.exists() or not legacy_work.exists():
            return
        old_state_file=legacy_work / 'checkpoint.json'
        if not old_state_file.is_file():
            return
        old_state=checkpoint(old_state_file)
        if old_state.get('phase') not in ('CAPTURING','CAPTURED','PUBLISHING'):
            return
        old_id=old_state.get('identity',{})
        need(old_state.get('orderTransmission') is False and
             old_id.get('asOfSession')==asof and
             old_id.get('sessionDate')==target and
             old_id.get('mode')==identity['mode'] and
             old_id.get('symbolsSha256')==identity['symbolsSha256'] and
             old_id.get('engine')==identity['engine'] and
             old_id.get('orderTransmission') is False,
             'SAVED_CAPTURE_SCOPE_CHANGED')
        before=old_id.get('pins',{})
        after=identity.get('pins',{})
        need(type(before) is dict and set(before)==set(after) and
             all(before.get(key)==value for key,value in after.items()
                 if key!='dailyCycleTool'),
             'SAVED_CAPTURE_ENGINE_PINS_CHANGED')
        name=old_state.get('captureLog') or old_state.get('attemptLog')
        need(type(name) is str and re.fullmatch(r'capture-[a-f0-9]{32}\.log',name),
             'SAVED_CAPTURE_LOG_NAME')
        oldlog=safe(legacy_work / name)
        raw=oldlog.read_bytes()
        need(0<len(raw)<20_000_000,'SAVED_CAPTURE_LOG_SIZE')
        if old_state.get('captureSha256') is not None:
            need(digest(raw)==old_state['captureSha256'],
                 'SAVED_CAPTURE_LOG_DIGEST_CHANGED')
        parsed=daily.parse_nightly(raw)
        need(parsed['sessionDate']==target and parsed['previousSession']==asof and
             parsed['nightlyMode'] in (
               'CANDIDATE_ONLY_FRESH_G1_AND_PREVIOUS_COMPLETE',
               'FRIDAY_FULL_UNIVERSE_AND_PREVIOUS_COMPLETE'),
             'SAVED_CAPTURE_FINAL_SESSION_WRONG')
        # If an unknown or partial source exists, the strict data stage later
        # rejects it. Never mark an archived partial wave as completed.
        no_workers()
        dest=pipe.work / name
        need(not dest.exists() and not dest.is_symlink(),
             'SAVED_LOG_COPY_COLLISION')
        os.link(oldlog,dest)
        need(digest(dest.read_bytes())==digest(raw),'SAVED_LOG_COPY_CHANGED')
        pipe.save({'schemaId':SCHEMA,
                   'identitySha256':digest(encode(identity)),
                   'identity':identity,'orderTransmission':False},
                  phase='CAPTURED',captureLog=name,captureSha256=digest(raw))
        print('NO11_AUTO_MINUTE_REUSED_VERIFIED_SAVED_CAPTURE=True',flush=True)
        print('NO11_AUTO_MINUTE_RSS_RECAPTURED=False',flush=True)
    pipe=Pipeline(work, identity, pointer, capture, publish, validate, no_workers)
    adopt_prior_completed_capture(pipe)
    if os.environ.get('ARK_AUTO_MINUTE_RESUME_ONLY')=='1':
        need(pipe.state_file.is_file() and
             checkpoint(pipe.state_file).get('phase') in ('CAPTURED','PUBLISHING','COMPLETE'),
             'SAVED_CAPTURE_NOT_VERIFIED_NO_RECAPTURE')
    pipe.run()
'''

def transform(raw,helper_sha):
    bom=raw.startswith(b'\xef\xbb\xbf')
    text=raw.decode('utf-8-sig')
    newline='\r\n' if '\r\n' in text else '\n'
    text=text.replace('\r\n','\n')
    if MARK in text:return raw
    match=re.findall(r"'-data-books-v1-[a-f0-9]{16}'",text)
    if len(match)!=1 or len(helper_sha)!=64 or 'ARK_NO11_CIRCUIT_AUDIT_V1' not in text:
        raise ValueError('NO11_AUTO_MINUTE_WORKER_SOURCE_NOT_BOUND')
    old_tag=match[0]
    new_tag="'-auto-minutes-v1-"+helper_sha[:16]+"'"
    text=text.replace(old_tag,new_tag,1)
    anchor='    Pipeline(work, identity, pointer, capture, publish, validate, no_workers).run()'
    if text.count(anchor)!=1:
        raise ValueError('NO11_AUTO_MINUTE_WORKER_ENTRY_CHANGED')
    adopted=("    legacy_work = root / 'resumable-nightly' / "
             "(asof + '_' + target + "+old_tag+")\n")
    text=text.replace(anchor,adopted+ADOPT,1)
    compile(text,'no11_auto_minute_worker.py','exec')
    if text.count(MARK)!=1 or 'no_workers()' not in ADOPT:
        raise ValueError('NO11_AUTO_MINUTE_WORKER_GUARDS_CHANGED')
    return (b'\xef\xbb\xbf' if bom else b'')+text.replace('\n',newline).encode('utf-8')
