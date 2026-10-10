"""Immutable G-admission bridge. Identity/reporting metadata is not a State feature."""
from __future__ import annotations
import hashlib, importlib.util, sys
from pathlib import Path
from .common import ROOT, r, F, digest
G_SHA='5955f2d8420debfd135913e33c3be0f316fca0c18c9b86977a868672b7107a29'
p=ROOT/'docs/evidence/phase57-five-minute-reference-g-v1/generate_reference.py'
if hashlib.sha256(p.read_bytes()).hexdigest()!=G_SHA:raise RuntimeError('G_ADMISSION_SOURCE_CHANGED')
sp=importlib.util.spec_from_file_location('phase57_state_v2_g_admission',p)
g=importlib.util.module_from_spec(sp);sys.modules[sp.name]=g;sp.loader.exec_module(g)
# G validates all its source pins before its instance is shared with v2.
g.load_ref(ROOT/'docs/phase57-five-minute-entry-state/mechanical-v1')
g._r=r
VINTAGE='G_FIXED_DEV_2155_INPUTS_V1_20260921'

def admit(source_root, out):
    return g.admission(g.source_paths(ROOT,source_root),Path(out))

def split_task(task):
    """Whitelist explicitly; origin score/rank, old Entry and outcomes are absent."""
    identity={'opportunityId':task['id'],'sessionDate':task['session'],
              'securityId':task['symbol'],'selectorAt':task['selectorAt']}
    context={k:task[k] for k in ('previous','previousDay','previousBasis','previousContext',
             'scale','dailyRows','dailyReasons','sourceHashes','quality','calendar')}
    context['basis']=g.BASIS
    context['sourceVintageId']=VINTAGE
    context['previousCoverage']=F(len(task['previous']),len(g.ends_for(task['previousDay'])))
    return identity,context

def prefix_at(bars,t):
    # Router sees event metadata, not prices. Known-at violations are deliberately
    # NOT filtered here: the NOW reader must fail rather than silently discard them.
    return tuple(b for b in bars if b.end<=t)

# Only these exact stored byte hashes can be mechanically restored. No generic
# whitespace normalization, pin replacement, or acceptance of a mismatching spec.
PIN_RECOVERY={
 'docs/phase57-five-minute-entry-state/STATE_DEFINITION_v2_FREEZE_CANDIDATE.md':('aa490daeee40dc33a48dd030944dc6f31a36179caa525641eeeeb11bbd2c8f42','d2747332abd6a47f84cabebadde05f02c2fe1717e12d3a12891a3640a2e50068'),
 'docs/evidence/phase57-state-v2-hardening/HARDENING_EVIDENCE.md':('e1706de69e5f3129af62cab597326cff910a164a0691d36268fb8ebfc6d4d5f9','5aa8349cbb774e4fcd866697d4a2f8585ab18e9a8883a98337e9f841c7a5bddb')}

def verify_spec(out):
    receipts=[]
    for rel,(stored,wanted) in PIN_RECOVERY.items():
        b=(ROOT/rel).read_bytes();h=hashlib.sha256(b).hexdigest()
        fixed=b if h==wanted else b+b'\n' if h==stored else None
        if fixed is None or hashlib.sha256(fixed).hexdigest()!=wanted:raise ValueError('FROZEN_PIN_UNRECOVERABLE:'+rel)
        dest=Path(out)/Path(rel).name
        dest.write_bytes(fixed)
        receipts.append({'path':rel,'storageSHA256':h,'effectiveSHA256':wanted,'operation':'NONE' if b==fixed else 'RESTORE_EXACTLY_ONE_TERMINAL_LF','effectiveByteN':len(fixed),'semanticChange':False,'originalsIndependentlyRecoveredFromLibrary':True})
    return receipts
