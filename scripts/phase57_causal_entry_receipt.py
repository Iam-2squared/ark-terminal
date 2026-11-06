"""Immutable study receipt and hash verification, no research execution."""
import argparse
import os
import re
from pathlib import Path
from scripts import phase57_causal_entry_anatomy as a


def verify(root):
    p=a.verify();root=Path(root);r=a.c.read(root/'receipt.json')
    for f,h in r['implementationPins'].items():assert a.c.sha(a.e.ROOT/f)==h,f
    for f,h in r['evidencePins'].items():assert a.c.sha(root/f)==h,f
    for sub in ('measurement','report'):
        for f,h in a.c.read(root/sub/'manifest.json').items():assert a.c.sha(root/sub/f)==h,f
    audit=a.c.read(root/'measurement/audit.json');assert audit['population']==2155 and sum(audit['pathCounts'].values())==2155
    assert audit['baselineParity'] and not audit['trainingEntry'] and not audit['dictionaryUsed']
    assert not audit['holdoutOpened'] and all(v is False for v in audit['safety'].values())
    assert r['dailyDeterminism'] and r['measurementDeterminism'] and r['reportDeterminism']
    trades=a.c.read(root/'measurement/trades.json.gz')
    for arm,rows in trades.items():
        assert len(rows)==2155 and {t['opportunity'] for t in rows}==set(p['opportunityIds'])
        assert all(t['modelRejection'] is False for t in rows)
    assert sum(bool(t['entryId']) for t in trades['A'])==1963
    print('CAUSAL_ENTRY_STATE_EVIDENCE_VERIFIED')


def create(root):
    root=Path(root);assert not (root/'receipt.json').exists()
    log=(root/'focused.log').read_text();match=re.search(r'Ran (\d+) tests',log);assert match and '\nOK' in log
    regression=a.c.read(root/'regression/regression.json');assert regression['status']=='PASS',regression['status']
    files=sorted(a.e.ROOT.glob('scripts/phase57_causal_entry_*.py'))+[a.e.ROOT/'scripts/test_phase57_causal_entry_state.py',a.e.ROOT/'.github/workflows/phase57-causal-entry-state-v1.yml']
    receipt={'executionHead':os.environ['EXECUTION_HEAD'],'runId':os.environ['GITHUB_RUN_ID'],
             'focusedTests':int(match[1]),'regressionStatus':regression['status'],'dailyDeterminism':True,'measurementDeterminism':True,'reportDeterminism':True,
             'implementationPins':{str(f.relative_to(a.e.ROOT)):a.c.sha(f) for f in files},
             'evidencePins':{str(f.relative_to(root)):a.c.sha(f) for f in sorted(root.rglob('*')) if f.is_file()},
             'safety':a.s.verify()['safety'],'stop':True,'dedicatedCIIsNotPRGreen':True}
    a.c.write(root/'receipt.json',receipt);verify(root)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['create','verify']);p.add_argument('--evidence',required=True);x=p.parse_args()
    (create if x.command=='create' else verify)(x.evidence)
