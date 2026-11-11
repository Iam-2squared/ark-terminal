"""Install-safe patch: real two-session log parser + automatic small 1M drop.

The exact pinned existing morning/data/Trade verifiers remain unchanged.
Only the DATA cycle's log parse and pre-publication source selection change.
"""
from __future__ import annotations
import re
import no11_combined_nightly_parser as dual

MARK='ARK_NO11_AUTO_MINUTE_PRUNE_BOUND_DATA_CYCLE_V1'
ANCHOR='    m=native_module("ark_pinned_morning",binding["runner"])\n    prepared,selected,cb,mb,sb=verified_sources(m,record,hand_seed)'
INSERT='''    m=native_module("ark_pinned_morning",binding["runner"])
    # ARK_NO11_AUTO_MINUTE_PRUNE_BOUND_DATA_CYCLE_V1
    # A few bad entry-only 1M sources are skipped; never override protected
    # EXIT symbols, chart validation, source hashes or human review.
    tool=safe(Path(__file__).with_name("no11_auto_minute_exclusion.py"))
    need(digest(tool.read_bytes()) == binding.get("autoMinuteExclusionToolSha256"),
         "AUTO_MINUTE_EXCLUSION_TOOL_CHANGED")
    helper=native_module("ark_no11_auto_minute_exclusion_bound",tool)
    record=helper.prune(m,record,root,binding,previous_checkpoint)
    prepared,selected,cb,mb,sb=verified_sources(m,record,hand_seed)'''

def transform(raw):
    original=raw.decode('utf-8-sig')
    if MARK in original:
        return raw
    if dual.MARK not in original:
        raw=dual.transform(raw)
    bom=raw.startswith(b'\xef\xbb\xbf')
    source=raw.decode('utf-8-sig')
    newline='\r\n' if '\r\n' in source else '\n'
    text=source.replace('\r\n','\n')
    if text.count(ANCHOR)!=1 or 'NO11_DAILY_CYCLE_PREVIOUS_MINUTES_INCOMPLETE' in text:
        raise ValueError('NO11_AUTO_MINUTE_CYCLE_SOURCE_CONTEXT_INVALID')
    text=text.replace(ANCHOR,INSERT,1)
    if text.count(MARK)!=1 or 'not stage.get("omittedSymbols")' not in text:
        raise ValueError('NO11_AUTO_MINUTE_FROZEN_GUARDS_CHANGED')
    compile(text,'auto_minute_patched_daily_cycle.py','exec')
    return (b'\xef\xbb\xbf' if bom else b'')+text.replace('\n',newline).encode('utf-8')
