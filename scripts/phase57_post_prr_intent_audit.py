"""Verify append-only R50 decision-time classification correction."""
from __future__ import annotations

from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/evidence/phase57-post-prr-phase-a'
SUMMARY=ROOT/'docs/evidence/phase57-checkpoint-certified-guard-exit/CHECKPOINT_ENTRY_SUMMARY.jsonl.gz'


def rows(path):
    with gzip.open(path,'rt') as f:return [json.loads(line) for line in f]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source={(r['arm'],r['entryId']):r for r in rows(SUMMARY)}
    before=rows(OUT/'COMPARISON_MASK_ROWS.jsonl.gz')
    after=rows(OUT/'COMPARISON_MASK_ROWS_INTENT_V2.jsonl.gz')
    receipt=json.loads((OUT/'A0_INTENT_SEMANTICS_CORRECTION.json').read_text())
    assert len(source)==1614 and len(before)==len(after)==1725
    assert sha(OUT/'A0_CENSUS.json')==receipt['oldA0Sha256']
    assert sha(OUT/'COMPARISON_MASK_ROWS_INTENT_V2.jsonl.gz')==receipt['newMaskSha256']
    for old,new in zip(before,after):
        assert (old['world'],old['arm'],old['entryId'])==(
            new['world'],new['arm'],new['entryId'])
        ref=source[(new['arm'],new['entryId'])]
        control,ccmg=ref['controlNow'],ref['firstSellIntent']
        assert control is not None
        order=('UNKNOWN_NO_CCMG_INTENT' if ccmg is None else
               'CCMG_FIRST' if ccmg<control else
               'R50_FIRST' if control<ccmg else 'SAME_MINUTE')
        assert new['controlIntentMinute']==control and new['intentOrder']==order
        assert new['control_intent_time_known'] is True
        assert new['control_model_intent_time_known']==(ref['controlExitKind']=='MODEL_EXIT')
        assert new['control_terminal_intent_time_known']==(ref['controlExitKind']=='FORCED_TERMINAL')
        for key in old:
            if key not in ('intentOrder','controlIntentMinute','control_intent_time_known'):
                assert old[key]==new[key],key
    for arm in ('IM','R1'):
        for world in ('ALL_100','PRIMARY_FUNDED','PRIMARY_OUTSIDE_100'):
            for route in ('ALL_ROUTES','DEFENSIVE_ELIGIBLE','CONTROL_DEFAULT'):
                subset=[r for r in after if r['arm']==arm and
                        (r['world']=='PRIMARY_FUNDED' if world=='PRIMARY_FUNDED' else
                         r['world']=='ALL_100' and
                         (world!='PRIMARY_OUTSIDE_100' or not r['primary'])) and
                        (route=='ALL_ROUTES' or r['routeDecision']==route)]
                table=receipt['table'][f'{arm}:{world}:{route}']
                assert len(subset)==table['entryN']
                assert dict(Counter(r['intentOrder'] for r in subset))==table['intentOrderN']
                assert sum(r['control_model_intent_time_known'] for r in subset)==table['r50ModelIntentN']
                assert sum(r['control_terminal_intent_time_known'] for r in subset)==table['r50ForcedTerminalDecisionN']
    print(json.dumps({'status':'PASS','rowsVerified':len(after),
                      'correctionSha256':sha(OUT/'A0_INTENT_SEMANTICS_CORRECTION.json')}))


if __name__=='__main__':main()
